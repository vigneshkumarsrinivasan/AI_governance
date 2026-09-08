"""
Customer Acceptance E2E (spec §79) - one test that walks the whole journey a
real company runs on day one, with NO database writes. Runs on every release.

signup -> onboarding -> company applicability -> register AI systems ->
per-system intake (differentiated) -> model/vendor/agent -> assessment (real
regulatory requirements) -> evidence -> control test -> finding -> remediation
-> risk + acceptance -> report -> audit trail -> tenant isolation.
"""
import uuid
import pytest

pytestmark = pytest.mark.asyncio


def _h(t):
    return {"Authorization": f"Bearer {t}"}


async def test_full_customer_journey_no_db_edits(client):
    em = f"acceptance-{uuid.uuid4().hex[:8]}@co.example"

    # 1. signup
    s = (await client.post("/api/v1/auth/signup", json={
        "email": em, "password": "StrongPass1!", "full_name": "Founder",
        "organization_name": "Acceptance Test Ltd",
    })).json()
    tok = s["access_token"]
    assert s["user"]["ui_mode"] == "simple"

    # 2. onboarding (India fintech selling to DE/SG)
    r = await client.put("/api/v1/onboarding/profile", headers=_h(tok), json={
        "headquarters_country": "IN", "operating_countries": ["IN", "DE", "SG"],
        "employee_count": 30, "industry": "fintech", "sells_to_enterprises": True,
        "sells_to_financial_institutions": True, "develops_ai_products": True,
        "uses_generative_ai": True, "uses_rag": True, "builds_ai_agents": True,
        "uses_third_party_models": True, "makes_decisions_about_people": True,
        "decision_domains": ["credit"], "ai_providers": ["openai", "anthropic"],
        "data_types": ["personal", "financial"], "is_saas": True, "sells_software": True,
        "soc2_required": True, "completed": True,
    })
    assert r.status_code == 200

    # 3. company applicability - differentiated + explainable
    appl = (await client.get("/api/v1/onboarding/applicability", headers=_h(tok))).json()
    fw = {e["framework_key"]: e for e in appl["exposures"]}
    assert fw["gdpr"]["exposure"].startswith("DIRECTLY")
    assert fw["india_dpdp"]["exposure"].startswith("DIRECTLY")
    assert fw["eu_ai_act"]["exposure"].startswith("DIRECTLY")
    assert fw["dora"]["exposure"] != "DIRECTLY_APPLICABLE"      # not blindly applied
    assert fw["nist_ai_rmf"]["regulation_type"] == "VOLUNTARY_FRAMEWORK"
    assert all(e["reasoning"] and e["source_reference"] for e in appl["exposures"])
    assert appl["legal_review_recommended"] is True

    # 4. register 3 distinct AI systems
    loan = (await client.post("/api/v1/ai-systems", headers=_h(tok), json={
        "name": "Loan Decision AI", "business_purpose": "Credit underwriting",
        "is_generative_ai": False, "uses_traditional_ml": True, "makes_autonomous_decisions": True,
        "human_in_the_loop": False, "processes_personal_data": True, "processes_sensitive_data": True,
        "countries_deployed": ["DE"], "risk_classification": "High Risk",
    })).json()
    copilot = (await client.post("/api/v1/ai-systems", headers=_h(tok), json={
        "name": "Internal Coding Copilot", "business_purpose": "Assist engineers",
        "is_generative_ai": True, "internal_or_external": "Internal", "processes_personal_data": False,
        "countries_deployed": ["IN"], "risk_classification": "Minimal Risk",
    })).json()
    assert loan["id"] and copilot["id"]

    # 5. per-system intake is differentiated
    loan_i = (await client.post("/api/v1/ai-systems/intake-evaluate", headers=_h(tok), json={
        "system_name": "Loan Decision AI", "business_purpose": "Credit underwriting",
        "makes_decisions_about_individuals": True, "decision_domains": ["credit"],
        "processes_sensitive_personal_data": True, "is_generative_ai": False,
        "deployment_countries": ["DE"], "human_in_the_loop_approval": False,
    })).json()
    copilot_i = (await client.post("/api/v1/ai-systems/intake-evaluate", headers=_h(tok), json={
        "system_name": "Internal Coding Copilot", "business_purpose": "Assist engineers",
        "makes_decisions_about_individuals": False, "is_generative_ai": True,
        "processes_personal_data": False, "deployment_countries": ["IN"],
    })).json()
    assert "High" in loan_i["risk_level"]
    assert loan_i["risk_level"] != copilot_i["risk_level"]

    # 6. agent registry + risk score
    agent = (await client.post("/api/v1/agents", headers=_h(tok), json={
        "name": "IT Agent", "system_id": copilot["id"], "purpose": "Fix tickets",
        "tools": ["sql_query", "code_executor"], "has_code_execution": True,
        "has_database_access": True, "human_approval_required": False, "environments": ["Production"],
    })).json()
    got = (await client.get(f"/api/v1/agents/{agent['id']}", headers=_h(tok))).json()
    assert got["risk_score"] > 0

    # 7. assessment populates from the requirement set. In a fresh test DB the
    #    regulatory_* tables are empty, so it uses the legacy catalog; against a
    #    DB with ingested content it uses the real set (e.g. EU AI Act = 419).
    #    The live E2E (full_e2e.py / CUSTOMER_WORKFLOW_E2E_REPORT.md) verifies
    #    the 419-requirement path.
    a = (await client.post("/api/v1/assessments", headers=_h(tok), json={
        "system_id": loan["id"], "framework_id": "eu_ai_act", "title": "EU AI Act - Loan AI",
    })).json()
    assert a["requirement_count"] > 0
    assert a["requirement_source"] in ("legacy",) or a["requirement_source"].startswith("regulatory:")
    det = (await client.get(f"/api/v1/assessments/{a['id']}", headers=_h(tok))).json()
    first_req = det["responses"][0]["requirement_id"]
    r = await client.put(f"/api/v1/assessments/{a['id']}/response", headers=_h(tok), json={
        "requirement_id": first_req, "status": "Partial", "rationale": "partial", "evidence_ids": [],
    })
    assert r.status_code == 200

    # 8. evidence -> reject -> finding
    ev = (await client.post("/api/v1/evidence", headers=_h(tok), json={
        "title": "Draft policy", "evidence_type": "Policy", "file_url": "https://x/p.pdf",
        "control_ids": ["UC-AI-GOV-001"],
    })).json()
    await client.put(f"/api/v1/evidence/{ev['id']}/review", headers=_h(tok),
                     json={"status": "Insufficient", "notes": "not approved"})
    findings = (await client.get("/api/v1/findings", headers=_h(tok))).json()
    assert any(f["source"] == "Missing Evidence" for f in findings)

    # 9. failed control -> finding -> remediation -> resolve
    await client.put("/api/v1/controls/UC-AI-SEC-001", headers=_h(tok), json={
        "status": "Implemented", "effectiveness": "Ineffective", "owner": "CISO",
    })
    findings = (await client.get("/api/v1/findings", headers=_h(tok))).json()
    fc = next(f for f in findings if f["source"] == "Failed Control")
    task = (await client.post("/api/v1/remediations", headers=_h(tok), json={
        "finding_id": fc["id"], "title": "fix", "assigned_to": "AI Engineer",
    })).json()
    await client.put(f"/api/v1/remediations/{task['id']}", headers=_h(tok), json={"status": "Done"})
    findings = (await client.get("/api/v1/findings", headers=_h(tok))).json()
    assert next(f for f in findings if f["id"] == fc["id"])["status"] == "Resolved"

    # 10. risk + acceptance
    risk = (await client.post("/api/v1/risks", headers=_h(tok), json={
        "risk_code": "R-1", "title": "prompt injection", "category": "AI Security",
        "inherent_likelihood": 4, "inherent_impact": 5,
    })).json()
    assert (await client.put(f"/api/v1/risks/{risk['id']}/accept", headers=_h(tok),
                             json={"business_justification": "30 days pending fix"})).status_code == 200
    assert (await client.put(f"/api/v1/risks/{risk['id']}/accept", headers=_h(tok),
                             json={"business_justification": ""})).status_code in (400, 422)

    # 11. report + dashboard + audit are real
    rep = (await client.get("/api/v1/reports/executive", headers=_h(tok))).json()
    assert rep["organization"]["name"] == "Acceptance Test Ltd"
    dash = (await client.get("/api/v1/dashboard/metrics", headers=_h(tok))).json()
    assert isinstance(dash["overall_readiness_percentage"], (int, float))
    audit = (await client.get("/api/v1/audit", headers=_h(tok))).json()
    assert len(audit) >= 5

    # 12. tenant isolation
    other = (await client.post("/api/v1/auth/signup", json={
        "email": f"iso-{uuid.uuid4().hex[:8]}@co.example", "password": "StrongPass1!",
        "full_name": "X", "organization_name": "Other Ltd",
    })).json()["access_token"]
    assert (await client.get(f"/api/v1/ai-systems/{loan['id']}", headers=_h(other))).status_code in (403, 404)
    assert (await client.get(f"/api/v1/assessments/{a['id']}", headers=_h(other))).status_code in (403, 404)
    assert len((await client.get("/api/v1/ai-systems", headers=_h(other))).json()) == 0
