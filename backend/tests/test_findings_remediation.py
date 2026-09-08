"""
Regression tests for the finding / remediation workflow added during the
company-usability hardening pass (spec §16, §23, §24, §26, §35).

Before this pass Findings could only be created by the seed script - a real
customer could not raise, progress or close one. These tests lock in:
  - POST /findings (manual raise, RBAC-gated)
  - PUT  /findings/{id} (progress / close, row never deleted)
  - POST /remediations (task against a finding, works without Jira)
  - PUT  /remediations/{id} -> completing all tasks resolves the finding
  - a control marked Ineffective auto-raises a "Failed Control" finding
  - the control recovering auto-resolves that finding
  - rejected / insufficient evidence auto-raises a "Missing Evidence" finding
  - tenant isolation on all of the above
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _signup(client, org="FindingCo", email=None):
    email = email or f"find-{uuid.uuid4().hex[:8]}@co.example"
    r = await client.post("/api/v1/auth/signup", json={
        "email": email, "password": "StrongPass1!", "full_name": "Lead", "organization_name": org,
    })
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


async def test_manual_finding_and_remediation_lifecycle(client):
    tok = await _signup(client)

    # raise
    r = await client.post("/api/v1/findings", headers=_h(tok), json={
        "title": "Red team bypassed prompt-injection filter", "severity": "Critical",
        "control_id": "UC-AI-SEC-001", "source": "Red Team",
    })
    assert r.status_code == 201, r.text
    fid = r.json()["id"]
    assert r.json()["status"] == "Open"
    assert r.json()["due_date"] is not None  # SLA auto-set

    # it shows in the list
    lst = await client.get("/api/v1/findings", headers=_h(tok))
    assert any(f["id"] == fid for f in lst.json())

    # remediation task
    r = await client.post("/api/v1/remediations", headers=_h(tok), json={
        "finding_id": fid, "title": "Ship v2 filter", "assigned_to": "AI Engineer", "priority": "Critical",
    })
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    # creating a task moves the finding to Remediating
    lst = await client.get("/api/v1/findings", headers=_h(tok))
    assert next(f for f in lst.json() if f["id"] == fid)["status"] == "Remediating"

    # completing the task resolves the finding (still present in list = audit trail)
    r = await client.put(f"/api/v1/remediations/{tid}", headers=_h(tok), json={"status": "Done"})
    assert r.status_code == 200
    lst = await client.get("/api/v1/findings", headers=_h(tok))
    resolved = next(f for f in lst.json() if f["id"] == fid)
    assert resolved["status"] == "Resolved"

    # explicit close endpoint also works and does not delete
    r = await client.put(f"/api/v1/findings/{fid}", headers=_h(tok), json={"status": "Resolved", "severity": "High"})
    assert r.status_code == 200
    assert r.json()["severity"] == "High"


async def test_failed_control_autocreates_and_recovers_finding(client):
    tok = await _signup(client)

    r = await client.put("/api/v1/controls/UC-AI-AGT-005", headers=_h(tok), json={
        "status": "Implemented", "effectiveness": "Ineffective",
        "implementation_notes": "Sandbox escape found", "owner": "CISO",
    })
    assert r.status_code == 200

    lst = (await client.get("/api/v1/findings", headers=_h(tok))).json()
    auto = [f for f in lst if f["source"] == "Failed Control" and f["control_id"] == "UC-AI-AGT-005"]
    assert len(auto) == 1
    assert auto[0]["severity"] == "Critical"  # agent-security domain -> critical
    assert auto[0]["status"] == "Open"

    # marking the same control ineffective again must NOT create a duplicate
    await client.put("/api/v1/controls/UC-AI-AGT-005", headers=_h(tok), json={
        "status": "Implemented", "effectiveness": "Ineffective", "owner": "CISO",
    })
    lst = (await client.get("/api/v1/findings", headers=_h(tok))).json()
    assert len([f for f in lst if f["source"] == "Failed Control" and f["control_id"] == "UC-AI-AGT-005"
                and f["status"] not in ("Resolved", "Accepted Risk")]) == 1

    # recovery auto-resolves
    await client.put("/api/v1/controls/UC-AI-AGT-005", headers=_h(tok), json={
        "status": "Tested", "effectiveness": "Effective", "owner": "CISO",
    })
    lst = (await client.get("/api/v1/findings", headers=_h(tok))).json()
    assert all(f["status"] == "Resolved" for f in lst
               if f["source"] == "Failed Control" and f["control_id"] == "UC-AI-AGT-005")


async def test_rejected_evidence_autocreates_finding(client):
    tok = await _signup(client)
    r = await client.post("/api/v1/evidence", headers=_h(tok), json={
        "title": "Draft AI policy", "evidence_type": "Policy",
        "file_url": "https://example.com/p.pdf", "control_ids": ["UC-AI-GOV-001"],
    })
    assert r.status_code in (200, 201), r.text
    eid = r.json()["id"]

    r = await client.put(f"/api/v1/evidence/{eid}/review", headers=_h(tok),
                         json={"status": "Insufficient", "notes": "Not board approved"})
    assert r.status_code == 200

    lst = (await client.get("/api/v1/findings", headers=_h(tok))).json()
    ev = [f for f in lst if f["source"] == "Missing Evidence" and f["control_id"] == "UC-AI-GOV-001"]
    assert len(ev) == 1
    assert "insufficient" in ev[0]["title"].lower()


async def test_findings_and_remediation_are_tenant_isolated(client):
    a = await _signup(client, org="FA")
    b = await _signup(client, org="FB")

    fid = (await client.post("/api/v1/findings", headers=_h(a), json={
        "title": "A only", "severity": "High", "source": "Manual Review",
    })).json()["id"]

    # B cannot see or mutate A's finding
    assert all(f["id"] != fid for f in (await client.get("/api/v1/findings", headers=_h(b))).json())
    assert (await client.put(f"/api/v1/findings/{fid}", headers=_h(b), json={"status": "Resolved"})).status_code == 404
    assert (await client.post("/api/v1/remediations", headers=_h(b), json={
        "finding_id": fid, "title": "x",
    })).status_code == 404

    # unauthenticated blocked
    assert (await client.post("/api/v1/findings", json={"title": "x", "severity": "Low"})).status_code == 401


async def test_finding_rejects_foreign_system_id(client):
    a = await _signup(client, org="SA")
    b = await _signup(client, org="SB")
    sysB = (await client.post("/api/v1/ai-systems", headers=_h(b), json={"name": "B sys"})).json()["id"]
    r = await client.post("/api/v1/findings", headers=_h(a), json={
        "title": "cross", "severity": "High", "system_id": sysB,
    })
    assert r.status_code == 404
