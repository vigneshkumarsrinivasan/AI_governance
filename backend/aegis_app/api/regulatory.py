"""
Authoritative regulatory content API.

Serves source-traceable frameworks ingested by aegis_app.regulatory. Every
provision links back to its official source, retrieval date and hash. Admin
endpoints (ingest / validate / publish) are RBAC-gated.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from aegis_app.api.deps import get_current_user, require_governance_write
from aegis_app.core.database import get_db
from aegis_app.models.models import User, AuditEvent
from aegis_app.models.regulatory import (
    FrameworkVersion, FrameworkNode, RegulatoryRequirement,
    RegulatorySource, SourceArtifact, FrameworkValidation, SourceChangeEvent,
    RequirementControlMapping,
)
from aegis_app.regulatory.manifest import all_frameworks, get_framework

router = APIRouter(prefix="/regulatory", tags=["Regulatory Content"])


async def _latest_version(db: AsyncSession, key: str) -> Optional[FrameworkVersion]:
    return (await db.execute(
        select(FrameworkVersion).where(FrameworkVersion.framework_key == key)
        .order_by(FrameworkVersion.created_at.desc())
    )).scalars().first()


def _node_dict(n: FrameworkNode) -> Dict[str, Any]:
    return {
        "official_id": n.official_id,
        "node_type": n.node_type,
        "label": n.label,
        "depth": n.depth,
        "path": n.path,
        "source_text": n.source_text,
        "source_text_available": n.source_text_available,
        "platform_summary": n.platform_summary,
        "source_anchor_url": n.source_anchor_url,
        "source_hash": n.source_hash,
        "cross_references": n.cross_references or [],
        "interpretation_label": "OFFICIAL_SOURCE" if n.source_text else "PLATFORM_INTERPRETATION",
    }


# --------------------------------------------------------------------------
# Catalog
# --------------------------------------------------------------------------
@router.get("/frameworks")
async def list_frameworks(db: AsyncSession = Depends(get_db),
                          user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    out = []
    for fw in all_frameworks():
        key = fw["framework_key"]
        fv = await _latest_version(db, key)
        lic = fw.get("licence", {})
        row = {
            "framework_key": key,
            "framework_name": fw["framework_name"],
            "framework_family": fw["framework_family"],
            "authority": fw["authority"],
            "jurisdiction": fw["jurisdiction"],
            "framework_type": fw["framework_type"],
            "version_label": fw["version_label"],
            "canonical_identifier": fw.get("canonical_identifier"),
            "official_url": fw["documents"][0]["official_url"],
            "licence_name": lic.get("licence_name"),
            "licence_status": lic.get("licence_status"),
            "manifest_ingestion_status": fw.get("ingestion_status"),
            "production_status": fv.validation_status if fv else "NOT_INGESTED",
            "published_status": fv.published_status if fv else None,
            "coverage": fv.coverage if fv else {},
            "requirement_count": (fv.ingested_counts or {}).get("requirements", 0) if fv else 0,
            "hierarchy_node_count": (fv.ingested_counts or {}).get("hierarchy_nodes", 0) if fv else 0,
            "blocking_reasons": fv.blocking_reasons if fv else ["not ingested"],
        }
        out.append(row)
    return out


@router.get("/frameworks/{key}")
async def framework_detail(key: str, db: AsyncSession = Depends(get_db),
                           user: User = Depends(get_current_user)) -> Dict[str, Any]:
    fw = get_framework(key)
    if not fw:
        raise HTTPException(404, "framework not in manifest")
    fv = await _latest_version(db, key)
    if not fv:
        return {"framework_key": key, "manifest": fw, "production_status": "NOT_INGESTED",
                "required_source": fw["documents"][0].get("machine_readable_url")
                or fw["documents"][0]["official_url"]}
    roots = (await db.execute(
        select(FrameworkNode).where(FrameworkNode.framework_version_id == fv.id,
                                    FrameworkNode.parent_id.is_(None))
        .order_by(FrameworkNode.ordinal)
    )).scalars().all()
    children = (await db.execute(
        select(FrameworkNode).where(FrameworkNode.framework_version_id == fv.id,
                                    FrameworkNode.depth == 1).order_by(FrameworkNode.ordinal)
    )).scalars().all()
    artifact = (await db.execute(
        select(SourceArtifact).join(RegulatorySource)
        .where(RegulatorySource.framework_key == key)
        .order_by(SourceArtifact.retrieved_at.desc())
    )).scalars().first()
    return {
        "framework_key": key,
        "framework_name": fv.framework_name,
        "authority": fv.authority,
        "jurisdiction": fv.jurisdiction,
        "framework_type": fv.framework_type,
        "version_label": fv.version_label,
        "publication_date": fv.publication_date,
        "effective_date": fv.effective_date,
        "application_dates": fv.application_dates,
        "production_status": fv.validation_status,
        "published_status": fv.published_status,
        "coverage": fv.coverage,
        "expected_counts": fv.expected_counts,
        "ingested_counts": fv.ingested_counts,
        "blocking_reasons": fv.blocking_reasons,
        "licence": fw.get("licence", {}),
        "attribution": fw.get("licence", {}).get("attribution_statement"),
        "source": {
            "official_url": fw["documents"][0]["official_url"],
            "retrieved_url": artifact.retrieved_url if artifact else None,
            "retrieved_at": artifact.retrieved_at.isoformat() if artifact else None,
            "sha256": artifact.sha256 if artifact else None,
            "byte_size": artifact.byte_size if artifact else None,
            "fixture_backed": artifact.fixture_backed if artifact else None,
        },
        "top_level_nodes": [_node_dict(n) for n in (roots + children)],
    }


@router.get("/frameworks/{key}/tree")
async def framework_tree(key: str, db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user)) -> Dict[str, Any]:
    fv = await _latest_version(db, key)
    if not fv:
        raise HTTPException(404, "framework not ingested")
    nodes = (await db.execute(
        select(FrameworkNode).where(FrameworkNode.framework_version_id == fv.id)
        .order_by(FrameworkNode.depth, FrameworkNode.ordinal)
    )).scalars().all()
    by_id = {n.id: {**_node_dict(n), "children": []} for n in nodes}
    roots = []
    for n in nodes:
        d = by_id[n.id]
        if n.parent_id and n.parent_id in by_id:
            by_id[n.parent_id]["children"].append(d)
        else:
            roots.append(d)
    return {"framework_key": key, "version_label": fv.version_label, "tree": roots}


@router.get("/frameworks/{key}/requirements")
async def framework_requirements(key: str, db: AsyncSession = Depends(get_db),
                                 user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    fv = await _latest_version(db, key)
    if not fv:
        raise HTTPException(404, "framework not ingested")
    reqs = (await db.execute(
        select(RegulatoryRequirement).where(RegulatoryRequirement.framework_version_id == fv.id)
        .order_by(RegulatoryRequirement.requirement_key)
    )).scalars().all()
    return [{
        "requirement_key": r.requirement_key,
        "source_reference": r.source_reference,
        "normalized_requirement": r.normalized_requirement,
        "interpretation_label": r.interpretation_label,
        "obligation_type": r.obligation_type,
        "subject_roles": r.subject_roles or [],
        "mandatory": r.mandatory,
        "temporal_state": r.temporal_state,
        "effective_from": r.effective_from,
        "domain": r.domain,
        "evidence_expectations": r.evidence_expectations or [],
        "test_method": r.test_method,
        "review_status": r.review_status,
        "source_text": r.source_text,
        "source_text_available": r.source_text_available,
        "source_anchor_url": r.source_anchor_url,
        "source_hash": r.source_hash,
    } for r in reqs]


@router.get("/requirements/{requirement_key}")
async def requirement_detail(requirement_key: str, db: AsyncSession = Depends(get_db),
                             user: User = Depends(get_current_user)) -> Dict[str, Any]:
    r = (await db.execute(
        select(RegulatoryRequirement).where(RegulatoryRequirement.requirement_key == requirement_key)
        .order_by(RegulatoryRequirement.created_at.desc())
    )).scalars().first()
    if not r:
        raise HTTPException(404, "requirement not found")
    fv = (await db.execute(
        select(FrameworkVersion).where(FrameworkVersion.id == r.framework_version_id))).scalar_one()
    src = (await db.execute(
        select(RegulatorySource).where(RegulatorySource.id == r.source_id))).scalars().first()
    artifact = (await db.execute(
        select(SourceArtifact).where(SourceArtifact.id == r.source_artifact_id))).scalars().first()
    maps = (await db.execute(
        select(RequirementControlMapping).where(RequirementControlMapping.requirement_id == r.id))).scalars().all()
    return {
        "requirement_key": r.requirement_key,
        "framework_key": fv.framework_key,
        "framework_name": fv.framework_name,
        "version_label": fv.version_label,
        "source_reference": r.source_reference,
        "source_parent_reference": r.source_parent_reference,
        "normalized_requirement": r.normalized_requirement,
        "interpretation_label": r.interpretation_label,
        "obligation_type": r.obligation_type,
        "evidence_expectations": r.evidence_expectations or [],
        "test_method": r.test_method,
        "review_status": r.review_status,
        "official_source": {
            "authority": src.authority if src else fv.authority,
            "document_name": src.document_name if src else None,
            "reference": r.source_reference,
            "version": fv.version_label,
            "official_url": r.source_anchor_url or (src.official_url if src else None),
            "retrieved_at": artifact.retrieved_at.isoformat() if artifact else None,
            "sha256": artifact.sha256 if artifact else None,
            "licence_status": src.licence_status if src else None,
            "attribution": src.attribution_statement if src else None,
        },
        "source_text": r.source_text,
        "source_text_available": r.source_text_available,
        "control_mappings": [{
            "control_code": m.control_code, "mapping_type": m.mapping_type,
            "state": m.state, "confidence": m.confidence, "rationale": m.rationale,
        } for m in maps],
    }


@router.get("/frameworks/{key}/validation")
async def framework_validation(key: str, db: AsyncSession = Depends(get_db),
                               user: User = Depends(get_current_user)) -> Dict[str, Any]:
    fv = await _latest_version(db, key)
    if not fv:
        raise HTTPException(404, "framework not ingested")
    checks = (await db.execute(
        select(FrameworkValidation).where(FrameworkValidation.framework_version_id == fv.id)
    )).scalars().all()
    latest_run = max((c.run_id for c in checks), default=None)
    checks = [c for c in checks if c.run_id == latest_run]
    return {
        "framework_key": key,
        "version_label": fv.version_label,
        "production_status": fv.validation_status,
        "coverage": fv.coverage,
        "blocking_reasons": fv.blocking_reasons,
        "checks": [{
            "layer": c.layer, "check": c.check_key, "severity": c.severity,
            "status": c.status, "detail": c.detail,
        } for c in sorted(checks, key=lambda x: (x.layer, x.check_key))],
    }


@router.get("/frameworks/{key}/coverage")
async def framework_coverage(key: str, db: AsyncSession = Depends(get_db),
                             user: User = Depends(get_current_user)) -> Dict[str, Any]:
    fv = await _latest_version(db, key)
    if not fv:
        raise HTTPException(404, "framework not ingested")
    return {"framework_key": key, "version_label": fv.version_label,
            "coverage": fv.coverage, "production_status": fv.validation_status,
            "expected_counts": fv.expected_counts, "ingested_counts": fv.ingested_counts,
            "note": "Coverage is not a compliance score - it measures how completely the "
                    "authoritative source has been ingested, validated and mapped."}


@router.get("/licenses")
async def framework_licenses(db: AsyncSession = Depends(get_db),
                             user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    out = []
    for fw in all_frameworks():
        lic = fw.get("licence", {})
        for doc in fw["documents"]:
            out.append({
                "framework_key": fw["framework_key"],
                "framework_name": fw["framework_name"],
                "authority": fw["authority"],
                "document_name": doc["document_name"],
                "official_url": doc["official_url"],
                "licence_name": lic.get("licence_name"),
                "licence_url": lic.get("licence_url"),
                "licence_status": lic.get("licence_status"),
                "commercial_reuse_allowed": lic.get("commercial_reuse_allowed"),
                "redistribution_allowed": lic.get("redistribution_allowed"),
                "attribution_required": lic.get("attribution_required"),
                "share_alike_required": lic.get("share_alike_required"),
                "attribution_statement": lic.get("attribution_statement"),
            })
    return out


@router.get("/readiness-report")
async def readiness_report(db: AsyncSession = Depends(get_db),
                           user: User = Depends(get_current_user)) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for fw in all_frameworks():
        key = fw["framework_key"]
        lic = fw.get("licence", {})
        fv = await _latest_version(db, key)
        entry: Dict[str, Any] = {
            "framework": fw["framework_name"], "framework_key": key,
            "authority": fw["authority"], "jurisdiction": fw["jurisdiction"],
            "version": fw["version_label"], "canonical_identifier": fw.get("canonical_identifier"),
            "official_source": fw["documents"][0]["official_url"],
            "licence": lic.get("licence_name"), "licence_status": lic.get("licence_status"),
            "attribution": lic.get("attribution_statement"),
            "manifest_ingestion_status": fw.get("ingestion_status"),
        }
        if not fv:
            entry.update({"production_status": "NOT_INGESTED", "requirements": 0,
                          "hierarchy_nodes": 0, "coverage": {},
                          "blocking_reasons": ["not ingested"],
                          "required_source_for_next_step":
                              fw["documents"][0].get("machine_readable_url")
                              or fw["documents"][0]["official_url"]})
        else:
            artifact = (await db.execute(
                select(SourceArtifact).join(RegulatorySource)
                .where(RegulatorySource.framework_key == key)
                .order_by(SourceArtifact.retrieved_at.desc()))).scalars().first()
            n_map = (await db.execute(
                select(func.count(RequirementControlMapping.id)).join(RegulatoryRequirement)
                .where(RegulatoryRequirement.framework_version_id == fv.id))).scalar() or 0
            entry.update({
                "production_status": fv.validation_status,
                "published_status": fv.published_status,
                "version_ingested": fv.version_label,
                "source_sha256": artifact.sha256 if artifact else None,
                "source_retrieved_at": artifact.retrieved_at.isoformat() if artifact else None,
                "hierarchy_nodes": (fv.ingested_counts or {}).get("hierarchy_nodes", 0),
                "requirements": (fv.ingested_counts or {}).get("requirements", 0),
                "control_mappings": n_map,
                "coverage": fv.coverage,
                "expected_counts": fv.expected_counts,
                "blocking_reasons": fv.blocking_reasons,
            })
        rows.append(entry)
    summary = {
        "frameworks_total": len(rows),
        "ingested": sum(1 for r in rows if r["production_status"] != "NOT_INGESTED"),
        "production_ready": sum(1 for r in rows if r["production_status"] == "PRODUCTION_READY"),
        "validated": sum(1 for r in rows if r["production_status"] == "VALIDATED"),
        "verified": sum(1 for r in rows if r["production_status"] == "VERIFIED"),
        "partial": sum(1 for r in rows if r["production_status"] == "PARTIAL"),
        "not_ingested_or_blocked": sum(1 for r in rows
                                       if r["production_status"] in ("NOT_INGESTED", "UNVERIFIED")),
        "licence_unknown": sum(1 for r in rows if r["licence_status"] == "UNKNOWN"),
    }
    return {"summary": summary, "frameworks": rows}


@router.get("/search")
async def regulatory_search(q: str = Query(..., min_length=2), limit: int = 50,
                            db: AsyncSession = Depends(get_db),
                            user: User = Depends(get_current_user)) -> Dict[str, Any]:
    like = f"%{q}%"
    nodes = (await db.execute(
        select(FrameworkNode).where(or_(
            FrameworkNode.official_id.ilike(like),
            FrameworkNode.label.ilike(like),
            FrameworkNode.source_text.ilike(like),
        )).limit(limit)
    )).scalars().all()
    reqs = (await db.execute(
        select(RegulatoryRequirement).where(or_(
            RegulatoryRequirement.requirement_key.ilike(like),
            RegulatoryRequirement.normalized_requirement.ilike(like),
            RegulatoryRequirement.source_text.ilike(like),
        )).limit(limit)
    )).scalars().all()
    fv_ids = {n.framework_version_id for n in nodes} | {r.framework_version_id for r in reqs}
    fmap = {fv.id: fv for fv in (await db.execute(
        select(FrameworkVersion).where(FrameworkVersion.id.in_(fv_ids or ["-"])))).scalars().all()}
    return {
        "query": q,
        "nodes": [{
            "framework_key": fmap[n.framework_version_id].framework_key if n.framework_version_id in fmap else None,
            "official_id": n.official_id, "node_type": n.node_type, "label": n.label,
            "source_anchor_url": n.source_anchor_url,
        } for n in nodes],
        "requirements": [{
            "framework_key": fmap[r.framework_version_id].framework_key if r.framework_version_id in fmap else None,
            "requirement_key": r.requirement_key, "source_reference": r.source_reference,
            "normalized_requirement": r.normalized_requirement,
        } for r in reqs],
    }


# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------
@router.post("/admin/ingest/{key}")
async def admin_ingest(key: str, db: AsyncSession = Depends(get_db),
                       user: User = Depends(require_governance_write)) -> Dict[str, Any]:
    if not get_framework(key):
        raise HTTPException(404, "framework not in manifest")
    from aegis_app.regulatory.db import session_scope
    from aegis_app.regulatory.pipeline import ingest_framework

    def _run():
        with session_scope() as s:
            return ingest_framework(s, key)
    result = await run_in_threadpool(_run)
    db.add(AuditEvent(tenant_id=user.tenant_id, actor_id=user.id, actor_email=user.email,
                      action="REGULATORY_INGEST", object_type="framework", object_id=key,
                      changes={"status": result.get("status")}))
    return result


@router.post("/admin/frameworks/{key}/validate")
async def admin_validate(key: str, db: AsyncSession = Depends(get_db),
                         user: User = Depends(require_governance_write)) -> Dict[str, Any]:
    from aegis_app.regulatory.db import session_scope
    from aegis_app.regulatory.validate import validate_framework_version
    from aegis_app.models.regulatory import FrameworkVersion as FV

    def _run():
        with session_scope() as s:
            fv = s.execute(select(FV).where(FV.framework_key == key)
                           .order_by(FV.created_at.desc())).scalars().first()
            if not fv:
                return {"error": "not ingested"}
            return validate_framework_version(s, fv)
    return await run_in_threadpool(_run)


@router.post("/admin/frameworks/{key}/publish")
async def admin_publish(key: str, force: bool = False, db: AsyncSession = Depends(get_db),
                        user: User = Depends(require_governance_write)) -> Dict[str, Any]:
    fv = await _latest_version(db, key)
    if not fv:
        raise HTTPException(404, "framework not ingested")
    if fv.validation_status != "PRODUCTION_READY" and not force:
        raise HTTPException(409, {
            "message": "framework has not passed the production-readiness gate",
            "production_status": fv.validation_status,
            "blocking_reasons": fv.blocking_reasons,
            "hint": "resolve blockers or call with ?force=true to publish UNDER REVIEW content",
        })
    # demote any previously current version
    prev = (await db.execute(
        select(FrameworkVersion).where(FrameworkVersion.framework_key == key,
                                       FrameworkVersion.is_current.is_(True)))).scalars().all()
    for p in prev:
        p.is_current = False
    fv.published_status = "PUBLISHED"
    fv.is_current = True
    from datetime import datetime, timezone
    fv.published_at = datetime.now(timezone.utc)
    db.add(AuditEvent(tenant_id=user.tenant_id, actor_id=user.id, actor_email=user.email,
                      action="REGULATORY_PUBLISH", object_type="framework_version", object_id=fv.id,
                      changes={"framework_key": key, "version": fv.version_label, "forced": force}))
    return {"framework_key": key, "version_label": fv.version_label,
            "published_status": fv.published_status, "production_status": fv.validation_status}


@router.get("/aiverify/capabilities")
async def aiverify_capabilities(user: User = Depends(get_current_user)) -> Dict[str, Any]:
    from aegis_app.regulatory.aiverify_adapter import STOCK_TESTS, capabilities, AIVERIFY_REPO
    return {
        "repo": AIVERIFY_REPO,
        "capabilities": capabilities(),
        "stock_tests": STOCK_TESTS,
        "note": "Technical tests are run by the AI Verify toolkit; this platform imports/normalizes "
                "their results. A passing result means the system passed the configured tests, "
                "not that it is safe.",
    }


@router.post("/aiverify/import-result")
async def aiverify_import_result(payload: Dict[str, Any], db: AsyncSession = Depends(get_db),
                                 user: User = Depends(require_governance_write)) -> Dict[str, Any]:
    from aegis_app.regulatory.aiverify_adapter import import_result
    try:
        norm = import_result(
            system_id=payload["system_id"], model_ref=payload["model_ref"],
            capability=payload["capability"], result_json=payload["result_json"],
            dataset_ref=payload.get("dataset_ref"),
            test_engine_version=payload.get("test_engine_version"),
            aiverify_repo_ref=payload.get("aiverify_repo_ref"),
        )
    except KeyError as e:
        raise HTTPException(422, f"missing field: {e}")
    db.add(AuditEvent(tenant_id=user.tenant_id, actor_id=user.id, actor_email=user.email,
                      action="AIVERIFY_RESULT_IMPORT", object_type="ai_system",
                      object_id=payload["system_id"], changes={"outcome": norm.outcome}))
    return {"normalized": norm.__dict__, "evidence_payload": norm.as_evidence_payload()}


@router.get("/admin/source-changes")
async def admin_source_changes(db: AsyncSession = Depends(get_db),
                               user: User = Depends(require_governance_write)) -> List[Dict[str, Any]]:
    events = (await db.execute(
        select(SourceChangeEvent).order_by(SourceChangeEvent.detected_at.desc()))).scalars().all()
    srcs = {s.id: s for s in (await db.execute(select(RegulatorySource))).scalars().all()}
    return [{
        "id": e.id,
        "framework_key": srcs[e.source_id].framework_key if e.source_id in srcs else None,
        "detected_at": e.detected_at.isoformat(),
        "change_kind": e.change_kind,
        "previous_sha256": e.previous_sha256,
        "new_sha256": e.new_sha256,
        "status": e.status,
    } for e in events]
