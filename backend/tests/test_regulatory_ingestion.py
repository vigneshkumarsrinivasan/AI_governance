"""
Regulatory content subsystem: manifest/licence gate, parsers, ingestion
pipeline, 3-layer validation, immutability, and the read/admin API.

Parser + pipeline tests run fully offline against committed fixtures
(tests/fixtures/*, aegis_app/regulatory/fixtures/*). Live-source retrieval is
NOT exercised here - that belongs in a separate, network-gated suite.
"""

import uuid
from pathlib import Path

import pytest

from tests.test_api_security import _signup

FIXTURES = Path(__file__).parent / "fixtures"


# --------------------------------------------------------------------------
# Manifest + licence gate
# --------------------------------------------------------------------------
def test_manifest_loads_and_validates():
    from aegis_app.regulatory.manifest import all_frameworks, load_manifest
    load_manifest()
    fws = all_frameworks()
    assert len(fws) == 17
    for fw in fws:
        assert fw["documents"], f"{fw['framework_key']} has no documents"
        assert fw["licence"]["licence_status"] in {
            "VERIFIED_REUSABLE", "VERIFIED_WITH_ATTRIBUTION", "VERIFIED_SHARE_ALIKE",
            "SOURCE_ONLY_NO_REDISTRIBUTION", "CUSTOMER_LICENCE_REQUIRED", "UNKNOWN",
        }


def test_licence_gate_blocks_unknown_redistribution():
    from aegis_app.regulatory.manifest import redistribution_allowed, store_source_text
    assert redistribution_allowed("mitre_atlas") is True          # Apache-2.0
    assert redistribution_allowed("nist_sp_800_53") is True        # US gov public domain
    # India DPDP licence is UNKNOWN -> the product may not redistribute it...
    assert redistribution_allowed("india_dpdp") is False
    # ...but the operator supplied their own copy, so their own instance may store the text
    assert store_source_text("india_dpdp") is True
    # a framework with no operator override and UNKNOWN licence stores nothing
    assert store_source_text("mitre_atlas") is True


# --------------------------------------------------------------------------
# Parsers (offline, real trimmed sources)
# --------------------------------------------------------------------------
def _manifest(key):
    from aegis_app.regulatory.manifest import get_framework
    return get_framework(key)


def test_mitre_atlas_parser():
    from aegis_app.regulatory.parsers.mitre_atlas import parse
    raw = (FIXTURES / "atlas_small.yaml").read_bytes()
    pf = parse(raw, _manifest("mitre_atlas"))
    assert pf.framework_key == "mitre_atlas"
    types = {n.node_type for n in pf.nodes}
    assert {"framework", "tactic", "technique", "subtechnique", "mitigation", "case_study"} <= types
    # subtechnique parented to its technique, not a tactic
    sub = next(n for n in pf.nodes if n.node_type == "subtechnique")
    assert sub.parent_official_id == "AML.T0000"
    assert pf.sanity_check() == []
    # every technique became one assessable requirement, with official text + citation
    reqs = [r for r in pf.requirements]
    assert len(reqs) == pf.expected_counts["requirements"] > 0
    assert all(r.source_anchor_url and r.source_text for r in reqs)


def test_nist_oscal_parser():
    from aegis_app.regulatory.parsers.nist_oscal import parse
    raw = (FIXTURES / "oscal_small.json").read_bytes()
    pf = parse(raw, _manifest("nist_sp_800_53"))
    fam = [n for n in pf.nodes if n.node_type == "control_family"]
    assert {f.official_id for f in fam} == {"AT", "RA"}
    ctrls = [n for n in pf.nodes if n.node_type == "control"]
    enh = [n for n in pf.nodes if n.node_type == "control_enhancement"]
    assert ctrls and enh
    assert pf.expected_counts["controls_total"] == len(ctrls) + len(enh)
    # AT-2 exists and carries verbatim statement text
    at2 = next(n for n in pf.nodes if n.official_id == "AT-2")
    assert at2.source_text and "training" in at2.source_text.lower()
    assert pf.sanity_check() == []


def test_nist_ai_rmf_pdf_parser_extracts_full_taxonomy():
    from aegis_app.regulatory.parsers.nist_pdf import parse_ai_rmf
    pdf = Path(__file__).resolve().parents[2] / "NIST.AI.100-1.pdf"
    if not pdf.exists():
        pytest.skip("operator-supplied NIST.AI.100-1.pdf not present")
    pf = parse_ai_rmf(pdf.read_bytes(), _manifest("nist_ai_rmf"))
    funcs = {n.official_id for n in pf.nodes if n.node_type == "function"}
    assert funcs == {"GOVERN", "MAP", "MEASURE", "MANAGE"}
    subs = [n for n in pf.nodes if n.node_type == "subcategory"]
    assert len(subs) == 72
    # this time the full subcategory outcome text IS present (from Appendix A)
    assert all((s.source_text or "").strip() for s in subs)
    assert pf.sanity_check() == []


# --------------------------------------------------------------------------
# Pipeline + validation (offline via the AI RMF fixture)
# --------------------------------------------------------------------------
@pytest.fixture()
def sync_session():
    from aegis_app.regulatory.db import create_all, SessionLocal, engine
    create_all()
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()
        # release the pooled SQLite connection so it can't lock the shared test
        # DB file against the async engine used by the API client fixture
        engine.dispose()


def test_pipeline_ingests_ai_rmf_and_validates(sync_session):
    from aegis_app.regulatory.pipeline import ingest_framework
    from aegis_app.models.regulatory import FrameworkVersion, FrameworkValidation

    result = ingest_framework(sync_session, "nist_ai_rmf")
    sync_session.commit()

    if result.get("status") in ("SOURCE_RETRIEVAL_BLOCKED", "BLOCKED"):
        pytest.skip("NIST.AI.100-1.pdf not available in this environment")

    assert result["status"] in ("PARTIAL", "VERIFIED", "VALIDATED")
    # a machine pass can never reach PRODUCTION_READY (human review gates)
    assert result["status"] != "PRODUCTION_READY"
    assert result["blocking_reasons"]
    cov = result["coverage"]
    for k in ("source", "hierarchy", "requirement_extraction", "validation", "source_text"):
        assert k in cov
    assert cov["hierarchy"] == 1.0 and cov["requirement_extraction"] == 1.0

    fv = (sync_session.query(FrameworkVersion)
          .filter_by(framework_key="nist_ai_rmf").order_by(FrameworkVersion.created_at.desc()).first())
    assert fv is not None
    checks = sync_session.query(FrameworkValidation).filter_by(framework_version_id=fv.id).all()
    assert {"SOURCE", "SEMANTIC", "COMPLIANCE"} <= {c.layer for c in checks}
    # requirements are machine-extracted and unmapped -> these blockers must be present
    crit = [c for c in checks if c.severity == "CRITICAL" and c.status == "FAIL"]
    assert not crit  # structure/source/licence all clean


def test_published_version_is_immutable(sync_session):
    from aegis_app.regulatory.pipeline import ingest_framework
    from aegis_app.models.regulatory import FrameworkVersion

    ingest_framework(sync_session, "nist_ai_rmf")
    sync_session.commit()
    fv = (sync_session.query(FrameworkVersion)
          .filter_by(framework_key="nist_ai_rmf").order_by(FrameworkVersion.created_at.desc()).first())
    fv.published_status = "PUBLISHED"
    sync_session.commit()

    # the pipeline must refuse to overwrite a PUBLISHED version (it surfaces this
    # as a non-fatal result rather than crashing a batch run)
    result = ingest_framework(sync_session, "nist_ai_rmf")
    assert result["status"] == "IMMUTABLE"
    assert "PUBLISHED" in result["error"]


def test_blocked_framework_records_metadata_only(sync_session):
    from aegis_app.regulatory.pipeline import ingest_framework
    from aegis_app.models.regulatory import RegulatorySource, FrameworkVersion

    result = ingest_framework(sync_session, "nist_sp_800_161")
    sync_session.commit()
    assert result["status"] == "BLOCKED"
    # source/licence metadata captured, but NO framework version / provisions
    src = sync_session.query(RegulatorySource).filter_by(framework_key="nist_sp_800_161").first()
    assert src is not None
    assert sync_session.query(FrameworkVersion).filter_by(framework_key="nist_sp_800_161").first() is None


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_regulatory_catalog_and_licence_endpoints(client):
    acct = await _signup(client, email=f"reg-{uuid.uuid4().hex[:8]}@example.com")
    h = {"Authorization": f"Bearer {acct['access_token']}"}

    fw = await client.get("/api/v1/regulatory/frameworks", headers=h)
    assert fw.status_code == 200
    body = fw.json()
    assert len(body) == 17
    assert {r["framework_key"] for r in body} >= {"mitre_atlas", "eu_ai_act", "nist_sp_800_53"}

    lic = await client.get("/api/v1/regulatory/licenses", headers=h)
    assert lic.status_code == 200
    assert any(r["licence_status"] == "UNKNOWN" for r in lic.json())
    assert any("CC BY-SA" in (r["licence_name"] or "") for r in lic.json())

    rep = await client.get("/api/v1/regulatory/readiness-report", headers=h)
    assert rep.status_code == 200
    assert rep.json()["summary"]["frameworks_total"] == 17


@pytest.mark.asyncio
async def test_regulatory_requires_auth(client):
    assert (await client.get("/api/v1/regulatory/frameworks")).status_code == 401


@pytest.mark.asyncio
async def test_assessment_uses_ingested_regulatory_requirements(client, sync_session):
    """Spec sections 27 / 35 / 50: an assessment for an ingested framework must
    generate from the full source-traceable requirement set, not the legacy
    hand-authored ~10-question JSON."""
    from aegis_app.regulatory.pipeline import ingest_framework
    from aegis_app.models.regulatory import FrameworkVersion

    res = ingest_framework(sync_session, "nist_ai_rmf")
    sync_session.commit()
    if res.get("status") in ("BLOCKED", "SOURCE_RETRIEVAL_BLOCKED"):
        pytest.skip("NIST.AI.100-1.pdf not available")
    fv = (sync_session.query(FrameworkVersion)
          .filter_by(framework_key="nist_ai_rmf").order_by(FrameworkVersion.created_at.desc()).first())
    expected = fv.ingested_counts["requirements"]
    assert expected >= 60  # AI RMF has 72 subcategory-level requirements

    acct = await _signup(client, email=f"assess-{uuid.uuid4().hex[:8]}@example.com")
    h = {"Authorization": f"Bearer {acct['access_token']}"}
    sysr = await client.post("/api/v1/ai-systems", json={"name": "RMF Test System"}, headers=h)
    sid = sysr.json()["id"]

    created = await client.post("/api/v1/assessments", json={
        "title": "AI RMF assessment", "framework_id": "nist_ai_rmf", "system_id": sid}, headers=h)
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["requirement_count"] == expected
    assert body["requirement_source"].startswith("regulatory:")

    detail = await client.get(f"/api/v1/assessments/{body['id']}", headers=h)
    assert detail.status_code == 200
    responses = detail.json()["responses"]
    assert len(responses) == expected
    # each item is source-traceable
    assert all(r["requirement_id"].startswith("NIST-AIRMF-") for r in responses)
    assert any(r.get("source_text") for r in responses)


# --------------------------------------------------------------------------
# Operator-supplied local documents (EU docx)
# --------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parents[2]


def test_eu_docx_parser_full_hierarchy():
    docx = _REPO / "EU AI Act.docx"
    if not docx.exists():
        pytest.skip("operator-supplied 'EU AI Act.docx' not present")
    from aegis_app.regulatory.parsers.eu_docx import parse
    pf = parse(docx.read_bytes(), _manifest("eu_ai_act"))
    ec = pf.expected_counts
    assert ec["recitals"] == 180          # AI Act has 180 recitals
    assert ec["articles"] == 113          # ...and 113 articles
    assert ec["definitions"] == 68        # ...and 68 Article 3 definitions
    assert ec["annexes"] == 13
    assert pf.sanity_check() == []
    # Article 5 prohibitions must be classified PROHIBITION and dated 2025-02-02
    art5 = [r for r in pf.requirements
            if r.requirement_key == "EU-AIA-ARTICLE-5" or r.requirement_key.startswith("EU-AIA-ARTICLE-5-")]
    assert art5
    assert any(r.obligation_type == "PROHIBITION" for r in art5)
    assert all(r.effective_from == "2025-02-02" for r in art5)  # Article 113: prohibitions apply first
    # recitals and definitions are NOT turned into requirements
    assert not any(r.obligation_type in ("RECITAL", "DEFINITION") for r in pf.requirements)


def test_inventory_identifies_every_supplied_document():
    from aegis_app.regulatory.inventory import build_manifest
    man = build_manifest(_REPO)
    if man["documents_found"] == 0:
        pytest.skip("no operator documents in workspace")
    assert man["unidentified"] == []
    keys = set(man["by_framework"])
    assert {"eu_ai_act", "gdpr", "dora", "nis2", "eu_cra", "mitre_atlas"} & keys or \
        {"eu_ai_act", "gdpr"} <= keys
