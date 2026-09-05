"""
Executive Reports API Endpoints.
Outputs structured reports for executive board presentations and audit readiness.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.models.models import AISystem, CustomerControl, Finding, Evidence, Organization, User
from aegis_app.services.scoring import calculate_compliance_scores
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.services.report_generator import generate_executive_compliance_report
from aegis_app.api.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/executive", response_model=Dict[str, Any])
async def get_executive_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_res = await db.execute(select(Organization).where(Organization.tenant_id == current_user.tenant_id))
    org = org_res.scalars().first()
    org_dict = {"name": org.name, "industry": org.industry, "headquarters_country": org.headquarters_country} if org else {}

    sys_res = await db.execute(select(AISystem).where(AISystem.tenant_id == current_user.tenant_id))
    systems = [{"name": s.name, "business_unit": s.business_unit, "ai_technology": s.ai_technology, "model_provider": s.model_provider, "model_name": s.model_name, "risk_classification": s.risk_classification, "eu_ai_act_classification": s.eu_ai_act_classification, "production_status": s.production_status} for s in sys_res.scalars().all()]

    ctrl_res = await db.execute(select(CustomerControl).where(CustomerControl.tenant_id == current_user.tenant_id))
    controls = [{"status": c.status, "effectiveness": c.effectiveness} for c in ctrl_res.scalars().all()]

    ev_res = await db.execute(select(Evidence).where(Evidence.tenant_id == current_user.tenant_id))
    evidence = [{"title": e.title} for e in ev_res.scalars().all()]

    find_res = await db.execute(select(Finding).where(Finding.tenant_id == current_user.tenant_id))
    findings = [{"title": f.title, "severity": f.severity, "status": f.status, "due_date": f.due_date} for f in find_res.scalars().all()]

    scores = calculate_compliance_scores(controls, {}, [f for f in findings if f["status"] != "Resolved"])
    frameworks = crosswalk_service.get_frameworks_summary()

    report = generate_executive_compliance_report(
        organization=org_dict,
        ai_systems=systems,
        scores=scores,
        frameworks=frameworks,
        findings=findings,
        evidence_items=evidence
    )
    return report
