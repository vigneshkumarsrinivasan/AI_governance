"""
AI Compliance Assessments Endpoints.
Supports executing assessments against single or multiple frameworks,
recording answers (Yes/No/Partial/NA/Unknown), attaching evidence, and recalculating scores.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aegis_app.core.database import get_db
from aegis_app.models.models import Assessment, AssessmentResponse, AISystem, User, AuditEvent
from aegis_app.schemas.schemas import AssessmentCreate, AssessmentResponseInput, AssessmentDetailResponse
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.api.deps import get_current_user

router = APIRouter(prefix="/assessments", tags=["Assessments"])

@router.get("", response_model=List[Dict[str, Any]])
async def list_assessments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Assessment)
        .where(Assessment.tenant_id == current_user.tenant_id)
        .options(selectinload(Assessment.ai_system))
        .order_by(Assessment.created_at.desc())
    )
    assessments = result.scalars().all()
    
    return [
        {
            "id": a.id,
            "title": a.title,
            "framework_id": a.framework_id,
            "system_id": a.system_id,
            "system_name": a.ai_system.name if a.ai_system else "Unknown",
            "status": a.status,
            "readiness_percentage": a.readiness_percentage,
            "implementation_score": a.implementation_score,
            "evidence_score": a.evidence_score,
            "created_at": a.created_at
        }
        for a in assessments
    ]

@router.post("", response_model=Dict[str, Any])
async def create_assessment(
    payload: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fw = crosswalk_service.get_framework(payload.framework_id)
    if not fw:
        raise HTTPException(status_code=404, detail="Framework not found")
        
    assessment = Assessment(
        tenant_id=current_user.tenant_id,
        organization_id=current_user.organization_id or current_user.tenant_id,
        system_id=payload.system_id,
        title=payload.title,
        framework_id=payload.framework_id,
        status="In Progress",
        readiness_percentage=0.0
    )
    db.add(assessment)
    await db.flush()
    
    # Pre-populate responses for all requirements in this framework
    for ch in fw.get("chapters", []):
        for req in ch.get("requirements", []):
            resp = AssessmentResponse(
                assessment_id=assessment.id,
                requirement_id=req["id"],
                status="Unknown",
                rationale="Pending initial compliance review"
            )
            db.add(resp)
            
    await db.commit()
    await db.refresh(assessment)
    return {"id": assessment.id, "title": assessment.title, "status": assessment.status}

@router.get("/{assessment_id}", response_model=AssessmentDetailResponse)
async def get_assessment(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Assessment)
        .where(Assessment.id == assessment_id, Assessment.tenant_id == current_user.tenant_id)
        .options(selectinload(Assessment.ai_system), selectinload(Assessment.responses))
    )
    assessment = result.scalars().first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    fw = crosswalk_service.get_framework(assessment.framework_id)
    fw_name = fw["name"] if fw else assessment.framework_id
    
    # Map requirement metadata
    req_meta = {}
    if fw:
        for ch in fw.get("chapters", []):
            for req in ch.get("requirements", []):
                req_meta[req["id"]] = req
                
    responses_data = []
    for r in assessment.responses:
        meta = req_meta.get(r.requirement_id, {})
        responses_data.append({
            "id": r.id,
            "requirement_id": r.requirement_id,
            "article": meta.get("article", ""),
            "title": meta.get("title", r.requirement_id),
            "normalized_requirement": meta.get("normalized_requirement", ""),
            "status": r.status,
            "rationale": r.rationale,
            "evidence_ids": r.evidence_ids or [],
            "official_url": meta.get("official_url", "")
        })
        
    return AssessmentDetailResponse(
        id=assessment.id,
        system_id=assessment.system_id,
        system_name=assessment.ai_system.name if assessment.ai_system else "Unknown",
        framework_id=assessment.framework_id,
        framework_name=fw_name,
        title=assessment.title,
        status=assessment.status,
        readiness_percentage=assessment.readiness_percentage,
        implementation_score=assessment.implementation_score,
        evidence_score=assessment.evidence_score,
        effectiveness_score=assessment.effectiveness_score,
        responses=responses_data,
        created_at=assessment.created_at,
        completed_at=assessment.completed_at
    )

@router.put("/{assessment_id}/response", response_model=Dict[str, Any])
async def submit_response(
    assessment_id: str,
    payload: AssessmentResponseInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Assessment)
        .where(Assessment.id == assessment_id, Assessment.tenant_id == current_user.tenant_id)
        .options(selectinload(Assessment.responses))
    )
    assessment = result.scalars().first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    # Find matching response record
    target_resp = None
    for r in assessment.responses:
        if r.requirement_id == payload.requirement_id:
            target_resp = r
            break
            
    if not target_resp:
        target_resp = AssessmentResponse(
            assessment_id=assessment.id,
            requirement_id=payload.requirement_id
        )
        db.add(target_resp)
        assessment.responses.append(target_resp)
        
    target_resp.status = payload.status
    target_resp.rationale = payload.rationale
    target_resp.evidence_ids = payload.evidence_ids
    
    # Recalculate assessment score
    total_reqs = len(assessment.responses)
    if total_reqs > 0:
        compliant_points = 0.0
        evidence_points = 0.0
        for r in assessment.responses:
            if r.status == "Yes":
                compliant_points += 1.0
            elif r.status == "Partial":
                compliant_points += 0.5
            elif r.status == "N/A":
                compliant_points += 1.0
                
            if r.evidence_ids and len(r.evidence_ids) > 0:
                evidence_points += 1.0
                
        assessment.implementation_score = round((compliant_points / total_reqs) * 100.0, 1)
        assessment.evidence_score = round((evidence_points / total_reqs) * 100.0, 1)
        assessment.readiness_percentage = round(
            (0.6 * assessment.implementation_score) + (0.4 * assessment.evidence_score), 1
        )
        
    await db.commit()
    return {
        "status": "success",
        "readiness_percentage": assessment.readiness_percentage,
        "implementation_score": assessment.implementation_score,
        "evidence_score": assessment.evidence_score
    }
