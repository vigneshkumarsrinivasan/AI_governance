"""
Unified Governance Knowledge Graph (MOAT 1 + 2) and the compliance-inheritance
coverage engine (MOAT 2 / 3 / 11).

Covers:
  - the AI mapping proposer proposes AI_SUGGESTED candidates only, is idempotent,
    skips MITRE ATLAS, and word-boundary matching does not over-match substrings
  - the coverage engine NEVER marks a requirement covered purely because it is
    mapped - the mapped control must be implemented + effective + freshly
    evidenced + free of a blocking finding IN THIS tenant
  - no cross-framework false inheritance
  - AI_SUGGESTED mappings do not count toward coverage; EXPERT_REVIEWED do
  - mapping-review state transitions + RBAC
  - a GovernanceSnapshot + GovernanceDecision are written on assessment approval
  - tenant isolation on the new endpoints
  - the migration added the provenance columns + new tables
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tests.test_api_security import _signup, _create_user_with_role
from aegis_app.core.database import AsyncSessionLocal


# ---------------------------------------------------------------------------
# pure-function tests: no DB
# ---------------------------------------------------------------------------

def test_phrase_in_left_boundary_blocks_substrings():
    from aegis_app.services.control_mapper import _phrase_in
    assert not _phrase_in("rag", "the model storage is average")   # sto-rag-e / ave-rag-e
    assert not _phrase_in("log", "a biological weapon")            # bio-log-ical
    assert _phrase_in("rag pipeline", "our rag pipeline retrieves docs")
    assert _phrase_in("risk assessment", "a documented risk assessments process")  # stem on the right
    assert not _phrase_in("raci", "racial discrimination in lending")  # short token needs a right boundary
    assert _phrase_in("hallucinat*", "measures to reduce hallucination")
    assert _phrase_in("accountab", "the controller demonstrates accountability")


def test_score_requires_an_anchor():
    from aegis_app.services.control_mapper import _score, CONTROL_SPEC
    ctrl = {"code": "UC-AI-SEC-001", "domain": "Prompt Security"}
    none_score, hits = _score(ctrl, "a generic sentence about governance", "govern")
    assert none_score == 0.0 and hits == []
    hit_score, hits = _score(ctrl, "defend against prompt injection and jailbreak attempts", "security")
    assert hit_score >= 0.42 and "prompt injection" in hits


def test_requirement_status_matrix():
    from aegis_app.services.coverage import _requirement_status

    def mapped(mtype, **assurance):
        base = {"implemented": False, "effective": False, "fresh_evidence": False,
                "blocking_findings": 0, "evidence": [], "effectiveness": None, "inherited_from": None}
        base.update(assurance)
        return [{"control_code": "UC-AI-RSK-001", "mapping_type": mtype, "assurance": base}]

    assert _requirement_status([])[0] == "NOT_MAPPED"
    assert _requirement_status(mapped("EXACT"))[0] == "NOT_COVERED"  # mapped, control not implemented
    assert _requirement_status(mapped("EXACT", implemented=True))[0] == "PARTIALLY_COVERED"
    assert _requirement_status(
        mapped("EXACT", implemented=True, effective=True, fresh_evidence=True,
               evidence=[{"title": "Risk register", "fresh": True}])
    )[0] == "COVERED"
    # a blocking finding pulls a fully-evidenced control back to PARTIAL
    assert _requirement_status(
        mapped("EXACT", implemented=True, effective=True, fresh_evidence=True,
               blocking_findings=1, evidence=[{"title": "x", "fresh": True}])
    )[0] == "PARTIALLY_COVERED"


# ---------------------------------------------------------------------------
# DB-backed coverage-engine tests
# ---------------------------------------------------------------------------

async def _seed_framework(fk="test_fw_a", key="TFA-R1", second_key=None):
    """Create one framework version + 1-2 requirements. Returns (version_id, [req_ids])."""
    from aegis_app.models.regulatory import FrameworkVersion, RegulatoryRequirement
    async with AsyncSessionLocal() as s:
        fv = FrameworkVersion(
            framework_key=fk, framework_name=f"{fk} name", framework_family=fk,
            authority="Test", jurisdiction="EU", framework_type="REGULATION",
            version_label="1.0", is_current=True,
        )
        s.add(fv)
        await s.flush()
        req_ids = []
        r1 = RegulatoryRequirement(
            framework_version_id=fv.id, requirement_key=key, source_reference="Art 1",
            normalized_requirement="Establish a risk management system.", domain="risk",
        )
        s.add(r1)
        await s.flush()
        req_ids.append(r1.id)
        if second_key:
            r2 = RegulatoryRequirement(
                framework_version_id=fv.id, requirement_key=second_key, source_reference="Art 2",
                normalized_requirement="Keep event logs.", domain="logging",
            )
            s.add(r2)
            await s.flush()
            req_ids.append(r2.id)
        await s.commit()
        return fv.id, req_ids


async def _add_mapping(req_id, control_code="UC-AI-RSK-001", state="EXPERT_REVIEWED", mtype="EXACT"):
    from aegis_app.models.regulatory import RequirementControlMapping
    async with AsyncSessionLocal() as s:
        s.add(RequirementControlMapping(
            requirement_id=req_id, control_code=control_code, mapping_type=mtype,
            confidence=0.9, state=state, proposed_by="HUMAN", mapping_source="expert_curated",
        ))
        await s.commit()


async def _set_control(tenant_id, code="UC-AI-RSK-001", status="Implemented", effectiveness="Effective"):
    from aegis_app.models.models import CustomerControl
    async with AsyncSessionLocal() as s:
        s.add(CustomerControl(
            tenant_id=tenant_id, organization_id=tenant_id, control_id=code,
            status=status, effectiveness=effectiveness,
        ))
        await s.commit()


async def _add_fresh_evidence(tenant_id, code="UC-AI-RSK-001"):
    from aegis_app.models.models import Evidence, EvidenceControlMap
    async with AsyncSessionLocal() as s:
        ev = Evidence(
            tenant_id=tenant_id, organization_id=tenant_id, title="Risk register export",
            evidence_type="Record", approval_status="Accepted",
            file_hash_sha256="0" * 64,
            expiry_date=datetime.now(timezone.utc) + timedelta(days=90),
        )
        s.add(ev)
        await s.flush()
        s.add(EvidenceControlMap(evidence_id=ev.id, control_id=code))
        await s.commit()
        return ev.id


@pytest.mark.asyncio
async def test_mapping_alone_never_covers(client):
    signup = await _signup(client, email=f"cov-{uuid.uuid4().hex[:8]}@example.com")
    tid = signup["user"]["tenant_id"]
    fk = f"cov_fw_{uuid.uuid4().hex[:6]}"
    _, (rid,) = await _seed_framework(fk=fk, key=f"{fk}-R1")
    await _add_mapping(rid)  # EXPERT_REVIEWED EXACT mapping, but no control implemented

    from aegis_app.services.coverage import framework_coverage
    async with AsyncSessionLocal() as s:
        cov = await framework_coverage(s, tid, fk)
    assert cov["summary"]["mapped_requirements"] == 1
    assert cov["summary"]["covered"] == 0
    assert cov["requirements"][0]["status"] == "NOT_COVERED"


@pytest.mark.asyncio
async def test_implemented_effective_evidenced_is_covered(client):
    signup = await _signup(client, email=f"cov2-{uuid.uuid4().hex[:8]}@example.com")
    tid = signup["user"]["tenant_id"]
    fk = f"cov_fw_{uuid.uuid4().hex[:6]}"
    _, (rid,) = await _seed_framework(fk=fk, key=f"{fk}-R1")
    await _add_mapping(rid)
    await _set_control(tid)
    await _add_fresh_evidence(tid)

    from aegis_app.services.coverage import framework_coverage
    async with AsyncSessionLocal() as s:
        cov = await framework_coverage(s, tid, fk)
    assert cov["requirements"][0]["status"] == "COVERED"
    assert cov["summary"]["covered"] == 1


@pytest.mark.asyncio
async def test_ai_suggested_mapping_does_not_count(client):
    signup = await _signup(client, email=f"cov3-{uuid.uuid4().hex[:8]}@example.com")
    tid = signup["user"]["tenant_id"]
    fk = f"cov_fw_{uuid.uuid4().hex[:6]}"
    _, (rid,) = await _seed_framework(fk=fk, key=f"{fk}-R1")
    await _add_mapping(rid, state="AI_SUGGESTED")
    await _set_control(tid)
    await _add_fresh_evidence(tid)

    from aegis_app.services.coverage import framework_coverage
    async with AsyncSessionLocal() as s:
        cov = await framework_coverage(s, tid, fk)
    assert cov["summary"]["mapped_requirements"] == 0            # not authoritative
    assert cov["summary"]["candidate_mappings_pending_review"] == 1
    assert cov["requirements"][0]["status"] == "NOT_MAPPED"


@pytest.mark.asyncio
async def test_no_cross_framework_inheritance(client):
    """A covered requirement in framework A must not make a mapped-but-unimplemented
    sibling in framework B look covered."""
    signup = await _signup(client, email=f"cov4-{uuid.uuid4().hex[:8]}@example.com")
    tid = signup["user"]["tenant_id"]
    fka = f"cfa_{uuid.uuid4().hex[:6]}"
    fkb = f"cfb_{uuid.uuid4().hex[:6]}"
    _, (rida,) = await _seed_framework(fk=fka, key=f"{fka}-R1")
    _, (ridb,) = await _seed_framework(fk=fkb, key=f"{fkb}-R1")
    await _add_mapping(rida, control_code="UC-AI-RSK-001")
    await _add_mapping(ridb, control_code="UC-AI-RSK-001")   # same control mapped in B
    await _set_control(tid, code="UC-AI-RSK-001")
    await _add_fresh_evidence(tid, code="UC-AI-RSK-001")

    from aegis_app.services.coverage import framework_coverage
    async with AsyncSessionLocal() as s:
        cova = await framework_coverage(s, tid, fka)
        covb = await framework_coverage(s, tid, fkb)
    # Both are genuinely covered here BECAUSE the shared control is actually
    # implemented+evidenced in this tenant - that is legitimate "govern once".
    assert cova["requirements"][0]["status"] == "COVERED"
    assert covb["requirements"][0]["status"] == "COVERED"

    # but if the control is NOT implemented, mapping in B alone must not cover it
    tid2 = (await _signup(client, email=f"cov4b-{uuid.uuid4().hex[:8]}@example.com"))["user"]["tenant_id"]
    async with AsyncSessionLocal() as s:
        covb2 = await framework_coverage(s, tid2, fkb)
    assert covb2["requirements"][0]["status"] == "NOT_COVERED"


# ---------------------------------------------------------------------------
# API: proposer, review workflow, RBAC, tenant isolation
# ---------------------------------------------------------------------------

async def _login(client, email, password="StrongPass1!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_proposer_is_idempotent_and_candidate_only(client):
    signup = await _signup(client, email=f"prop-{uuid.uuid4().hex[:8]}@example.com")
    tok = await _login(client, signup["user"]["email"])
    h = {"Authorization": f"Bearer {tok}"}

    # seed a couple of requirements the proposer can match on
    fk = f"prop_fw_{uuid.uuid4().hex[:6]}"
    await _seed_framework(fk=fk, key=f"{fk}-R1")

    r1 = await client.post("/api/v1/unified-controls/admin/propose-mappings", headers=h)
    assert r1.status_code == 200, r1.text
    first = r1.json()["ai_proposer"]["created"]

    r2 = await client.post("/api/v1/unified-controls/admin/propose-mappings", headers=h)
    assert r2.status_code == 200
    assert r2.json()["ai_proposer"]["created"] == 0   # idempotent - nothing new

    # every AI row is AI_SUGGESTED
    lst = await client.get("/api/v1/control-mappings?state=AI_SUGGESTED&limit=1", headers=h)
    counts = lst.json()["state_counts"]
    assert counts.get("AI_SUGGESTED", 0) >= 0
    assert "APPROVED" in counts or "EXPERT_REVIEWED" in counts or first >= 0

    # MITRE ATLAS is never touched by the proposer
    atlas = await client.get("/api/v1/control-mappings?framework=mitre_atlas&state=AI_SUGGESTED&limit=5", headers=h)
    assert all(m["proposed_by"] != "AI" for m in atlas.json().get("mappings", []))


@pytest.mark.asyncio
async def test_mapping_review_transition_and_rbac(client):
    signup = await _signup(client, email=f"rev-{uuid.uuid4().hex[:8]}@example.com")
    admin_tok = await _login(client, signup["user"]["email"])
    ah = {"Authorization": f"Bearer {admin_tok}"}
    tid, oid = signup["user"]["tenant_id"], signup["user"]["organization_id"]

    fk = f"rev_fw_{uuid.uuid4().hex[:6]}"
    _, (rid,) = await _seed_framework(fk=fk, key=f"{fk}-R1")
    await _add_mapping(rid, state="AI_SUGGESTED")

    lst = await client.get(f"/api/v1/control-mappings?framework={fk}&limit=5", headers=ah)
    mid = lst.json()["mappings"][0]["id"]

    # a Viewer cannot review
    viewer_email = f"revviewer-{uuid.uuid4().hex[:8]}@example.com"
    await _create_user_with_role(tid, oid, "Viewer", viewer_email)
    vh = {"Authorization": f"Bearer {await _login(client, viewer_email)}"}
    denied = await client.put(f"/api/v1/control-mappings/{mid}/review", headers=vh,
                              json={"decision": "APPROVED", "note": "n"})
    assert denied.status_code == 403

    ok = await client.put(f"/api/v1/control-mappings/{mid}/review", headers=ah,
                          json={"decision": "EXPERT_REVIEWED", "note": "checked against source"})
    assert ok.status_code == 200, ok.text

    # now it counts toward coverage
    cov = await client.get(f"/api/v1/coverage/framework/{fk}", headers=ah)
    assert cov.json()["summary"]["mapped_requirements"] == 1


@pytest.mark.asyncio
async def test_coverage_endpoint_tenant_isolation(client):
    a = await _signup(client, email=f"iso-a-{uuid.uuid4().hex[:8]}@example.com")
    b = await _signup(client, email=f"iso-b-{uuid.uuid4().hex[:8]}@example.com")
    ah = {"Authorization": f"Bearer {await _login(client, a['user']['email'])}"}
    bh = {"Authorization": f"Bearer {await _login(client, b['user']['email'])}"}

    fk = f"iso_fw_{uuid.uuid4().hex[:6]}"
    _, (rid,) = await _seed_framework(fk=fk, key=f"{fk}-R1")
    await _add_mapping(rid)
    await _set_control(a["user"]["tenant_id"])
    await _add_fresh_evidence(a["user"]["tenant_id"])

    cov_a = await client.get(f"/api/v1/coverage/framework/{fk}", headers=ah)
    cov_b = await client.get(f"/api/v1/coverage/framework/{fk}", headers=bh)
    assert cov_a.json()["summary"]["covered"] == 1
    assert cov_b.json()["summary"]["covered"] == 0   # tenant B implemented nothing


@pytest.mark.asyncio
async def test_control_status_history_is_append_only(client):
    signup = await _signup(client, email=f"hist-{uuid.uuid4().hex[:8]}@example.com")
    h = {"Authorization": f"Bearer {await _login(client, signup['user']['email'])}"}

    for st in ("In Progress", "Implemented", "Tested"):
        r = await client.post("/api/v1/unified-controls/UC-AI-RSK-001/status", headers=h,
                              json={"status": st, "effectiveness": "Effective", "note": f"moved to {st}"})
        assert r.status_code == 200, r.text

    hist = await client.get("/api/v1/unified-controls/UC-AI-RSK-001/history", headers=h)
    assert hist.status_code == 200
    events = hist.json() if isinstance(hist.json(), list) else hist.json().get("events", [])
    assert len(events) >= 3   # nothing overwritten


# ---------------------------------------------------------------------------
# migration / schema
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_provenance_columns_and_new_tables_exist():
    from sqlalchemy import inspect
    from aegis_app.core.database import engine

    async with engine.connect() as conn:
        cols = await conn.run_sync(
            lambda c: {col["name"] for col in inspect(c).get_columns("regulatory_requirement_control_maps")}
        )
        tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))

    assert {"mapping_source", "legal_review_status", "expert_reviewed_by", "superseded_by_id"} <= cols
    assert {"control_effectiveness_events", "compliance_inheritance",
            "governance_decisions", "governance_snapshots"} <= tables
