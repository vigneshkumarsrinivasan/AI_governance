"""
Compliance-inheritance / coverage engine (MOAT 2, 3, 11).

"Govern once. Prove everywhere." A tenant implements a Unified Control ONCE;
this engine computes, per framework requirement, whether that requirement is
covered - and explains exactly why.

Hard rule (MOAT 2): a requirement is NEVER marked covered merely because it is
mapped to a control, or because a sibling framework's requirement is covered.
The mapped control must itself be implemented, effective, freshly evidenced and
free of a blocking finding in THIS tenant.

Only EXPERT_REVIEWED / APPROVED mappings count. AI_SUGGESTED / NEEDS_REVIEW
mappings are surfaced separately as "coverage available after mapping review".
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_app.models.models import (
    CustomerControl, Evidence, EvidenceControlMap, Finding, ComplianceInheritance,
)
from aegis_app.models.regulatory import (
    RegulatoryRequirement, RequirementControlMapping, FrameworkVersion,
    AUTHORITATIVE_MAPPING_STATES,
)
from aegis_app.services.crosswalk import crosswalk_service

_IMPLEMENTED = ("Implemented", "Tested")
_EFFECTIVE = ("Effective", "Partially Effective")
_STRONG_TYPES = ("EXACT", "STRONG")


async def _control_assurance(db: AsyncSession, tenant_id: str) -> Dict[str, Dict[str, Any]]:
    """Per unified-control assurance snapshot for this tenant."""
    unified = {c["code"]: c for c in crosswalk_service.get_unified_controls()}
    out: Dict[str, Dict[str, Any]] = {
        code: {"code": code, "title": c["title"], "domain": c["domain"],
               "status": "Not Started", "effectiveness": None, "implemented": False,
               "effective": False, "evidence": [], "fresh_evidence": False,
               "blocking_findings": 0, "inherited_from": None}
        for code, c in unified.items()
    }

    for cc in (await db.execute(select(CustomerControl).where(CustomerControl.tenant_id == tenant_id))).scalars().all():
        e = out.get(cc.control_id)
        if not e:
            continue
        e["status"] = cc.status
        e["effectiveness"] = cc.effectiveness
        e["implemented"] = cc.status in _IMPLEMENTED
        e["effective"] = cc.effectiveness in _EFFECTIVE

    # inheritance from a shared scope (org policy, vendor assessment, infra config)
    for inh in (await db.execute(
        select(ComplianceInheritance).where(ComplianceInheritance.tenant_id == tenant_id,
                                            ComplianceInheritance.applies_to_system_id.is_(None))
    )).scalars().all():
        e = out.get(inh.control_code)
        if e and not e["implemented"]:
            e["implemented"] = True
            e["inherited_from"] = f"{inh.source_scope}:{inh.source_ref or ''}".rstrip(":")
            if inh.verified_state == "VERIFIED":
                e["effective"] = True

    now = datetime.now(timezone.utc)
    ev_rows = (await db.execute(
        select(EvidenceControlMap.control_id, Evidence.id, Evidence.title,
               Evidence.approval_status, Evidence.expiry_date)
        .join(Evidence, Evidence.id == EvidenceControlMap.evidence_id)
        .where(Evidence.tenant_id == tenant_id)
    )).all()
    for code, eid, title, status, expiry in ev_rows:
        e = out.get(code)
        if not e:
            continue
        exp = expiry
        if exp is not None and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        fresh = status in ("Accepted", "Approved") and (exp is None or exp > now)
        e["evidence"].append({"id": eid, "title": title, "status": status, "fresh": fresh})
        if fresh:
            e["fresh_evidence"] = True

    for f in (await db.execute(
        select(Finding).where(Finding.tenant_id == tenant_id,
                              Finding.status.notin_(("Resolved", "Accepted Risk")),
                              Finding.severity.in_(("Critical", "High")))
    )).scalars().all():
        e = out.get(f.control_id)
        if e:
            e["blocking_findings"] += 1

    return out


async def _current_version(db: AsyncSession, framework_key: str):
    return (await db.execute(
        select(FrameworkVersion).where(FrameworkVersion.framework_key == framework_key)
        .order_by(FrameworkVersion.is_current.desc(), FrameworkVersion.created_at.desc())
    )).scalars().first()


def _requirement_status(mapped: List[Dict[str, Any]]) -> tuple[str, str]:
    """Given the mapped controls' assurance, decide requirement coverage + why."""
    if not mapped:
        return "NOT_MAPPED", "No reviewed Unified Control is mapped to this requirement yet."

    strong = [m for m in mapped if m["mapping_type"] in _STRONG_TYPES]
    consider = strong or mapped

    for m in consider:
        a = m["assurance"]
        if a["implemented"] and a["effective"] and a["fresh_evidence"] and a["blocking_findings"] == 0:
            ev = ", ".join(e["title"] for e in a["evidence"] if e["fresh"])[:160]
            src = f" (inherited from {a['inherited_from']})" if a["inherited_from"] else ""
            return "COVERED", (f"Satisfied via {m['control_code']} ({m['mapping_type']}){src}: "
                               f"implemented, {a['effectiveness'] or 'effective'}, evidence [{ev or '—'}] accepted and current.")

    # partial paths
    impl = [m for m in mapped if m["assurance"]["implemented"]]
    if impl:
        m = impl[0]; a = m["assurance"]
        gaps = []
        if not a["fresh_evidence"]:
            gaps.append("no current accepted evidence")
        if not a["effective"]:
            gaps.append(f"effectiveness is {a['effectiveness'] or 'untested'}")
        if a["blocking_findings"]:
            gaps.append(f"{a['blocking_findings']} open high/critical finding(s)")
        if m["mapping_type"] not in _STRONG_TYPES:
            gaps.append(f"mapping is {m['mapping_type']} only")
        return "PARTIALLY_COVERED", (f"Partly satisfied via {m['control_code']}: implemented, but "
                                     + "; ".join(gaps) + ".")

    codes = ", ".join(m["control_code"] for m in mapped[:4])
    return "NOT_COVERED", f"Mapped to {codes} but that control is not implemented in this company."


async def framework_coverage(db: AsyncSession, tenant_id: str, framework_key: str) -> Dict[str, Any]:
    fv = await _current_version(db, framework_key)
    if not fv:
        return {"framework_key": framework_key, "available": False,
                "reason": "This framework is not ingested (no source-traceable requirements).",
                "requirements": [], "summary": {}}

    assurance = await _control_assurance(db, tenant_id)

    reqs = (await db.execute(
        select(RegulatoryRequirement).where(RegulatoryRequirement.framework_version_id == fv.id)
        .order_by(RegulatoryRequirement.requirement_key)
    )).scalars().all()
    req_ids = [r.id for r in reqs]

    maps = (await db.execute(
        select(RequirementControlMapping).where(RequirementControlMapping.requirement_id.in_(req_ids))
    )).scalars().all()
    auth_by_req: Dict[str, List[Any]] = {}
    cand_by_req: Dict[str, List[Any]] = {}
    for m in maps:
        (auth_by_req if m.state in AUTHORITATIVE_MAPPING_STATES else cand_by_req).setdefault(m.requirement_id, []).append(m)

    items = []
    counts = {"COVERED": 0, "PARTIALLY_COVERED": 0, "NOT_COVERED": 0, "NOT_MAPPED": 0}
    for r in reqs:
        mapped = [
            {"control_code": m.control_code, "mapping_type": m.mapping_type,
             "confidence": m.confidence, "assurance": assurance.get(m.control_code,
                {"implemented": False, "effective": False, "fresh_evidence": False,
                 "blocking_findings": 0, "evidence": [], "effectiveness": None, "inherited_from": None})}
            for m in auth_by_req.get(r.id, [])
        ]
        status, why = _requirement_status(mapped)
        counts[status] = counts.get(status, 0) + 1
        items.append({
            "requirement_key": r.requirement_key,
            "source_reference": r.source_reference,
            "title": (r.normalized_requirement or "")[:180],
            "obligation_type": r.obligation_type,
            "domain": r.domain,
            "status": status,
            "explanation": why,
            "via_controls": [m["control_code"] for m in mapped],
            "candidate_controls": sorted({m.control_code for m in cand_by_req.get(r.id, [])}),
        })

    total = len(reqs)
    mapped_total = total - counts["NOT_MAPPED"]
    covered_pct = round(100 * counts["COVERED"] / total, 1) if total else 0.0
    readiness = round(100 * (counts["COVERED"] + 0.5 * counts["PARTIALLY_COVERED"]) / total, 1) if total else 0.0

    return {
        "framework_key": framework_key,
        "framework_name": fv.framework_name,
        "version_label": fv.version_label,
        "available": True,
        "requirements": items,
        "summary": {
            "total_requirements": total,
            "mapped_requirements": mapped_total,
            "mapping_coverage_pct": round(100 * mapped_total / total, 1) if total else 0.0,
            "covered": counts["COVERED"],
            "partially_covered": counts["PARTIALLY_COVERED"],
            "not_covered": counts["NOT_COVERED"],
            "not_mapped": counts["NOT_MAPPED"],
            "covered_pct": covered_pct,
            "readiness_pct": readiness,
            "candidate_mappings_pending_review": sum(1 for r in reqs if r.id in cand_by_req and r.id not in auth_by_req),
        },
    }


async def coverage_summary(db: AsyncSession, tenant_id: str, framework_keys: List[str]) -> Dict[str, Any]:
    per = []
    for fk in framework_keys:
        c = await framework_coverage(db, tenant_id, fk)
        if c["available"]:
            per.append({"framework_key": fk, "framework_name": c["framework_name"], **c["summary"]})
    if per:
        overall = round(sum(p["readiness_pct"] for p in per) / len(per), 1)
    else:
        overall = 0.0
    # explainability
    reasons = []
    total_notmapped = sum(p["not_mapped"] for p in per)
    total_notcov = sum(p["not_covered"] for p in per)
    total_partial = sum(p["partially_covered"] for p in per)
    if total_notcov:
        reasons.append(f"{total_notcov} mapped requirement(s) have an unimplemented control")
    if total_partial:
        reasons.append(f"{total_partial} requirement(s) are partially covered (missing evidence / effectiveness / open finding)")
    if total_notmapped:
        reasons.append(f"{total_notmapped} requirement(s) have no reviewed control mapping yet")
    return {
        "overall_readiness_pct": overall,
        "frameworks": per,
        "explanation": reasons or ["All applicable requirements are covered."],
    }


async def evidence_reuse(db: AsyncSession, tenant_id: str, evidence_id: str) -> Dict[str, Any]:
    """MOAT 3 - how far one evidence object reaches: controls, requirements,
    frameworks, AI systems."""
    ev = (await db.execute(
        select(Evidence).where(Evidence.id == evidence_id, Evidence.tenant_id == tenant_id)
    )).scalars().first()
    if not ev:
        return {"found": False}

    control_codes = (await db.execute(
        select(EvidenceControlMap.control_id).where(EvidenceControlMap.evidence_id == evidence_id)
    )).scalars().all()
    control_codes = sorted(set(control_codes))

    maps = (await db.execute(
        select(RequirementControlMapping, FrameworkVersion.framework_key, FrameworkVersion.framework_name)
        .join(RegulatoryRequirement, RegulatoryRequirement.id == RequirementControlMapping.requirement_id)
        .join(FrameworkVersion, FrameworkVersion.id == RegulatoryRequirement.framework_version_id)
        .where(RequirementControlMapping.control_code.in_(control_codes),
               RequirementControlMapping.state.in_(AUTHORITATIVE_MAPPING_STATES))
    )).all() if control_codes else []

    frameworks = {}
    req_ids = set()
    for m, fk, fn in maps:
        frameworks[fk] = fn
        req_ids.add(m.requirement_id)

    # AI systems whose applicable_frameworks intersect
    from aegis_app.models.models import AISystem
    systems = (await db.execute(select(AISystem).where(AISystem.tenant_id == tenant_id))).scalars().all()
    touched_systems = [s.name for s in systems if set(s.applicable_frameworks or []) & set(frameworks.keys())]

    return {
        "found": True,
        "evidence_id": evidence_id,
        "title": ev.title,
        "approval_status": ev.approval_status,
        "supports": {
            "unified_controls": len(control_codes),
            "control_codes": control_codes,
            "requirements": len(req_ids),
            "frameworks": len(frameworks),
            "framework_names": list(frameworks.values()),
            "ai_systems": len(touched_systems),
            "ai_system_names": touched_systems[:20],
        },
    }
