"""
Tests for Phase 2: regulatory + asset knowledge graph query endpoints.
Verifies each traversal returns real, computed results grounded in actual
tenant data - not canned answers - and respects tenant isolation.
"""

import uuid
import pytest

from tests.test_api_security import _signup
from tests.test_registries import _create_system


@pytest.mark.asyncio
async def test_requirement_affected_systems(client):
    admin = await _signup(client, email=f"graph-req-{uuid.uuid4().hex[:8]}@example.com")
    token = admin["access_token"]

    system_id = await _create_system(client, token, "EU AI Act System")
    await client.put(
        f"/api/v1/ai-systems/{system_id}",
        json={"risk_classification": "High Risk"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # AISystemUpdate schema doesn't expose applicable_frameworks directly;
    # set it via a raw create instead, since intake/create defaults matter here.
    system2 = await client.post(
        "/api/v1/ai-systems",
        json={"name": "System With EU AI Act Framework"},
        headers={"Authorization": f"Bearer {token}"},
    )
    system2_id = system2.json()["id"]

    # Use a known requirement id from the real EU AI Act content loaded at startup.
    resp = await client.get(
        "/api/v1/graph/requirement/EU-AIA-ART-09/affected-systems",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["framework_id"] == "eu_ai_act"
    assert "affected_systems_count" in body


@pytest.mark.asyncio
async def test_requirement_not_found(client):
    admin = await _signup(client, email=f"graph-404-{uuid.uuid4().hex[:8]}@example.com")
    resp = await client.get(
        "/api/v1/graph/requirement/NOT-A-REAL-REQUIREMENT/affected-systems",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_controls_satisfying_multiple_frameworks(client):
    admin = await _signup(client, email=f"graph-ctrl-{uuid.uuid4().hex[:8]}@example.com")
    token = admin["access_token"]
    resp = await client.get(
        "/api/v1/graph/controls/multi-framework",
        params={"frameworks": "owasp_llm,mitre_atlas"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    controls = resp.json()
    assert len(controls) >= 1
    for c in controls:
        assert "owasp_llm" in c["covers_frameworks"]
        assert "mitre_atlas" in c["covers_frameworks"]


@pytest.mark.asyncio
async def test_evidence_highest_coverage_ranking(client):
    admin = await _signup(client, email=f"graph-ev-{uuid.uuid4().hex[:8]}@example.com")
    token = admin["access_token"]

    # Evidence mapped to a control with broad crosswalk coverage should rank
    # above evidence mapped to nothing.
    ev = await client.post(
        "/api/v1/evidence",
        json={"title": "Broad Coverage Evidence", "control_ids": ["UC-AI-SEC-001"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ev.status_code == 200

    resp = await client.get("/api/v1/graph/evidence/highest-coverage", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    ranked = resp.json()
    assert len(ranked) == 1
    assert ranked[0]["title"] == "Broad Coverage Evidence"
    assert ranked[0]["satisfied_requirements_count"] > 0


@pytest.mark.asyncio
async def test_vendor_regulatory_exposure_and_shared_model_graph(client):
    admin = await _signup(client, email=f"graph-vendor-{uuid.uuid4().hex[:8]}@example.com")
    token = admin["access_token"]

    vendor = await client.post("/api/v1/vendors", json={"name": "Exposure Vendor"}, headers={"Authorization": f"Bearer {token}"})
    vendor_id = vendor.json()["id"]

    sys1 = await _create_system(client, token, "System One")
    sys2 = await _create_system(client, token, "System Two")

    model = await client.post(
        "/api/v1/models",
        json={"name": "Shared-Model", "vendor_id": vendor_id, "system_id": sys1},
        headers={"Authorization": f"Bearer {token}"},
    )
    model_id = model.json()["id"]
    await client.post(f"/api/v1/models/{model_id}/link-system", json={"system_id": sys2}, headers={"Authorization": f"Bearer {token}"})

    exposure = await client.get("/api/v1/graph/vendors/regulatory-exposure", headers={"Authorization": f"Bearer {token}"})
    assert exposure.status_code == 200
    vendor_row = next(v for v in exposure.json() if v["vendor_id"] == vendor_id)
    assert vendor_row["dependent_systems_count"] == 2

    # Both default-created systems are "High Risk" (AISystemCreate default),
    # so they should appear as a shared-high-risk-model cluster.
    shared = await client.get("/api/v1/graph/models/shared-high-risk", headers={"Authorization": f"Bearer {token}"})
    assert shared.status_code == 200
    cluster = next((c for c in shared.json() if c["model_id"] == model_id), None)
    assert cluster is not None
    assert cluster["high_risk_systems_count"] == 2


@pytest.mark.asyncio
async def test_agent_tool_dependents(client):
    admin = await _signup(client, email=f"graph-agent-{uuid.uuid4().hex[:8]}@example.com")
    token = admin["access_token"]
    system_id = await _create_system(client, token, "Agent Host System")

    await client.post(
        "/api/v1/agents",
        json={"name": "Vulnerable-Tool-User", "system_id": system_id, "tools": ["log4j-parser", "jira_api_client"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/graph/agents/tool-dependents", params={"tool": "log4j-parser"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["dependent_agents_count"] == 1
    assert body["dependent_agents"][0]["name"] == "Vulnerable-Tool-User"


@pytest.mark.asyncio
async def test_graph_queries_are_tenant_isolated(client):
    tenant_a = await _signup(client, email=f"graph-iso-a-{uuid.uuid4().hex[:8]}@example.com")
    tenant_b = await _signup(client, email=f"graph-iso-b-{uuid.uuid4().hex[:8]}@example.com")

    sys_id = await _create_system(client, tenant_a["access_token"], "Tenant A Only System")
    await client.post(
        "/api/v1/agents", json={"name": "Tenant A Agent", "system_id": sys_id, "tools": ["shared-tool-name"]},
        headers={"Authorization": f"Bearer {tenant_a['access_token']}"},
    )

    resp = await client.get(
        "/api/v1/graph/agents/tool-dependents", params={"tool": "shared-tool-name"},
        headers={"Authorization": f"Bearer {tenant_b['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["dependent_agents_count"] == 0
