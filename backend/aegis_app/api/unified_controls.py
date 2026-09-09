"""
Unified Control Library + cross-framework coverage API (MOAT 1, 2, 3, 11).

  GET  /unified-controls                      - library enriched with reach + tenant state
  GET  /unified-controls/{code}               - one control: mapped requirements by framework + coverage
  GET  /unified-controls/{code}/history       - append-only assurance history (MOAT 4)
  POST /unified-controls/{code}/status        - set tenant control status (writes history + audit)
  POST /unified-controls/admin/propose-mappings - run the AI mapping proposer (AI_SUGGESTED only)
  GET  /control-mappings                      - list mappings (filter by state / control / framework)
  PUT  /control-mappings/{id}/review          - state transition (MOAT 2 validation workflow)
  GET  /coverage/framework/{key}              - per-requirement coverage for a framework
  GET  /coverage/summary                      - readiness across the tenant's applicable frameworks
  GET  /inheritance  /  POST /inheritance     - shared-scope control reuse (MOAT 3)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_app.core.database import get_db
from aegis_app.api.deps import get_current_user, require_roles
from aegis_app.core import permissions as _perm
from aegis_app.models.models import (
    User, AuditEvent, CustomerControl, ControlEffectivenessEvent, ComplianceInheritance,
    EvidenceControlMap, Evidence, Finding, AISystem,
)
from aegis_app.models.regulatory import (
    RegulatoryRequirement, RequirementControlMapping, FrameworkVersion, MAPPING_STATES,
    AUTHORITATIVE_MAPPING_STATES,
)
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.services import control_mapper, coverage as coverage_svc

router = APIRouter(tags=["Unified Controls & Coverage"])

require_mapping_review = require_roles(sorted(set(_perm.LEGAL_REVIEW) | {"Tenant Admin", "AI Governance Lead", "Compliance Manager", "Auditor"}))
require_control_write = require_roles(_perm.GOVERNANCE_WRITE)


# ---------------------------------------------------------------- library

@router.get("/unified-controls")
async def list_unified_controls(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    tid = current_user.tenant_id
    controls = crosswalk_service.get_unified_controls()

    # reach: authoritative mappings per control -> requirement + framework counts
    reach_rows = (await db.execute(
        select(RequirementControlMapping.control_code, FrameworkVersion.framework_key,
               func.count(RequirementControlMapping.id))
        .join(RegulatoryRequirement, RegulatoryRequirement.id == RequirementControlMapping.requirement_id)
        .join(FrameworkVersion, FrameworkVersion.id == RegulatoryRequirement.framework_version_id)
        .where(RequirementControlMapping.state.in_(AUTHORITATIVE_MAPPING_STATES))
        .group_by(RequirementControlMapping.control_code, FrameworkVersion.framework_key)
    )).all()
    cand_rows = (await db.execute(
        select(RequirementControlMapping.control_code, func.count(RequirementControlMapping.id))
        .where(RequirementControlMapping.state.notin_(AUTHORITATIVE_MAPPING_STATES + ("REJECTED", "DEPRECATED")))
        .group_by(RequirementControlMapping.control_code)
    )).all()
    reach: Dict[str, Dict[str, Any]] = {}
    for code, fk, n in reach_rows:
        r = reach.setdefault(code, {"requirements": 0, "frameworks": set()})
        r["requirements"] += n
        r["frameworks"].add(fk)
    cand = {code: n for code, n in cand_rows}

    cc = {c.control_id: c for c in (await db.execute(select(CustomerControl).where(CustomerControl.tenant_id == tid))).scalars().all()}
    ev_counts = {r[0]: r[1] for r in (await db.execute(
        select(EvidenceControlMap.control_id, func.count(EvidenceControlMap.id))
        .join(Evidence, Evidence.id == EvidenceControlMap.evidence_id)
        .where(Evidence.tenant_id == tid).group_by(EvidenceControlMap.control_id)
    )).all()}

    out = []
    for c in controls:
        r = reach.get(c["code"], {"requirements": 0, "frameworks": set()})
        s = cc.get(c["code"])
        out.append({
            "code": c["code"], "title": c["title"], "domain": c["domain"],
            "objective": c["objective"],
            "reach": {"requirements": r["requirements"], "frameworks": sorted(r["frameworks"]),
                      "candidate_mappings_pending_review": cand.get(c["code"], 0)},
            "tenant_status": s.status if s else "Not Started",
            "tenant_effectiveness": s.effectiveness if s else None,
            "evidence_count": ev_counts.get(c["code"], 0),
        })
    return {"controls": out, "total": len(out)}


@router.get("/unified-controls/{code}")
async def unified_control_detail(code: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    control = next((c for c in crosswalk_service.get_unified_controls() if c["code"] == code), None)
    if not control:
        raise HTTPException(404, "Unified control not found")
    tid = current_user.tenant_id

    rows = (await db.execute(
        select(RequirementControlMapping, RegulatoryRequirement, FrameworkVersion.framework_key, FrameworkVersion.framework_name)
        .join(RegulatoryRequirement, RegulatoryRequirement.id == RequirementControlMapping.requirement_id)
        .join(FrameworkVersion, FrameworkVersion.id == RegulatoryRequirement.framework_version_id)
        .where(RequirementControlMapping.control_code == code)
        .order_by(FrameworkVersion.framework_key)
    )).all()
    by_fw: Dict[str, Dict[str, Any]] = {}
    for m, req, fk, fn in rows:
        g = by_fw.setdefault(fk, {"framework_key": fk, "framework_name": fn, "requirements": []})
        g["requirements"].append({
            "requirement_key": req.requirement_key, "source_reference": req.source_reference,
            "text": (req.normalized_requirement or "")[:220],
            "mapping_type": m.mapping_type, "confidence": m.confidence, "state": m.state,
            "rationale": m.rationale, "mapping_source": m.mapping_source, "mapping_id": m.id,
            "reviewed_by": m.reviewed_by, "source_anchor_url": req.source_anchor_url,
        })

    s = (await db.execute(select(CustomerControl).where(
        CustomerControl.tenant_id == tid, CustomerControl.control_id == code))).scalars().first()
    ev = (await db.execute(
        select(Evidence).join(EvidenceControlMap, EvidenceControlMap.evidence_id == Evidence.id)
        .where(EvidenceControlMap.control_id == code, Evidence.tenant_id == tid)
    )).scalars().all()
    findings = (await db.execute(
        select(Finding).where(Finding.tenant_id == tid, Finding.control_id == code)
    )).scalars().all()
    inh = (await db.execute(
        select(ComplianceInheritance).where(ComplianceInheritance.tenant_id == tid, ComplianceInheritance.control_code == code)
    )).scalars().all()

    return {
        "control": {k: control.get(k) for k in ("code", "title", "domain", "objective", "description",
                    "control_type", "implementation_type", "control_frequency", "risk_addressed",
                    "implementation_guidance", "expected_evidence", "test_procedure")},
        "frameworks": list(by_fw.values()),
        "reach": {
            "requirements": sum(len(g["requirements"]) for g in by_fw.values()),
            "frameworks": len(by_fw),
            "authoritative": sum(1 for g in by_fw.values() for r in g["requirements"] if r["state"] in AUTHORITATIVE_MAPPING_STATES),
        },
        "tenant": {
            "status": s.status if s else "Not Started",
            "effectiveness": s.effectiveness if s else None,
            "owner": s.owner if s else None,
            "notes": s.implementation_notes if s else None,
            "evidence": [{"id": e.id, "title": e.title, "type": e.evidence_type, "approval_status": e.approval_status,
                          "expiry_date": e.expiry_date.isoformat() if e.expiry_date else None} for e in ev],
            "open_findings": [{"id": f.id, "title": f.title, "severity": f.severity, "status": f.status}
                              for f in findings if f.status not in ("Resolved", "Accepted Risk")],
            "inherited": [{"scope": i.source_scope, "ref": i.source_ref, "verified_state": i.verified_state} for i in inh],
        },
    }


@router.get("/unified-controls/{code}/history")
async def control_history(code: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (await db.execute(
        select(ControlEffectivenessEvent)
        .where(ControlEffectivenessEvent.tenant_id == current_user.tenant_id,
               ControlEffectivenessEvent.control_code == code)
        .order_by(ControlEffectivenessEvent.changed_at.desc())
    )).scalars().all()
    return [{"status": r.status, "effectiveness": r.effectiveness, "lifecycle_state": r.lifecycle_state,
             "note": r.note, "changed_by": r.changed_by,
             "changed_at": r.changed_at.isoformat() if r.changed_at else None} for r in rows]


class ControlStatusInput(BaseModel):
    status: str
    effectiveness: Optional[str] = None
    note: Optional[str] = None
    owner: Optional[str] = None


@router.post("/unified-controls/{code}/status")
async def set_control_status(
    code: str, payload: ControlStatusInput,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_control_write),
):
    if not any(c["code"] == code for c in crosswalk_service.get_unified_controls()):
        raise HTTPException(404, "Unified control not found")
    tid = current_user.tenant_id
    s = (await db.execute(select(CustomerControl).where(
        CustomerControl.tenant_id == tid, CustomerControl.control_id == code))).scalars().first()
    if not s:
        s = CustomerControl(tenant_id=tid, organization_id=current_user.organization_id or tid, control_id=code)
        db.add(s)
    before = {"status": s.status, "effectiveness": s.effectiveness}
    s.status = payload.status
    s.effectiveness = payload.effectiveness or s.effectiveness
    if payload.note:
        s.implementation_notes = payload.note
    if payload.owner:
        s.owner = payload.owner

    # append-only history (MOAT 4) - never overwrite
    db.add(ControlEffectivenessEvent(
        tenant_id=tid, organization_id=current_user.organization_id, control_code=code,
        status=s.status, effectiveness=s.effectiveness, note=payload.note,
        changed_by=current_user.full_name,
    ))
    db.add(AuditEvent(
        tenant_id=tid, actor_id=current_user.id, actor_email=current_user.email,
        action="SET_UNIFIED_CONTROL_STATUS", object_type="CustomerControl", object_id=code,
        changes={"before": before, "after": {"status": s.status, "effectiveness": s.effectiveness}},
    ))
    await db.commit()
    return {"code": code, "status": s.status, "effectiveness": s.effectiveness}


# ---------------------------------------------------------------- mapping workflow

@router.post("/unified-controls/admin/propose-mappings")
async def propose_mappings(
    frameworks: Optional[str] = Query(None, description="comma-separated framework keys; blank = all"),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_mapping_review),
):
    fk = [x.strip() for x in frameworks.split(",")] if frameworks else None
    authoritative = await control_mapper.load_authoritative_seed(db)
    seed = await control_mapper.load_crosswalk_seed(db)
    ai = await control_mapper.propose_mappings(db, controls=crosswalk_service.get_unified_controls(), frameworks=fk)
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="PROPOSE_CONTROL_MAPPINGS", object_type="RequirementControlMapping", object_id="(batch)",
        changes={"authoritative": authoritative.get("created"), "seed": seed, "ai_proposed": ai["created"]},
    ))
    await db.commit()
    return {"expert_curated": authoritative, "crosswalk_seed": seed, "ai_proposer": ai,
            "note": "Expert-curated (EXPERT_REVIEWED) and crosswalk (APPROVED) mappings count toward coverage; "
                    "AI-proposed mappings are AI_SUGGESTED and do not count until a reviewer promotes them."}


@router.get("/control-mappings")
async def list_mappings(
    state: Optional[str] = None, control_code: Optional[str] = None, framework: Optional[str] = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    q = (select(RequirementControlMapping, RegulatoryRequirement.requirement_key,
                RegulatoryRequirement.source_reference, FrameworkVersion.framework_key)
         .join(RegulatoryRequirement, RegulatoryRequirement.id == RequirementControlMapping.requirement_id)
         .join(FrameworkVersion, FrameworkVersion.id == RegulatoryRequirement.framework_version_id))
    if state:
        q = q.where(RequirementControlMapping.state == state)
    if control_code:
        q = q.where(RequirementControlMapping.control_code == control_code)
    if framework:
        q = q.where(FrameworkVersion.framework_key == framework)
    q = q.order_by(RequirementControlMapping.confidence.desc()).limit(limit)
    rows = (await db.execute(q)).all()
    counts = {r[0]: r[1] for r in (await db.execute(
        select(RequirementControlMapping.state, func.count(RequirementControlMapping.id))
        .group_by(RequirementControlMapping.state))).all()}
    return {
        "state_counts": counts,
        "mappings": [{
            "id": m.id, "control_code": m.control_code, "requirement_key": rk, "source_reference": sr,
            "framework_key": fk, "mapping_type": m.mapping_type, "confidence": m.confidence,
            "state": m.state, "proposed_by": m.proposed_by, "mapping_source": m.mapping_source,
            "rationale": m.rationale, "reviewed_by": m.reviewed_by,
        } for m, rk, sr, fk in rows],
    }


class MappingReviewInput(BaseModel):
    decision: str = Field(pattern="^(DRAFT|NEEDS_REVIEW|EXPERT_REVIEWED|APPROVED|REJECTED|DEPRECATED)$")
    note: Optional[str] = None
    legal_review_status: Optional[str] = None


@router.put("/control-mappings/{mapping_id}/review")
async def review_mapping(
    mapping_id: str, payload: MappingReviewInput,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_mapping_review),
):
    m = (await db.execute(select(RequirementControlMapping).where(RequirementControlMapping.id == mapping_id))).scalars().first()
    if not m:
        raise HTTPException(404, "Mapping not found")
    before = m.state
    m.state = payload.decision
    m.reviewed_by = current_user.full_name
    m.reviewed_at = datetime.now(timezone.utc)
    m.last_reviewed_at = m.reviewed_at
    if payload.decision == "EXPERT_REVIEWED":
        m.expert_reviewed_by = current_user.full_name
        m.expert_reviewed_at = m.reviewed_at
    if payload.legal_review_status:
        m.legal_review_status = payload.legal_review_status
    if payload.note:
        m.rationale = (m.rationale or "") + f"\n[review {m.reviewed_at.date()}] {payload.note}"
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="REVIEW_CONTROL_MAPPING", object_type="RequirementControlMapping", object_id=m.id,
        changes={"from": before, "to": m.state, "control": m.control_code},
    ))
    await db.commit()
    return {"id": m.id, "state": m.state, "reviewed_by": m.reviewed_by}


# ---------------------------------------------------------------- coverage

@router.get("/coverage/framework/{framework_key}")
async def framework_coverage(
    framework_key: str, status: Optional[str] = None, q: Optional[str] = None, limit: int = 500,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    result = await coverage_svc.framework_coverage(db, current_user.tenant_id, framework_key)
    if status:
        result["requirements"] = [r for r in result["requirements"] if r["status"] == status]
    if q:
        ql = q.lower()
        result["requirements"] = [r for r in result["requirements"]
                                  if ql in r["title"].lower() or ql in (r["source_reference"] or "").lower()]
    result["requirements"] = result["requirements"][:limit]
    return result


@router.get("/coverage/summary")
async def coverage_summary(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    systems = (await db.execute(select(AISystem).where(AISystem.tenant_id == current_user.tenant_id))).scalars().all()
    fks = sorted({fk for s in systems for fk in (s.applicable_frameworks or [])})
    if not fks:
        fks = ["eu_ai_act", "nist_ai_rmf", "gdpr", "owasp_llm"]
    return await coverage_svc.coverage_summary(db, current_user.tenant_id, fks)


# ---------------------------------------------------------------- inheritance (MOAT 3)

class InheritanceInput(BaseModel):
    control_code: str
    source_scope: str = Field(pattern="^(organization|business_unit|vendor|infrastructure|shared_platform)$")
    source_ref: Optional[str] = None
    applicability_note: Optional[str] = None
    verified_state: str = "ASSERTED"
    evidence_ids: List[str] = Field(default_factory=list)


@router.get("/inheritance")
async def list_inheritance(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (await db.execute(
        select(ComplianceInheritance).where(ComplianceInheritance.tenant_id == current_user.tenant_id)
    )).scalars().all()
    return [{"id": r.id, "control_code": r.control_code, "source_scope": r.source_scope,
             "source_ref": r.source_ref, "verified_state": r.verified_state,
             "applies_to_system_id": r.applies_to_system_id, "applicability_note": r.applicability_note,
             "evidence_ids": r.evidence_ids or []} for r in rows]


@router.post("/inheritance", status_code=201)
async def create_inheritance(
    payload: InheritanceInput,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_control_write),
):
    if not any(c["code"] == payload.control_code for c in crosswalk_service.get_unified_controls()):
        raise HTTPException(404, "Unified control not found")
    row = ComplianceInheritance(
        tenant_id=current_user.tenant_id, control_code=payload.control_code,
        source_scope=payload.source_scope, source_ref=payload.source_ref,
        applicability_note=payload.applicability_note, verified_state=payload.verified_state,
        evidence_ids=payload.evidence_ids, created_by=current_user.full_name,
    )
    db.add(row)
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="CREATE_COMPLIANCE_INHERITANCE", object_type="ComplianceInheritance", object_id=payload.control_code,
        changes={"scope": payload.source_scope, "ref": payload.source_ref},
    ))
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "control_code": row.control_code, "source_scope": row.source_scope}
