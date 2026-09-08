"""
Unified Control Library & Customer Controls Endpoints.
Enables managing normalized enterprise controls and updating implementation status.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.models.models import CustomerControl, User, AuditEvent, Finding
from aegis_app.schemas.schemas import UnifiedControlItem, CustomerControlUpdate
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.services.findings import create_finding, open_finding_exists
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

    # Control test outcome drives the finding lifecycle (spec §16/§26/§32):
    # a control that is Ineffective (or explicitly Failed) raises a "Failed
    # Control" finding; when it recovers, the auto-raised finding is resolved.
    control_meta = next((c for c in crosswalk_service.get_unified_controls() if c["id"] == control_id), None)
    control_title = control_meta["title"] if control_meta else control_id
    failed = (payload.effectiveness == "Ineffective") or (payload.status in ("Failed", "Not Started"))
    severe = "Critical" if (control_meta and control_meta.get("domain") in ("Prompt Security", "Model Security", "Agent Security")) else "High"

    if payload.effectiveness == "Ineffective":
        await create_finding(
            db, tenant_id=current_user.tenant_id,
            organization_id=current_user.organization_id or current_user.tenant_id,
            title=f"Control not operating effectively: {control_title}",
            description=payload.implementation_notes or f"{control_id} was marked Ineffective on a control test.",
            severity=severe, source="Failed Control", control_id=control_id,
            actor_id=current_user.id, actor_email=current_user.email,
        )
    elif payload.effectiveness in ("Effective", "Partially Effective"):
        existing = await open_finding_exists(
            db, current_user.tenant_id, source="Failed Control", control_id=control_id
        )
        if existing and existing.status not in ("Resolved", "Accepted Risk"):
            existing.status = "Resolved"
            db.add(AuditEvent(
                tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
                action="AUTO_RESOLVE_FINDING", object_type="Finding", object_id=existing.id,
                changes={"reason": f"{control_id} effectiveness recovered to {payload.effectiveness}"},
            ))

    await db.commit()

    return payload
