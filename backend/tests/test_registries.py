"""
Tests for Phase 1: Model Registry, Agent Registry, Vendor Registry, and
their dependency-graph views (Model -> Systems, Vendor -> Models -> Systems,
Agent Permission Graph). Includes cross-tenant isolation checks for every
new resource type, per the "every new asset type must be tenant-isolated"
requirement.
"""

import uuid
import pytest

from tests.test_api_security import _signup


async def _create_system(client, token, name="Test System"):
    resp = await client.post("/api/v1/ai-systems", json={"name": name}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_model_registry_crud_and_dependents(client):
    admin = await _signup(client, email=f"model-admin-{uuid.uuid4().hex[:8]}@example.com")
    token = admin["access_token"]

    system_id = await _create_system(client, token, "Loan Decision Engine")

    create = await client.post(
        "/api/v1/models",
        json={"name": "GPT-4o", "provider": "OpenAI", "version": "2024-11-20", "system_id": system_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create.status_code == 200, create.text
    model_id = create.json()["id"]

    # Link to a second system - proving Model -> many Systems is real, not 1:1.
    system2_id = await _create_system(client, token, "Customer Support Copilot")
    link = await client.post(
        f"/api/v1/models/{model_id}/link-system",
        json={"system_id": system2_id, "role": "Secondary"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert link.status_code == 200

    dependents = await client.get(f"/api/v1/models/{model_id}/dependents", headers={"Authorization": f"Bearer {token}"})
    assert dependents.status_code == 200
    body = dependents.json()
    dependent_ids = {s["id"] for s in body["dependent_systems"]}
    assert system_id in dependent_ids
    assert system2_id in dependent_ids
    assert len(body["dependent_systems"]) == 2

    update = await client.put(
        f"/api/v1/models/{model_id}", json={"status": "Deprecated"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert update.status_code == 200
    assert update.json()["status"] == "Deprecated"


@pytest.mark.asyncio
async def test_agent_registry_risk_score_and_permission_graph(client):
    admin = await _signup(client, email=f"agent-admin-{uuid.uuid4().hex[:8]}@example.com")
    token = admin["access_token"]
    system_id = await _create_system(client, token, "IT Support Agent Host System")

    high_risk_agent = await client.post(
        "/api/v1/agents",
        json={
            "name": "Deploy-Bot", "system_id": system_id,
            "has_code_execution": True, "has_git_write_access": True, "has_payment_access": True,
            "autonomy_level": "Fully Autonomous", "human_approval_required": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert high_risk_agent.status_code == 200, high_risk_agent.text
    high_risk_data = high_risk_agent.json()
    assert high_risk_data["risk_score"] > 50  # payment(25) + code_exec(20) + git_write(18) + autonomy(25) + no_approval(15) - kill_switch(10)

    low_risk_agent = await client.post(
        "/api/v1/agents",
        json={"name": "Read-Only-Reporter", "system_id": system_id, "autonomy_level": "Supervised", "human_approval_required": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert low_risk_agent.status_code == 200
    assert low_risk_agent.json()["risk_score"] < high_risk_data["risk_score"]

    graph = await client.get("/api/v1/agents/permission-graph", headers={"Authorization": f"Bearer {token}"})
    assert graph.status_code == 200
    g = graph.json()
    assert high_risk_data["id"] in [a["id"] for a in g["agents_with_code_execution"]]
    assert high_risk_data["id"] in [a["id"] for a in g["agents_with_github_write"]]
    assert high_risk_data["id"] in [a["id"] for a in g["agents_with_financial_actions"]]
    assert high_risk_data["id"] in [a["id"] for a in g["agents_without_human_approval_gate"]]
    assert low_risk_agent.json()["id"] not in [a["id"] for a in g["agents_without_human_approval_gate"]]


@pytest.mark.asyncio
async def test_vendor_registry_impact_via_api(client):
    admin = await _signup(client, email=f"vendor-admin-{uuid.uuid4().hex[:8]}@example.com")
    token = admin["access_token"]

    vendor = await client.post(
        "/api/v1/vendors",
        json={"name": "Acme Foundation Models Inc", "service_type": "Foundation Model API", "risk_rating": "Medium"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert vendor.status_code == 200
    vendor_id = vendor.json()["id"]

    # AISystemCreate defaults risk_classification to "High Risk", so the "low
    # risk" system here must be explicitly downgraded to actually test the
    # high-risk-only filter in the vendor impact endpoint.
    sys_high = await _create_system(client, token, "High Risk Credit System")
    sys_low = await _create_system(client, token, "Low Risk Internal Tool")
    await client.put(
        f"/api/v1/ai-systems/{sys_low}", json={"risk_classification": "Minimal Risk"}, headers={"Authorization": f"Bearer {token}"}
    )

    model = await client.post(
        "/api/v1/models",
        json={"name": "VendorModel-1", "provider": "Acme", "vendor_id": vendor_id, "system_id": sys_high},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert model.status_code == 200
    model_id = model.json()["id"]
    await client.post(
        f"/api/v1/models/{model_id}/link-system", json={"system_id": sys_low, "role": "Secondary"},
        headers={"Authorization": f"Bearer {token}"},
    )

    impact = await client.get(f"/api/v1/vendors/{vendor_id}/impact", headers={"Authorization": f"Bearer {token}"})
    assert impact.status_code == 200
    body = impact.json()
    assert body["dependent_systems_count"] == 2
    assert body["high_risk_systems_count"] == 1
    assert body["high_risk_systems"][0]["id"] == sys_high


@pytest.mark.asyncio
async def test_registries_are_tenant_isolated(client):
    tenant_a = await _signup(client, email=f"reg-a-{uuid.uuid4().hex[:8]}@example.com")
    tenant_b = await _signup(client, email=f"reg-b-{uuid.uuid4().hex[:8]}@example.com")
    token_a, token_b = tenant_a["access_token"], tenant_b["access_token"]

    system_id = await _create_system(client, token_a, "Tenant A System")
    model = await client.post(
        "/api/v1/models", json={"name": "Tenant A Model", "system_id": system_id}, headers={"Authorization": f"Bearer {token_a}"}
    )
    model_id = model.json()["id"]

    agent = await client.post(
        "/api/v1/agents", json={"name": "Tenant A Agent", "system_id": system_id}, headers={"Authorization": f"Bearer {token_a}"}
    )
    agent_id = agent.json()["id"]

    vendor = await client.post(
        "/api/v1/vendors", json={"name": "Tenant A Vendor"}, headers={"Authorization": f"Bearer {token_a}"}
    )
    vendor_id = vendor.json()["id"]

    # Every read/write of Tenant A's registry objects using Tenant B's token must 404.
    for path in [f"/api/v1/models/{model_id}", f"/api/v1/agents/{agent_id}", f"/api/v1/vendors/{vendor_id}"]:
        resp = await client.get(path, headers={"Authorization": f"Bearer {token_b}"})
        assert resp.status_code == 404, f"{path} leaked across tenants"

    # List endpoints must not include Tenant A's objects either.
    models_b = await client.get("/api/v1/models", headers={"Authorization": f"Bearer {token_b}"})
    assert all(m["id"] != model_id for m in models_b.json())
    agents_b = await client.get("/api/v1/agents", headers={"Authorization": f"Bearer {token_b}"})
    assert all(a["id"] != agent_id for a in agents_b.json())
    vendors_b = await client.get("/api/v1/vendors", headers={"Authorization": f"Bearer {token_b}"})
    assert all(v["id"] != vendor_id for v in vendors_b.json())
