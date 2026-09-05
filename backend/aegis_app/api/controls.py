"""
Unified Control Library & Customer Controls Endpoints.
Enables managing normalized enterprise controls and updating implementation status.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.models.models import CustomerControl, User, AuditEvent
from aegis_app.schemas.schemas import UnifiedControlItem, CustomerControlUpdate
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.api.deps import get_current_user, require_governance_write

router = APIRouter(prefix="/controls", tags=["Unified Controls"])

@router.get("", response_model=List[UnifiedControlItem])
async def list_controls(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all Unified Controls joined with the tenant's current customer control status.
    """
    base_controls = crosswalk_service.get_unified_controls()
    
    # Query tenant's customer control statuses
    result = await db.execute(
        select(CustomerControl).where(CustomerControl.tenant_id == current_user.tenant_id)
    )
    customer_controls = {cc.control_id: cc for cc in result.scalars().all()}
    
    enriched = []
    for c in base_controls:
        cc = customer_controls.get(c["id"])
        enriched.append(
            UnifiedControlItem(
                id=c["id"],
                code=c["code"],
                title=c["title"],
                domain=c["domain"],
                objective=c["objective"],
                description=c["description"],
                control_type=c["control_type"],
                implementation_type=c["implementation_type"],
                control_frequency=c["control_frequency"],
                risk_addressed=c["risk_addressed"],
                implementation_guidance=c["implementation_guidance"],
                expected_evidence=c["expected_evidence"],
                test_procedure=c["test_procedure"],
                customer_status=cc.status if cc else "In Progress",
                customer_effectiveness=cc.effectiveness if cc else "Effective"
            )
        )
    return enriched

@router.put("/{control_id}", response_model=CustomerControlUpdate)
async def update_control_status(
    control_id: str,
    payload: CustomerControlUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    """
    Updates the organization's implementation status or effectiveness for a unified control.
    """
    result = await db.execute(
        select(CustomerControl).where(
            CustomerControl.control_id == control_id,
            CustomerControl.tenant_id == current_user.tenant_id
        )
    )
    cc = result.scalars().first()
    if not cc:
        cc = CustomerControl(
            tenant_id=current_user.tenant_id,
            organization_id=current_user.organization_id or current_user.tenant_id,
            control_id=control_id,
            status=payload.status,
            effectiveness=payload.effectiveness,
            implementation_notes=payload.implementation_notes,
            owner=payload.owner or current_user.full_name
        )
        db.add(cc)
    else:
        cc.status = payload.status
        cc.effectiveness = payload.effectiveness
        if payload.implementation_notes:
            cc.implementation_notes = payload.implementation_notes
        if payload.owner:
            cc.owner = payload.owner
            
    audit = AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="UPDATE_CUSTOMER_CONTROL",
        object_type="CustomerControl",
        object_id=control_id,
        changes=payload.model_dump()
    )
    db.add(audit)
    await db.commit()
    
    return payload
