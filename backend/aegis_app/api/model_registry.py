"""
Model Registry Endpoints.

A Model is a tenant-level catalog asset (not owned by a single AI System) -
AISystemModelLink is the real many-to-many relationship supporting the
dependency view "Model -> AI Systems" required by the AI governance spec.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.models.models import AIModel, AISystemModelLink, AISystem, AIAgent, Vendor, Risk, User, AuditEvent
from aegis_app.schemas.schemas import ModelCreate, ModelUpdate, ModelResponse, ModelLinkSystemInput
from aegis_app.api.deps import get_current_user, require_governance_write

router = APIRouter(prefix="/models", tags=["Model Registry"])


@router.get("", response_model=List[ModelResponse])
async def list_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(AIModel).where(AIModel.tenant_id == current_user.tenant_id).order_by(AIModel.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ModelResponse)
async def create_model(
    payload: ModelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    model = AIModel(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(model)
    await db.flush()

    if payload.system_id:
        db.add(AISystemModelLink(tenant_id=current_user.tenant_id, system_id=payload.system_id, model_id=model.id, role="Primary"))

    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="CREATE_MODEL", object_type="AIModel", object_id=model.id,
        changes={"name": model.name, "provider": model.provider, "version": model.version}
    ))
    await db.commit()
    await db.refresh(model)
    return model


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(AIModel).where(AIModel.id == model_id, AIModel.tenant_id == current_user.tenant_id))
    model = result.scalars().first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: str,
    payload: ModelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    result = await db.execute(select(AIModel).where(AIModel.id == model_id, AIModel.tenant_id == current_user.tenant_id))
    model = result.scalars().first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model, field, value)

    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="UPDATE_MODEL", object_type="AIModel", object_id=model.id, changes=update_data
    ))
    await db.commit()
    await db.refresh(model)
    return model


@router.delete("/{model_id}", response_model=Dict[str, str])
async def delete_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    result = await db.execute(select(AIModel).where(AIModel.id == model_id, AIModel.tenant_id == current_user.tenant_id))
    model = result.scalars().first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    await db.delete(model)
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="DELETE_MODEL", object_type="AIModel", object_id=model_id, changes={"name": model.name}
    ))
    await db.commit()
    return {"status": "deleted", "id": model_id}


@router.post("/{model_id}/link-system", response_model=Dict[str, str])
async def link_model_to_system(
    model_id: str,
    payload: ModelLinkSystemInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    model_res = await db.execute(select(AIModel).where(AIModel.id == model_id, AIModel.tenant_id == current_user.tenant_id))
    if not model_res.scalars().first():
        raise HTTPException(status_code=404, detail="Model not found")
    sys_res = await db.execute(select(AISystem).where(AISystem.id == payload.system_id, AISystem.tenant_id == current_user.tenant_id))
    if not sys_res.scalars().first():
        raise HTTPException(status_code=404, detail="AI System not found")

    existing = await db.execute(
        select(AISystemModelLink).where(
            AISystemModelLink.model_id == model_id, AISystemModelLink.system_id == payload.system_id
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="This model is already linked to this system")

    link = AISystemModelLink(tenant_id=current_user.tenant_id, system_id=payload.system_id, model_id=model_id, role=payload.role)
    db.add(link)
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="LINK_MODEL_TO_SYSTEM", object_type="AIModel", object_id=model_id,
        changes={"system_id": payload.system_id, "role": payload.role}
    ))
    await db.commit()
    return {"status": "linked", "model_id": model_id, "system_id": payload.system_id}


@router.get("/{model_id}/dependents", response_model=Dict[str, Any])
async def get_model_dependents(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dependency view: Model -> AI Systems, Model -> Agents, Model -> Vendor,
    Model -> Risks. This is what makes the Model Registry a real registry
    rather than a disconnected metadata card.
    """
    model_res = await db.execute(select(AIModel).where(AIModel.id == model_id, AIModel.tenant_id == current_user.tenant_id))
    model = model_res.scalars().first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    link_res = await db.execute(
        select(AISystemModelLink.system_id, AISystemModelLink.role).where(AISystemModelLink.model_id == model_id)
    )
    linked_system_ids = {row[0]: row[1] for row in link_res.all()}
    if model.system_id:
        linked_system_ids.setdefault(model.system_id, "Primary (legacy)")

    systems = []
    if linked_system_ids:
        sys_res = await db.execute(
            select(AISystem).where(AISystem.id.in_(linked_system_ids.keys()), AISystem.tenant_id == current_user.tenant_id)
        )
        systems = [
            {"id": s.id, "name": s.name, "risk_classification": s.risk_classification,
             "lifecycle_status": s.lifecycle_status, "role": linked_system_ids.get(s.id)}
            for s in sys_res.scalars().all()
        ]

    agent_res = await db.execute(select(AIAgent).where(AIAgent.model_id == model_id, AIAgent.tenant_id == current_user.tenant_id))
    agents = [{"id": a.id, "name": a.name, "risk_score": a.risk_score} for a in agent_res.scalars().all()]

    vendor = None
    if model.vendor_id:
        v_res = await db.execute(select(Vendor).where(Vendor.id == model.vendor_id, Vendor.tenant_id == current_user.tenant_id))
        v = v_res.scalars().first()
        vendor = {"id": v.id, "name": v.name, "risk_rating": v.risk_rating} if v else None

    risk_res = await db.execute(
        select(Risk).where(Risk.system_id.in_(list(linked_system_ids.keys()) or ["__none__"]), Risk.tenant_id == current_user.tenant_id)
    )
    risks = [{"id": r.id, "title": r.title, "inherent_score": r.inherent_score} for r in risk_res.scalars().all()]

    high_risk_system_count = sum(1 for s in systems if "High" in (s["risk_classification"] or ""))

    return {
        "model_id": model.id, "model_name": model.name,
        "dependent_systems": systems,
        "high_risk_system_count": high_risk_system_count,
        "dependent_agents": agents,
        "vendor": vendor,
        "related_risks": risks,
    }
