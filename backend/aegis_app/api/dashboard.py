"""
Executive Dashboard Metrics Endpoints.
Calculates high-level posture, framework readiness, and risk breakdowns.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from aegis_app.core.database import get_db
from aegis_app.core.config import settings
from aegis_app.models.models import AISystem, CustomerControl, Finding, Evidence, EvidenceControlMap, User, Risk, Assessment
from aegis_app.schemas.schemas import DashboardMetricsResponse
from aegis_app.services.scoring import calculate_compliance_scores
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. AI Systems Breakdown
    sys_res = await db.execute(select(AISystem).where(AISystem.tenant_id == current_user.tenant_id))
    systems = sys_res.scalars().all()
    
    total_ai = len(systems)
    high_risk_count = sum(1 for s in systems if "High" in s.risk_classification)
    prohibited_count = sum(1 for s in systems if "Prohibited" in s.risk_classification or "Unacceptable" in s.risk_classification)
    genai_count = sum(1 for s in systems if s.is_generative_ai)
    agentic_count = sum(1 for s in systems if s.is_agentic_ai)

    # 2. Controls & Evidence
    ctrl_res = await db.execute(select(CustomerControl).where(CustomerControl.tenant_id == current_user.tenant_id))
    controls = [{"control_id": c.control_id, "status": c.status, "effectiveness": c.effectiveness} for c in ctrl_res.scalars().all()]
    
    # Evidence counts per control
    ev_map_res = await db.execute(select(EvidenceControlMap.control_id, func.count(EvidenceControlMap.id)).group_by(EvidenceControlMap.control_id))
    evidence_counts = {row[0]: row[1] for row in ev_map_res.all()}
    
    # Evidence items total
    ev_total_res = await db.execute(select(func.count(Evidence.id)).where(Evidence.tenant_id == current_user.tenant_id))
    active_evidence = ev_total_res.scalar() or 0

    # 3. Findings
    find_res = await db.execute(select(Finding).where(Finding.tenant_id == current_user.tenant_id))
    findings = [{"severity": f.severity, "status": f.status} for f in find_res.scalars().all()]
    open_findings = [f for f in findings if f["status"] != "Resolved"]
    critical_findings = sum(1 for f in open_findings if f["severity"] == "Critical")

    # 4. Calculate Scores
    scores = calculate_compliance_scores(controls, evidence_counts, open_findings)

    # 5. Risks distribution
    risk_res = await db.execute(select(Risk).where(Risk.tenant_id == current_user.tenant_id))
    risks = risk_res.scalars().all()
    risk_dist = {}
    for r in risks:
        cat = r.category or "General"
        risk_dist[cat] = risk_dist.get(cat, 0) + 1

    # 6. Framework Readiness - computed ONLY from real per-framework Assessment
    # records (average readiness_percentage across this tenant's assessments
    # for that framework_id). Frameworks with zero assessments are reported
    # separately as "unassessed" rather than assigned a fabricated percentage
    # derived from the unrelated overall score (see spec #23/#34: never reduce
    # compliance to a fake single-number breakdown).
    assess_res = await db.execute(
        select(Assessment.framework_id, Assessment.readiness_percentage)
        .where(Assessment.tenant_id == current_user.tenant_id)
    )
    framework_scores: Dict[str, list] = {}
    for framework_id, readiness in assess_res.all():
        framework_scores.setdefault(framework_id, []).append(readiness)

    fw_name_lookup = {fw["id"]: fw["short_name"] for fw in crosswalk_service.get_frameworks_summary()}
    framework_readiness = {
        fw_name_lookup.get(fid, fid): round(sum(vals) / len(vals), 1)
        for fid, vals in framework_scores.items()
    }

    assessed_ids = set(framework_scores.keys())
    recommended_ids = set()
    for s in systems:
        recommended_ids.update(s.applicable_frameworks or [])
    unassessed_frameworks = sorted(
        fw_name_lookup.get(fid, fid) for fid in (recommended_ids - assessed_ids)
    )

    return DashboardMetricsResponse(
        total_ai_systems=total_ai,
        high_risk_systems_count=high_risk_count,
        prohibited_systems_count=prohibited_count,
        genai_systems_count=genai_count,
        agentic_systems_count=agentic_count,
        overall_readiness_percentage=scores["overall_readiness"],
        implementation_score=scores["implementation_score"],
        evidence_completeness_score=scores["evidence_score"],
        control_effectiveness_score=scores["effectiveness_score"],
        open_findings_count=len(open_findings),
        critical_findings_count=critical_findings,
        active_evidence_artifacts_count=active_evidence,
        framework_readiness=framework_readiness,
        unassessed_frameworks=unassessed_frameworks,
        risk_category_distribution=risk_dist,
        legal_disclaimer=settings.LEGAL_DISCLAIMER
    )
