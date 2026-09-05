"""
Risk Register, Findings, and Remediation Management Endpoints.
Supports inherent vs residual risk scoring, MITRE ATLAS / OWASP mapping,
and SLA task tracking.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aegis_app.core.database import get_db
from aegis_app.models.models import Risk, Finding, RemediationTask, User, AuditEvent, AISystem
from aegis_app.schemas.schemas import RiskCreate, RiskResponse, FindingResponse
from aegis_app.api.deps import get_current_user, require_governance_write, require_risk_acceptance

router = APIRouter(prefix="", tags=["Risk & Remediation"])

@router.get("/risks", response_model=List[RiskResponse])
async def list_risks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Risk)
        .where(Risk.tenant_id == current_user.tenant_id)
        .options(selectinload(Risk.ai_system))
        .order_by(Risk.inherent_score.desc())
    )
    risks = result.scalars().all()
    return [
        RiskResponse(
            id=r.id,
            risk_code=r.risk_code,
            title=r.title,
            description=r.description,
            category=r.category,
            system_id=r.system_id,
            system_name=r.ai_system.name if r.ai_system else "Enterprise",
            inherent_score=r.inherent_score,
            residual_score=r.residual_score,
            treatment=r.treatment,
            status=r.status,
            owner=r.owner,
            mitre_atlas_technique=r.mitre_atlas_technique,
            owasp_category=r.owasp_category,
            created_at=r.created_at
        )
        for r in risks
    ]

@router.post("/risks", response_model=Dict[str, Any])
async def create_risk(
    payload: RiskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    inherent_score = payload.inherent_likelihood * payload.inherent_impact
    residual_score = max(1, int(inherent_score * 0.4))
    
    risk = Risk(
        tenant_id=current_user.tenant_id,
        organization_id=current_user.organization_id or current_user.tenant_id,
        system_id=payload.system_id,
        risk_code=payload.risk_code,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        threat_source=payload.threat_source,
        inherent_likelihood=payload.inherent_likelihood,
        inherent_impact=payload.inherent_impact,
        inherent_score=inherent_score,
        residual_likelihood=1,
        residual_impact=2,
        residual_score=residual_score,
        treatment=payload.treatment,
        status="Open",
        owner=current_user.full_name,
        mitre_atlas_technique=payload.mitre_atlas_technique,
        owasp_category=payload.owasp_category
    )
    db.add(risk)
    await db.commit()
    await db.refresh(risk)
    return {"id": risk.id, "risk_code": risk.risk_code, "status": risk.status}

@router.get("/findings", response_model=List[FindingResponse])
async def list_findings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Finding).where(Finding.tenant_id == current_user.tenant_id).order_by(Finding.created_at.desc())
    )
    findings = result.scalars().all()

    system_ids = {f.system_id for f in findings if f.system_id}
    system_names: Dict[str, str] = {}
    if system_ids:
        sys_result = await db.execute(
            select(AISystem.id, AISystem.name).where(
                AISystem.id.in_(system_ids), AISystem.tenant_id == current_user.tenant_id
            )
        )
        system_names = {row[0]: row[1] for row in sys_result.all()}

    response = []
    for f in findings:
        response.append(
            FindingResponse(
                id=f.id,
                title=f.title,
                description=f.description,
                severity=f.severity,
                source=f.source,
                status=f.status,
                system_id=f.system_id,
                system_name=system_names.get(f.system_id, "Enterprise-Wide") if f.system_id else "Enterprise-Wide",
                control_id=f.control_id,
                due_date=f.due_date,
                created_at=f.created_at
            )
        )
    return response

@router.get("/remediations", response_model=List[Dict[str, Any]])
async def list_remediations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(RemediationTask)
        .where(RemediationTask.tenant_id == current_user.tenant_id)
        .options(selectinload(RemediationTask.finding))
        .order_by(RemediationTask.created_at.desc())
    )
    tasks = result.scalars().all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "finding_title": t.finding.title if t.finding else "General Finding",
            "finding_severity": t.finding.severity if t.finding else "High",
            "priority": t.priority,
            "status": t.status,
            "assigned_to": t.assigned_to,
            "target_date": t.target_date
        }
        for t in tasks
    ]

@router.put("/remediations/{task_id}", response_model=Dict[str, Any])
async def update_remediation(
    task_id: str,
    status_update: Dict[str, str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    result = await db.execute(
        select(RemediationTask).where(
            RemediationTask.id == task_id,
            RemediationTask.tenant_id == current_user.tenant_id
        )
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Remediation task not found")

    if "status" in status_update:
        task.status = status_update["status"]

    await db.commit()
    return {"id": task.id, "status": task.status}


@router.put("/risks/{risk_id}/accept", response_model=Dict[str, Any])
async def accept_risk(
    risk_id: str,
    acceptance: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_risk_acceptance)
):
    """
    Formal risk acceptance (spec #38). Ordinary users cannot dismiss a risk -
    only Risk Manager / CISO / Compliance Manager / Tenant Admin may, and the
    justification is captured in the audit trail rather than allowing a silent
    status flip.
    """
    justification = acceptance.get("business_justification")
    if not justification:
        raise HTTPException(status_code=400, detail="business_justification is required to accept a risk")

    result = await db.execute(
        select(Risk).where(Risk.id == risk_id, Risk.tenant_id == current_user.tenant_id)
    )
    risk = result.scalars().first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    risk.treatment = "Accept"
    risk.status = "Accepted"

    audit = AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="ACCEPT_RISK",
        object_type="Risk",
        object_id=risk.id,
        changes={
            "business_justification": justification,
            "approver": current_user.full_name,
            "approver_role": current_user.role,
            "expiry_date": acceptance.get("expiry_date"),
            "compensating_controls": acceptance.get("compensating_controls"),
        }
    )
    db.add(audit)
    await db.commit()

    return {"id": risk.id, "status": risk.status, "treatment": risk.treatment, "approver": current_user.full_name}
