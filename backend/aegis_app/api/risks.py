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
from aegis_app.schemas.schemas import (
    RiskCreate, RiskResponse, FindingResponse, FindingCreate, FindingUpdate, RemediationCreate,
)
from aegis_app.api.deps import get_current_user, require_governance_write, require_risk_acceptance
from aegis_app.core import permissions as _perm
from aegis_app.api.deps import require_roles
from aegis_app.services.findings import create_finding as _create_finding

# Findings can be raised by governance, security, risk and audit roles.
require_finding_write = require_roles(sorted(set(_perm.GOVERNANCE_WRITE) | {"Auditor", "Legal Reviewer"}))

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

@router.post("/findings", response_model=FindingResponse, status_code=201)
async def create_finding_endpoint(
    payload: FindingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_finding_write),
):
    """Raise a finding manually (spec §23/§35). Findings are also raised
    automatically by failed control tests and rejected evidence."""
    if payload.system_id:
        owns = (await db.execute(select(AISystem.id).where(
            AISystem.id == payload.system_id, AISystem.tenant_id == current_user.tenant_id
        ))).first()
        if not owns:
            raise HTTPException(status_code=404, detail="system_id not found in your tenant")

    finding = await _create_finding(
        db, tenant_id=current_user.tenant_id,
        organization_id=current_user.organization_id or current_user.tenant_id,
        title=payload.title, description=payload.description or "", severity=payload.severity,
        source=payload.source, system_id=payload.system_id, control_id=payload.control_id,
        risk_id=payload.risk_id, due_date=payload.due_date,
        actor_id=current_user.id, actor_email=current_user.email, dedupe=False,
    )
    await db.commit()
    await db.refresh(finding)
    return FindingResponse(
        id=finding.id, title=finding.title, description=finding.description, severity=finding.severity,
        source=finding.source, status=finding.status, system_id=finding.system_id,
        system_name=None, control_id=finding.control_id, risk_id=finding.risk_id,
        due_date=finding.due_date, created_at=finding.created_at,
    )


@router.put("/findings/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: str,
    payload: FindingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_finding_write),
):
    """Update / progress / close a finding. Closed findings stay in the audit
    trail (status changes to Resolved, the row is never deleted)."""
    finding = (await db.execute(select(Finding).where(
        Finding.id == finding_id, Finding.tenant_id == current_user.tenant_id
    ))).scalars().first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    before = {"status": finding.status, "severity": finding.severity}
    for field in ("title", "description", "severity", "status", "due_date"):
        val = getattr(payload, field)
        if val is not None:
            setattr(finding, field, val)

    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="UPDATE_FINDING", object_type="Finding", object_id=finding.id,
        changes={"before": before, "after": {"status": finding.status, "severity": finding.severity}},
    ))
    await db.commit()
    await db.refresh(finding)
    return FindingResponse(
        id=finding.id, title=finding.title, description=finding.description, severity=finding.severity,
        source=finding.source, status=finding.status, system_id=finding.system_id, system_name=None,
        control_id=finding.control_id, risk_id=finding.risk_id, due_date=finding.due_date, created_at=finding.created_at,
    )


@router.post("/remediations", response_model=Dict[str, Any], status_code=201)
async def create_remediation(
    payload: RemediationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write),
):
    """Create a remediation task against a finding (spec §24). Works with the
    internal workflow whether or not Jira is configured."""
    finding = (await db.execute(select(Finding).where(
        Finding.id == payload.finding_id, Finding.tenant_id == current_user.tenant_id
    ))).scalars().first()
    if not finding:
        raise HTTPException(status_code=404, detail="finding_id not found in your tenant")

    task = RemediationTask(
        tenant_id=current_user.tenant_id, finding_id=finding.id,
        title=payload.title, description=payload.description,
        assigned_to=payload.assigned_to, priority=payload.priority,
        status="Todo", target_date=payload.target_date,
    )
    db.add(task)
    if finding.status == "Open":
        finding.status = "Remediating"
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="CREATE_REMEDIATION", object_type="RemediationTask", object_id=finding.id,
        changes={"finding_id": finding.id, "assigned_to": payload.assigned_to, "priority": payload.priority},
    ))
    await db.commit()
    await db.refresh(task)
    return {"id": task.id, "finding_id": task.finding_id, "status": task.status,
            "assigned_to": task.assigned_to, "priority": task.priority}


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
        if task.status in ("Done", "In Review"):
            from datetime import datetime, timezone
            task.completed_date = datetime.now(timezone.utc)
        # When every remediation task on a finding is Done, resolve the finding
        # (it stays in the audit trail - status change only, never deleted).
        if task.status == "Done":
            finding = (await db.execute(
                select(Finding).where(Finding.id == task.finding_id)
            )).scalars().first()
            if finding:
                siblings = (await db.execute(
                    select(RemediationTask).where(RemediationTask.finding_id == finding.id)
                )).scalars().all()
                if all(s.status == "Done" for s in siblings) and finding.status not in ("Resolved", "Accepted Risk"):
                    finding.status = "Resolved"
                    db.add(AuditEvent(
                        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
                        action="RESOLVE_FINDING", object_type="Finding", object_id=finding.id,
                        changes={"reason": "all remediation tasks completed"},
                    ))

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
