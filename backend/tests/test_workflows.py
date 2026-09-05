"""
Integration tests for the workflows added in this pass: evidence review
(separation of duties), formal risk acceptance, and persisted/reviewable
applicability decisions.
"""

import uuid
import pytest

from tests.test_api_security import _signup, _create_user_with_role


@pytest.mark.asyncio
async def test_evidence_review_requires_reviewer_role_not_uploader_role(client):
    admin = await _signup(client, email=f"ev-admin-{uuid.uuid4().hex[:8]}@example.com")
    admin_token = admin["access_token"]
    tenant_id = admin["user"]["tenant_id"]
    org_id = admin["user"]["organization_id"]

    files = {"file": ("report.txt", b"Pen test report contents", "text/plain")}
    data = {"title": "Pen Test Report", "evidence_type": "Test Report", "control_ids": "[]"}
    upload = await client.post(
        "/api/v1/evidence/upload", data=data, files=files, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert upload.status_code == 200
    evidence_id = upload.json()["id"]
    assert upload.json()["approval_status"] == "Submitted"

    # An AI Engineer (governance-write, but not an evidence reviewer) must not
    # be able to self-approve evidence - separation of duties.
    engineer_email = f"engineer-{uuid.uuid4().hex[:8]}@example.com"
    await _create_user_with_role(tenant_id, org_id, "AI Engineer", engineer_email)
    engineer_login = await client.post("/api/v1/auth/login", json={"email": engineer_email, "password": "StrongPass1!"})
    engineer_token = engineer_login.json()["access_token"]

    denied = await client.put(
        f"/api/v1/evidence/{evidence_id}/review",
        json={"status": "Accepted", "notes": "self-approved, should be rejected"},
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert denied.status_code == 403

    # A Compliance Manager (a designated reviewer role) can approve it.
    reviewer_email = f"reviewer-{uuid.uuid4().hex[:8]}@example.com"
    await _create_user_with_role(tenant_id, org_id, "Compliance Manager", reviewer_email)
    reviewer_login = await client.post("/api/v1/auth/login", json={"email": reviewer_email, "password": "StrongPass1!"})
    reviewer_token = reviewer_login.json()["access_token"]

    approved = await client.put(
        f"/api/v1/evidence/{evidence_id}/review",
        json={"status": "Accepted", "notes": "Verified against pen test vendor report"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert approved.status_code == 200
    assert approved.json()["approval_status"] == "Accepted"


@pytest.mark.asyncio
async def test_risk_acceptance_requires_justification_and_role(client):
    admin = await _signup(client, email=f"risk-admin-{uuid.uuid4().hex[:8]}@example.com")
    admin_token = admin["access_token"]

    create_risk = await client.post(
        "/api/v1/risks",
        json={"risk_code": "RSK-TEST-001", "title": "Test Risk", "category": "Security"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_risk.status_code == 200
    risk_id = create_risk.json()["id"]

    # Missing justification must be rejected.
    no_justification = await client.put(
        f"/api/v1/risks/{risk_id}/accept", json={}, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert no_justification.status_code == 400

    # With justification, a Tenant Admin (in the risk-acceptance tier) can accept it.
    accepted = await client.put(
        f"/api/v1/risks/{risk_id}/accept",
        json={"business_justification": "Compensating control in place; residual risk within appetite."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "Accepted"


@pytest.mark.asyncio
async def test_applicability_decision_persisted_and_reviewable(client):
    admin = await _signup(client, email=f"legal-admin-{uuid.uuid4().hex[:8]}@example.com")
    admin_token = admin["access_token"]

    intake_payload = {
        "system_name": "EU Credit Scoring Engine",
        "business_purpose": "Automated credit decisioning",
        "deployment_countries": ["EU", "DE"],
        "makes_decisions_about_individuals": True,
        "decision_domains": ["credit"],
        "interacts_directly_with_humans": False,
        "generates_synthetic_content": False,
        "processes_personal_data": True,
        "is_generative_ai": False,
        "uses_foundation_model": False,
        "is_autonomous_agent": False,
    }
    evaluate = await client.post(
        "/api/v1/ai-systems/intake-evaluate", json=intake_payload, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert evaluate.status_code == 200
    assert evaluate.json()["risk_level"] == "High Risk"

    # The evaluation must be persisted, not just returned transiently.
    decisions = await client.get(
        "/api/v1/ai-systems/applicability/decisions", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert decisions.status_code == 200
    matching = [d for d in decisions.json() if d["system_name"] == "EU Credit Scoring Engine"]
    assert len(matching) == 1
    decision = matching[0]
    assert decision["requires_legal_review"] is True
    assert decision["decision_status"] == "LEGAL_REVIEW_REQUIRED"
    assert len(decision["required_controls"]) > 0

    # Tenant Admin is in the LEGAL_REVIEW tier and can accept the classification,
    # closing the human-in-the-loop review loop.
    review = await client.put(
        f"/api/v1/ai-systems/applicability/decisions/{decision['id']}/review",
        json={"decision": "Accepted", "rationale": "Confirmed High-Risk classification is correct."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert review.status_code == 200
    assert review.json()["decision_status"] == "APPLICABLE"
