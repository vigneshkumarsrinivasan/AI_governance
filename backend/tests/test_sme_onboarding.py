"""
Tests for the SME repositioning layer (spec sections 4-7, 16, 23, 29):
  - company onboarding profile CRUD
  - company-level applicability engine: differentiated, explainable, never
    false certainty, legal/cert/voluntary distinction
  - AI Trust Score derives from real control state (no fabricated numbers)
  - next-actions derives from real gaps
  - UI mode toggle preserves both experiences
  - tenant isolation on every new endpoint
All of this is ADDITIVE - the existing per-system intake endpoint and every
enterprise route must still behave exactly as before.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _signup(client, org="Nimbus", email=None):
    email = email or f"sme-{uuid.uuid4().hex[:8]}@startup.io"
    r = await client.post("/api/v1/auth/signup", json={
        "email": email, "password": "StrongPass1!", "full_name": "Founder", "organization_name": org,
    })
    assert r.status_code == 200, r.text
    return r.json()


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


async def test_new_signup_lands_in_simple_mode_and_can_switch(client):
    s = await _signup(client)
    assert s["user"]["ui_mode"] == "simple"
    assert s["user"]["onboarding_completed"] is False

    me = await client.get("/api/v1/auth/me", headers=_hdr(s["access_token"]))
    assert me.json()["ui_mode"] == "simple"

    switch = await client.patch("/api/v1/auth/me/ui-mode", headers=_hdr(s["access_token"]),
                                json={"ui_mode": "advanced"})
    assert switch.status_code == 200
    assert switch.json()["ui_mode"] == "advanced"

    bad = await client.patch("/api/v1/auth/me/ui-mode", headers=_hdr(s["access_token"]),
                             json={"ui_mode": "nonsense"})
    assert bad.status_code == 422


async def test_onboarding_profile_roundtrip_and_completion(client):
    s = await _signup(client)
    tok = s["access_token"]

    empty = await client.get("/api/v1/onboarding/profile", headers=_hdr(tok))
    assert empty.status_code == 200 and empty.json()["exists"] is False

    put = await client.put("/api/v1/onboarding/profile", headers=_hdr(tok), json={
        "company_name": "Nimbus AI", "headquarters_country": "IN",
        "operating_countries": ["IN", "DE", "GB"], "employee_count": 28,
        "industry": "b2b_saas", "sells_to_enterprises": True,
        "develops_ai_products": True, "uses_generative_ai": True, "uses_rag": True,
        "builds_ai_agents": True, "uses_third_party_models": True,
        "ai_providers": ["openai", "anthropic"], "data_types": ["personal", "source_code"],
        "is_saas": True, "sells_software": True, "soc2_required": True, "completed": True,
    })
    assert put.status_code == 200, put.text
    assert put.json()["profile"]["completed"] is True

    me = await client.get("/api/v1/auth/me", headers=_hdr(tok))
    assert me.json()["onboarding_completed"] is True


async def test_company_applicability_is_differentiated_and_explainable(client):
    """Two very different companies must NOT get the same framework exposure."""
    saas = await _signup(client, org="PureSaaS")
    await client.put("/api/v1/onboarding/profile", headers=_hdr(saas["access_token"]), json={
        "headquarters_country": "US", "operating_countries": ["US"], "employee_count": 15,
        "industry": "b2b_saas", "develops_ai_products": True, "uses_generative_ai": True,
        "is_saas": True, "sells_software": True, "data_types": ["personal"],
        "makes_decisions_about_people": False, "completed": True,
    })
    saas_appl = (await client.get("/api/v1/onboarding/applicability", headers=_hdr(saas["access_token"]))).json()

    hw = await _signup(client, org="ConnectedThings")
    await client.put("/api/v1/onboarding/profile", headers=_hdr(hw["access_token"]), json={
        "headquarters_country": "DE", "operating_countries": ["DE", "FR"], "employee_count": 120,
        "industry": "iot", "develops_ai_products": True, "sells_connected_hardware": True,
        "is_iot": True, "has_embedded_software": True, "is_saas": False, "sells_software": True,
        "product_marketed_in_eu": True, "data_types": ["personal"], "completed": True,
    })
    hw_appl = (await client.get("/api/v1/onboarding/applicability", headers=_hdr(hw["access_token"]))).json()

    saas_fw = {e["framework_key"]: e for e in saas_appl["exposures"]}
    hw_fw = {e["framework_key"]: e for e in hw_appl["exposures"]}

    # CRA: directly applicable to the connected-hardware company, not the pure-SaaS one
    assert hw_fw["eu_cra"]["exposure"] == "DIRECTLY_APPLICABLE"
    assert saas_fw.get("eu_cra", {}).get("exposure") in (None, "SUPPLY_CHAIN_INDIRECT")
    assert hw_fw != saas_fw

    # every determination is explainable
    for e in saas_appl["exposures"]:
        assert e["reasoning"] and e["source_reference"] and e["jurisdiction"]
        assert e["regulation_type"] in (
            "LEGAL_REGULATORY", "CERTIFICATION", "VOLUNTARY_FRAMEWORK",
            "SECURITY_BEST_PRACTICE", "CONTRACTUAL",
        )

    # NIST AI RMF must be flagged voluntary, never legal
    rmf = saas_fw["nist_ai_rmf"]
    assert rmf["regulation_type"] == "VOLUNTARY_FRAMEWORK"
    assert rmf["exposure"] == "RECOMMENDED_BEST_PRACTICE"

    assert "disclaimer" in saas_appl


async def test_high_risk_employment_ai_triggers_legal_review(client):
    s = await _signup(client, org="HireBot")
    await client.put("/api/v1/onboarding/profile", headers=_hdr(s["access_token"]), json={
        "headquarters_country": "US", "operating_countries": ["US", "DE"], "employee_count": 40,
        "industry": "hrtech", "develops_ai_products": True, "makes_decisions_about_people": True,
        "decision_domains": ["employment"], "product_marketed_in_eu": True,
        "data_types": ["personal", "employee"], "completed": True,
    })
    appl = (await client.get("/api/v1/onboarding/applicability", headers=_hdr(s["access_token"]))).json()
    fw = {e["framework_key"]: e for e in appl["exposures"]}
    assert fw["eu_ai_act"]["exposure"] == "DIRECTLY_APPLICABLE"
    assert fw["eu_ai_act"]["confidence"] == "LEGAL_REVIEW_REQUIRED"
    assert appl["legal_review_recommended"] is True
    assert "eu_ai_act" in appl["legal_review_frameworks"]


async def test_applicability_decision_is_persisted_and_supersedes(client):
    s = await _signup(client)
    tok = s["access_token"]
    await client.put("/api/v1/onboarding/profile", headers=_hdr(tok), json={
        "operating_countries": ["US"], "develops_ai_products": True, "completed": True,
    })
    a1 = (await client.get("/api/v1/onboarding/applicability", headers=_hdr(tok))).json()
    a2 = (await client.get("/api/v1/onboarding/applicability", headers=_hdr(tok))).json()
    assert a1["decision_id"] and a2["decision_id"] and a1["decision_id"] != a2["decision_id"]


async def test_trust_score_has_no_data_for_fresh_tenant(client):
    s = await _signup(client)
    ts = (await client.get("/api/v1/sme/trust-score", headers=_hdr(s["access_token"]))).json()
    assert ts["has_data"] is False
    assert ts["ai_trust_score"] == 0.0
    assert {d["key"] for d in ts["dimensions"]} == {
        "ai_governance", "ai_security", "privacy", "vendor_risk", "agent_security", "secure_development",
    }
    for d in ts["dimensions"]:
        assert d["basis"]  # every dimension explains its number


async def test_next_actions_reflect_real_gaps(client):
    s = await _signup(client)
    tok = s["access_token"]
    await client.put("/api/v1/onboarding/profile", headers=_hdr(tok), json={
        "operating_countries": ["US"], "develops_ai_products": True,
        "ai_providers": ["openai", "anthropic"], "completed": True,
    })
    na = (await client.get("/api/v1/sme/next-actions", headers=_hdr(tok))).json()
    titles = " ".join(a["title"] for a in na["actions"])
    assert "OpenAI" in titles and "Anthropic" in titles          # declared providers not registered
    assert "Acceptable Use" in titles                            # no policy yet
    assert all(a["bucket"] in ("TODAY", "THIS_WEEK", "NEXT") for a in na["actions"])
    assert all(a["why_it_matters"] and a["steps"] for a in na["actions"])


async def test_new_sme_endpoints_are_tenant_isolated(client):
    a = await _signup(client, org="TenantA")
    b = await _signup(client, org="TenantB")
    await client.put("/api/v1/onboarding/profile", headers=_hdr(a["access_token"]), json={
        "company_name": "TenantA Secret Co", "operating_countries": ["IN"], "completed": True,
    })
    # Tenant B sees ITS OWN empty profile, never Tenant A's
    b_prof = (await client.get("/api/v1/onboarding/profile", headers=_hdr(b["access_token"]))).json()
    assert b_prof["exists"] is False

    # unauthenticated access refused
    assert (await client.get("/api/v1/onboarding/applicability")).status_code == 401
    assert (await client.get("/api/v1/sme/trust-score")).status_code == 401
    assert (await client.get("/api/v1/sme/next-actions")).status_code == 401


async def test_per_system_intake_still_works_unchanged(client):
    """The original per-AI-system applicability flow must be untouched."""
    s = await _signup(client)
    r = await client.post("/api/v1/ai-systems/intake-evaluate", headers=_hdr(s["access_token"]), json={
        "system_name": "Support Bot", "business_purpose": "Answer customer questions",
        "deployment_countries": ["EU"], "is_generative_ai": True, "processes_personal_data": True,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["system_name"] == "Support Bot"
    assert "eu_ai_act_classification" in body and "recommended_frameworks" in body


async def test_starter_packs_and_frameworks_catalog(client):
    s = await _signup(client)
    packs = (await client.get("/api/v1/onboarding/starter-packs", headers=_hdr(s["access_token"]))).json()
    ids = {p["id"] for p in packs["packs"]}
    assert {"b2b_ai_saas", "fintech", "healthtech", "hrtech", "india_it_services", "cra_digital_product"} <= ids

    cat = (await client.get("/api/v1/onboarding/frameworks-catalog", headers=_hdr(s["access_token"]))).json()
    keys = {f["framework_key"] for f in cat["commercial_frameworks"]}
    assert keys == {"soc2", "iso_27001", "iso_42001"}
    for f in cat["commercial_frameworks"]:
        # copyright guard: metadata only, no reproduced standard text
        assert f["content_availability"] == "METADATA_ONLY"
        assert f["licence_status"] == "COPYRIGHTED_CUSTOMER_LICENCE_REQUIRED"
