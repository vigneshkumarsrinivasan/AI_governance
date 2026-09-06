"""Three-layer validation engine (spec sections 38, 41, 55, 56, 57).

LAYER 1 SOURCE     - is the content backed by a hashed authoritative artefact + verified licence?
LAYER 2 SEMANTIC   - did the parser preserve a sound hierarchy / identifiers / citations?
LAYER 3 COMPLIANCE - do requirements carry the metadata assessments need?

Writes FrameworkValidation rows, computes coverage fractions, and sets the
framework version's readiness on the spec's vocabulary. Nothing here is allowed
to mark a framework PRODUCTION_READY unless every CRITICAL check passes AND
human-review coverage thresholds are met.
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from aegis_app.regulatory.manifest import get_framework, store_source_text
from aegis_app.models.regulatory import (
    FrameworkVersion, FrameworkNode, RegulatoryRequirement, RegulatoryDefinition,
    RequirementControlMapping, ApplicabilityRule, FrameworkValidation,
)

VERIFIED_REQ_THRESHOLD = 1.0       # spec section 32: scoring requirements must reach VERIFIED
MAPPING_RELEASE_THRESHOLD = 0.80   # spec section 44


def _now():
    return datetime.now(timezone.utc)


def validate_framework_version(session: Session, fv: FrameworkVersion) -> dict:
    run_id = str(uuid.uuid4())
    results: List[FrameworkValidation] = []

    def add(layer, key, severity, ok, detail="", evidence=None):
        results.append(FrameworkValidation(
            framework_version_id=fv.id, run_id=run_id, layer=layer, check_key=key,
            severity=severity, status="PASS" if ok else "FAIL", detail=detail,
            evidence=evidence or {},
        ))

    manifest_entry = get_framework(fv.framework_key) or {}
    licence = manifest_entry.get("licence", {})

    nodes = session.execute(
        select(FrameworkNode).where(FrameworkNode.framework_version_id == fv.id)
    ).scalars().all()
    reqs = session.execute(
        select(RegulatoryRequirement).where(RegulatoryRequirement.framework_version_id == fv.id)
    ).scalars().all()
    defs = session.execute(
        select(RegulatoryDefinition).where(RegulatoryDefinition.framework_version_id == fv.id)
    ).scalars().all()

    req_ids = [r.id for r in reqs]
    mappings = session.execute(
        select(RequirementControlMapping).where(RequirementControlMapping.requirement_id.in_(req_ids or ["-"]))
    ).scalars().all()
    rules = session.execute(
        select(ApplicabilityRule).where(ApplicabilityRule.framework_version_id == fv.id)
    ).scalars().all()

    # ---------------- LAYER 1 : SOURCE ----------------
    has_artifact = any(n.source_artifact_id for n in nodes) or any(r.source_artifact_id for r in reqs)
    add("SOURCE", "source_artifact_present", "CRITICAL", has_artifact,
        "At least one node/requirement is backed by a retrieved SourceArtifact." if has_artifact
        else "No SourceArtifact linked - content is not source-traceable.")

    has_hash = all(n.source_hash is not None for n in nodes)
    add("SOURCE", "node_source_hashes", "ERROR", has_hash,
        "Every node carries a source_hash." if has_hash else "Some nodes missing source_hash.")

    lic_status = licence.get("licence_status", "UNKNOWN")
    operator_supplied = bool(manifest_entry.get("operator_supplied_primary_source"))
    lic_ok = lic_status != "UNKNOWN" or operator_supplied
    add("SOURCE", "licence_verified", "CRITICAL", lic_ok,
        f"licence_status={lic_status}"
        + (" (operator-supplied primary source; redistribution licence review still pending)"
           if operator_supplied and lic_status == "UNKNOWN" else ""),
        {"licence": licence})
    if operator_supplied and lic_status == "UNKNOWN":
        add("SOURCE", "redistribution_licence_review_pending", "WARNING", False,
            "Operator supplied their own copy; a redistribution-licence review is required "
            "before this framework can ship in the commercial product.")

    attr_ok = bool(licence.get("attribution_statement"))
    add("SOURCE", "attribution_present", "ERROR", attr_ok,
        "Attribution statement recorded." if attr_ok else "Missing attribution statement.")

    # text reproduction must match licence
    can_show = store_source_text(fv.framework_key)
    showing_text = any(n.source_text for n in nodes) or any(r.source_text for r in reqs)
    lic_text_ok = can_show or not showing_text
    add("SOURCE", "text_reproduction_within_licence", "CRITICAL", lic_text_ok,
        "Full source text stored only where the licence permits reproduction."
        if lic_text_ok else
        f"Source text stored but licence_status={lic_status} does not permit redistribution.")

    expected = fv.expected_counts or {}
    add("SOURCE", "expected_counts_derived", "ERROR", bool(expected),
        "expected_counts derived from the authoritative source structure." if expected
        else "No expected_counts - cannot reconcile completeness.")

    # reconciliation on structural counts the parser derived from source
    recon_ok = True
    recon_detail = []
    ingested = fv.ingested_counts or {}
    for k, exp in expected.items():
        if k in ("requirements", "hierarchy_nodes"):
            got = ingested.get(k)
            if got is not None and got != exp:
                recon_ok = False
                recon_detail.append(f"{k}: expected {exp}, ingested {got}")
    add("SOURCE", "count_reconciliation", "CRITICAL", recon_ok,
        "; ".join(recon_detail) or "Ingested counts match source-derived expected counts.",
        {"expected": expected, "ingested": ingested})

    # ---------------- LAYER 2 : SEMANTIC ----------------
    dupes = [k for k, c in Counter(n.official_id for n in nodes).items() if c > 1]
    add("SEMANTIC", "no_duplicate_identifiers", "CRITICAL", not dupes,
        f"Duplicate official_id(s): {dupes[:10]}" if dupes else "All node identifiers unique.")

    roots = [n for n in nodes if n.parent_id is None]
    orphans = [n.official_id for n in roots if n.node_type not in ("framework", "release")]
    add("SEMANTIC", "no_orphan_nodes", "ERROR", not orphans,
        f"Orphan (parentless non-root) nodes: {orphans[:10]}" if orphans
        else "Every non-root node has a parent.")

    single_root = len(roots) == 1
    add("SEMANTIC", "single_root", "WARNING", single_root,
        f"{len(roots)} root nodes." if not single_root else "Exactly one root node.")

    req_node_ok = all(r.node_id is not None for r in reqs) if reqs else False
    add("SEMANTIC", "requirements_linked_to_nodes", "ERROR", req_node_ok,
        "Every requirement is linked to a hierarchy node." if req_node_ok
        else f"{sum(1 for r in reqs if r.node_id is None)}/{len(reqs)} requirements not linked to a node.")

    cite_missing = [n.official_id for n in nodes if not n.source_anchor_url][:10]
    add("SEMANTIC", "citations_present", "ERROR", not cite_missing,
        f"Nodes without a source citation URL: {cite_missing}" if cite_missing
        else "Every node has a clickable source citation.")

    req_cite_ok = all(r.source_anchor_url for r in reqs) if reqs else False
    add("SEMANTIC", "requirement_citations_present", "ERROR", req_cite_ok,
        "Every requirement has a source citation URL." if req_cite_ok
        else "Some requirements missing a source citation URL.")

    _TEXT_BEARING = {
        "article", "paragraph", "point", "subpoint", "recital", "subcategory",
        "control", "control_enhancement", "technique", "subtechnique", "risk",
        "task", "mitigation", "case_study", "practice", "rule", "sub_rule",
    }
    _parent_ids = {n.parent_id for n in nodes if n.parent_id}
    # a text-bearing node only *requires* verbatim text if it is a leaf - an
    # Article/Chapter/Technique that only contains numbered sub-provisions is a
    # container and legitimately carries no direct text of its own.
    _ALWAYS_TEXT = {"recital", "definition", "subcategory", "task"}
    text_nodes = [n for n in nodes if n.node_type in _TEXT_BEARING
                  and not (n.extra or {}).get("withdrawn")
                  and (n.id not in _parent_ids or n.node_type in _ALWAYS_TEXT)]
    with_text = [n for n in text_nodes if (n.source_text or "").strip()]
    source_text_cov = (len(with_text) / len(text_nodes)) if text_nodes else 1.0
    text_complete = (not can_show) or source_text_cov >= 0.999
    add("SEMANTIC", "official_source_text_complete", "ERROR", text_complete,
        f"Official source text present on {len(with_text)}/{len(text_nodes)} text-bearing nodes "
        f"({source_text_cov:.0%})." if text_nodes else "No text-bearing nodes.",
        {"missing_examples": [n.official_id for n in text_nodes if not (n.source_text or '').strip()][:10]})

    empty_norm = [r.requirement_key for r in reqs if not (r.normalized_requirement or "").strip()]
    add("SEMANTIC", "requirements_have_text", "CRITICAL", not empty_norm,
        f"Requirements with empty normalized text: {empty_norm[:10]}" if empty_norm
        else "Every requirement has normalized text.")

    # ---------------- LAYER 3 : COMPLIANCE ----------------
    ev_ok = all(r.evidence_expectations for r in reqs) if reqs else False
    add("COMPLIANCE", "evidence_expectations_present", "WARNING", ev_ok,
        "Every requirement carries evidence expectations." if ev_ok
        else f"{sum(1 for r in reqs if not r.evidence_expectations)}/{len(reqs)} requirements lack evidence expectations.")

    test_ok = all(r.test_method for r in reqs) if reqs else False
    add("COMPLIANCE", "test_method_present", "WARNING", test_ok,
        "Every requirement carries a test method." if test_ok else "Some requirements lack a test method.")

    verified = sum(1 for r in reqs if r.review_status in ("VERIFIED", "APPROVED"))
    verified_frac = verified / len(reqs) if reqs else 0.0
    add("COMPLIANCE", "requirements_human_verified", "WARNING", verified_frac >= VERIFIED_REQ_THRESHOLD,
        f"{verified}/{len(reqs)} requirements human-verified "
        f"({verified_frac:.0%}; release gate needs {VERIFIED_REQ_THRESHOLD:.0%}).")

    mapped_reqs = {m.requirement_id for m in mappings if m.state == "APPROVED"}
    mapping_frac = len(mapped_reqs) / len(reqs) if reqs else 0.0
    add("COMPLIANCE", "control_mapping_coverage", "INFO", mapping_frac >= MAPPING_RELEASE_THRESHOLD,
        f"{len(mapped_reqs)}/{len(reqs)} requirements have an APPROVED unified-control mapping ({mapping_frac:.0%}).")

    ruled_reqs = {r.requirement_key for r in rules if r.requirement_key}
    rule_frac = (len(ruled_reqs) / len(reqs)) if reqs else 0.0
    if any(r.requirement_key is None for r in rules):
        rule_frac = max(rule_frac, 1.0 if rules else 0.0)
    add("COMPLIANCE", "applicability_rule_coverage", "INFO", rule_frac > 0,
        f"Applicability rule coverage {rule_frac:.0%} ({len(rules)} rules).")

    # ---------------- coverage & readiness ----------------
    exp_nodes = expected.get("hierarchy_nodes") or len(nodes) or 1
    exp_reqs = expected.get("requirements") or len(reqs) or 1
    passed = sum(1 for r in results if r.status == "PASS")
    coverage = {
        "source": 1.0 if (has_artifact and lic_ok and lic_text_ok) else 0.0,
        "hierarchy": round(min(len(nodes) / exp_nodes, 1.0), 4),
        "requirement_extraction": round(min(len(reqs) / exp_reqs, 1.0), 4),
        "verified_requirements": round(verified_frac, 4),
        "control_mapping": round(mapping_frac, 4),
        "applicability_rule": round(rule_frac, 4),
        "evidence_guidance": round(sum(1 for r in reqs if r.evidence_expectations) / (len(reqs) or 1), 4),
        "source_text": round(source_text_cov, 4),
        "validation": round(passed / len(results), 4),
        "definitions": len(defs),
    }

    crit_fail = [r.check_key for r in results if r.severity == "CRITICAL" and r.status == "FAIL"]
    err_fail = [r.check_key for r in results if r.severity == "ERROR" and r.status == "FAIL"]

    blocking: List[str] = []
    blocking += [f"CRITICAL validation failed: {k}" for k in crit_fail]
    blocking += [f"validation error: {k}" for k in err_fail]
    if coverage["verified_requirements"] < VERIFIED_REQ_THRESHOLD:
        blocking.append(
            f"human requirement verification at {coverage['verified_requirements']:.0%} "
            f"(release gate requires {VERIFIED_REQ_THRESHOLD:.0%})")
    if coverage["control_mapping"] < MAPPING_RELEASE_THRESHOLD:
        blocking.append(
            f"unified-control mapping at {coverage['control_mapping']:.0%} "
            f"(release gate requires {MAPPING_RELEASE_THRESHOLD:.0%})")
    if coverage["applicability_rule"] <= 0:
        blocking.append("no reviewed applicability rules")
    if manifest_entry.get("ingestion_status") in ("SOURCE_RETRIEVAL_BLOCKED", "METADATA_ONLY"):
        blocking.append(f"manifest ingestion_status={manifest_entry.get('ingestion_status')}")

    if crit_fail:
        status = "UNVERIFIED"
    elif err_fail or coverage["hierarchy"] < 0.999 or coverage["requirement_extraction"] < 0.999:
        status = "PARTIAL"
    elif blocking:
        status = "VERIFIED"
    else:
        status = "PRODUCTION_READY"
    # VALIDATED = structurally complete & clean but still needs human sign-off items
    if status == "VERIFIED" and not err_fail and coverage["source"] == 1.0 \
            and coverage["hierarchy"] >= 0.999 and coverage["requirement_extraction"] >= 0.999:
        status = "VALIDATED"

    for r in results:
        session.add(r)
    fv.coverage = coverage
    fv.validation_status = status
    fv.blocking_reasons = blocking
    session.flush()

    return {
        "run_id": run_id,
        "status": status,
        "coverage": coverage,
        "checks": [{"layer": r.layer, "check": r.check_key, "severity": r.severity,
                    "status": r.status, "detail": r.detail} for r in results],
        "critical_failures": crit_fail,
        "error_failures": err_fail,
        "blocking_reasons": blocking,
        "counts": {"nodes": len(nodes), "requirements": len(reqs), "definitions": len(defs),
                   "mappings": len(mappings), "applicability_rules": len(rules)},
    }
