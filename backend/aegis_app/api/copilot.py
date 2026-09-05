"""
AI Governance Copilot Endpoints.
Rules-based, tenant-data-grounded question-answering with official citations
and zero fabrication (see services/copilot.py for what "rules-based" means
here and how an optional real LLM provider can be enabled).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.models.models import AISystem, CustomerControl, Finding, Vendor, User
from aegis_app.schemas.schemas import CopilotQueryInput, CopilotQueryResponse
from aegis_app.services.copilot import copilot_service
from aegis_app.api.deps import get_current_user

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])

@router.post("/query", response_model=CopilotQueryResponse)
async def query_copilot(
    payload: CopilotQueryInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch current tenant context
    sys_res = await db.execute(select(AISystem).where(AISystem.tenant_id == current_user.tenant_id))
    systems = [{"id": s.id, "name": s.name, "business_unit": s.business_unit, "risk_classification": s.risk_classification, "processes_personal_data": s.processes_personal_data, "is_agentic_ai": s.is_agentic_ai, "kill_switch_implemented": s.kill_switch_implemented} for s in sys_res.scalars().all()]

    ctrl_res = await db.execute(select(CustomerControl).where(CustomerControl.tenant_id == current_user.tenant_id))
    controls = [{"control_id": c.control_id, "status": c.status, "effectiveness": c.effectiveness} for c in ctrl_res.scalars().all()]

    find_res = await db.execute(select(Finding).where(Finding.tenant_id == current_user.tenant_id))
    findings = [{"title": f.title, "severity": f.severity, "status": f.status} for f in find_res.scalars().all()]

    vnd_res = await db.execute(select(Vendor).where(Vendor.tenant_id == current_user.tenant_id))
    vendors = [{"name": v.name, "service_type": v.service_type, "data_retention_days": v.data_retention_days, "risk_rating": v.risk_rating} for v in vnd_res.scalars().all()]

    result = copilot_service.answer_query(
        query=payload.query,
        systems_context=systems,
        controls_context=controls,
        findings_context=findings,
        vendors_context=vendors
    )
    return result
