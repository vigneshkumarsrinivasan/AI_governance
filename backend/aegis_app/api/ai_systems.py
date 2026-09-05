"""
AI Systems Inventory and Intake Endpoints.
Includes dynamic questionnaire evaluation and full CRUD with multi-tenant scoping.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.models.models import AISystem, User, AuditEvent, Risk, CustomerControl, ApplicabilityDecision
from aegis_app.schemas.schemas import (
    AISystemCreate, AISystemUpdate, AISystemResponse,
    IntakeQuestionnaireInput, IntakeEvaluationResult
)
from aegis_app.services.applicability import evaluate_ai_system_applicability
from aegis_app.api.deps import get_current_user, require_governance_write, require_legal_review

router = APIRouter(prefix="/ai-systems", tags=["AI Systems"])

@router.post("/intake-evaluate", response_model=IntakeEvaluationResult)
async def evaluate_intake(
    data: IntakeQuestionnaireInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Evaluates dynamic intake responses and generates explainable statutory classification,
    EU AI Act risk tier, recommended frameworks, and required unified controls.

    Every evaluation is persisted as an immutable ApplicabilityDecision record
    (never overwritten - spec #10/#75/#112/#113) so the decision can be audited,
    reproduced "as of" a given date, and routed to a Legal Reviewer when the
    rule engine flags LEGAL REVIEW REQUIRED.
    """
    result = evaluate_ai_system_applicability(data)

    decision_status = "LEGAL_REVIEW_REQUIRED" if result.risk_level in (
        "Unacceptable / Prohibited", "High Risk"
    ) else ("LIKELY_APPLICABLE" if result.recommended_frameworks else "NOT_APPLICABLE")

    decision = ApplicabilityDecision(
        tenant_id=current_user.tenant_id,
        organization_id=current_user.organization_id,
        system_name=data.system_name,
        input_snapshot=data.model_dump(),
        decision_status=decision_status,
        risk_level=result.risk_level,
        eu_ai_act_classification=result.eu_ai_act_classification,
        rationale=result.eu_ai_act_rationale,
        recommended_frameworks=result.recommended_frameworks,
        required_controls=result.required_unified_controls,
        rules_fired=getattr(result, "rules_fired", []),
        confidence="Rule-Based",
        requires_legal_review=(decision_status == "LEGAL_REVIEW_REQUIRED"),
        ruleset_version=getattr(result, "ruleset_version", None),
    )
    db.add(decision)
    await db.flush()

    audit = AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="APPLICABILITY_EVALUATION",
        object_type="ApplicabilityDecision",
        object_id=decision.id,
        changes={"system_name": data.system_name, "decision_status": decision_status, "risk_level": result.risk_level}
    )
    db.add(audit)
    await db.commit()

    return result

@router.get("", response_model=List[AISystemResponse])
async def list_ai_systems(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all AI systems strictly scoped to the current user's tenant.
    """
    result = await db.execute(
        select(AISystem)
        .where(AISystem.tenant_id == current_user.tenant_id)
        .order_by(AISystem.created_at.desc())
    )
    return result.scalars().all()

@router.post("", response_model=AISystemResponse)
async def create_ai_system(
    payload: AISystemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    """
    Registers a new AI system in the central inventory and records an audit event.
    """
    ai_system = AISystem(
        tenant_id=current_user.tenant_id,
        organization_id=current_user.organization_id or current_user.tenant_id,
        **payload.model_dump()
    )
    db.add(ai_system)
    await db.flush()
    
    # Audit log entry
    audit = AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="CREATE_AI_SYSTEM",
        object_type="AISystem",
        object_id=ai_system.id,
        changes={"name": ai_system.name, "risk_classification": ai_system.risk_classification}
    )
    db.add(audit)
    await db.commit()
    await db.refresh(ai_system)
    
    return ai_system

@router.get("/{system_id}", response_model=AISystemResponse)
async def get_ai_system(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(AISystem)
        .where(AISystem.id == system_id, AISystem.tenant_id == current_user.tenant_id)
    )
    system = result.scalars().first()
    if not system:
        raise HTTPException(status_code=404, detail="AI System not found")
    return system

@router.put("/{system_id}", response_model=AISystemResponse)
async def update_ai_system(
    system_id: str,
    payload: AISystemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    result = await db.execute(
        select(AISystem)
        .where(AISystem.id == system_id, AISystem.tenant_id == current_user.tenant_id)
    )
    system = result.scalars().first()
    if not system:
        raise HTTPException(status_code=404, detail="AI System not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(system, field, value)
        
    audit = AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="UPDATE_AI_SYSTEM",
        object_type="AISystem",
        object_id=system.id,
        changes=update_data
    )
    db.add(audit)
    await db.commit()
    await db.refresh(system)

    return system


@router.get("/applicability/decisions", response_model=List[Dict[str, Any]])
async def list_applicability_decisions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Full history of every applicability/classification determination made for
    this tenant, including ones superseded by a later re-assessment - history
    is never overwritten (spec #10, #113).
    """
    result = await db.execute(
        select(ApplicabilityDecision)
        .where(ApplicabilityDecision.tenant_id == current_user.tenant_id)
        .order_by(ApplicabilityDecision.created_at.desc())
    )
    decisions = result.scalars().all()
    return [
        {
            "id": d.id,
            "system_name": d.system_name,
            "decision_status": d.decision_status,
            "risk_level": d.risk_level,
            "eu_ai_act_classification": d.eu_ai_act_classification,
            "rationale": d.rationale,
            "recommended_frameworks": d.recommended_frameworks,
            "required_controls": d.required_controls,
            "requires_legal_review": d.requires_legal_review,
            "reviewer_email": d.reviewer_email,
            "reviewer_decision": d.reviewer_decision,
            "reviewer_rationale": d.reviewer_rationale,
            "reviewed_at": d.reviewed_at,
            "ruleset_version": d.ruleset_version,
            "created_at": d.created_at,
            "superseded_by_id": d.superseded_by_id,
        }
        for d in decisions
    ]


@router.put("/applicability/decisions/{decision_id}/review", response_model=Dict[str, Any])
async def review_applicability_decision(
    decision_id: str,
    review: Dict[str, str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_legal_review)
):
    """
    Legal Reviewer / Compliance Manager / Tenant Admin accepts, rejects, or
    modifies a rule-engine classification flagged LEGAL REVIEW REQUIRED.
    The rule engine's own output can never self-approve this (spec #75).
    """
    result = await db.execute(
        select(ApplicabilityDecision).where(
            ApplicabilityDecision.id == decision_id,
            ApplicabilityDecision.tenant_id == current_user.tenant_id
        )
    )
    decision = result.scalars().first()
    if not decision:
        raise HTTPException(status_code=404, detail="Applicability decision not found")

    decision.reviewer_id = current_user.id
    decision.reviewer_email = current_user.email
    decision.reviewer_decision = review.get("decision", "Accepted")  # Accepted, Rejected, Modified
    decision.reviewer_rationale = review.get("rationale")
    decision.reviewed_at = datetime.now(timezone.utc)
    if decision.reviewer_decision == "Accepted":
        decision.decision_status = "APPLICABLE" if decision.recommended_frameworks else "NOT_APPLICABLE"
    elif decision.reviewer_decision == "Rejected":
        decision.decision_status = "NOT_APPLICABLE"

    audit = AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="REVIEW_APPLICABILITY_DECISION",
        object_type="ApplicabilityDecision",
        object_id=decision.id,
        changes={"reviewer_decision": decision.reviewer_decision, "rationale": decision.reviewer_rationale}
    )
    db.add(audit)
    await db.commit()

    return {"id": decision.id, "decision_status": decision.decision_status, "reviewer_decision": decision.reviewer_decision}
