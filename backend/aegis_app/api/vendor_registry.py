"""
Vendor Registry Endpoints.

Full CRUD plus dependency propagation: Vendor -> Model -> AI Systems, so a
vendor risk-rating change can show exactly which (and how many high-risk)
systems are affected - the spec's "Vendor X -> Model X -> 14 AI Systems ->
4 high-risk systems" example.

Note: GET /security/vendors (api/security.py) continues to work unchanged
for backward compatibility with the existing frontend Security tab.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.models.models import Vendor, AIModel, AISystemModelLink, AISystem, User, AuditEvent
from aegis_app.schemas.schemas import VendorCreate, VendorUpdate, VendorResponse
from aegis_app.api.deps import get_current_user, require_governance_write

router = APIRouter(prefix="/vendors", tags=["Vendor Registry"])


@router.get("", response_model=List[VendorResponse])
async def list_vendors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Vendor).where(Vendor.tenant_id == current_user.tenant_id).order_by(Vendor.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=VendorResponse)
async def create_vendor(
    payload: VendorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    vendor = Vendor(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(vendor)
    await db.flush()
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="CREATE_VENDOR", object_type="Vendor", object_id=vendor.id,
        changes={"name": vendor.name, "risk_rating": vendor.risk_rating}
    ))
    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id, Vendor.tenant_id == current_user.tenant_id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: str,
    payload: VendorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id, Vendor.tenant_id == current_user.tenant_id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    update_data = payload.model_dump(exclude_unset=True)
    old_risk_rating = vendor.risk_rating
    for field, value in update_data.items():
        setattr(vendor, field, value)

    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="UPDATE_VENDOR", object_type="Vendor", object_id=vendor.id,
        changes={**update_data, "previous_risk_rating": old_risk_rating}
    ))
    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.delete("/{vendor_id}", response_model=Dict[str, str])
async def delete_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id, Vendor.tenant_id == current_user.tenant_id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    await db.delete(vendor)
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="DELETE_VENDOR", object_type="Vendor", object_id=vendor_id, changes={"name": vendor.name}
    ))
    await db.commit()
    return {"status": "deleted", "id": vendor_id}


@router.get("/{vendor_id}/impact", response_model=Dict[str, Any])
async def get_vendor_impact(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dependency propagation: Vendor -> Models -> AI Systems. If this vendor's
    risk rating changes, this is exactly the set of systems that need review.
    """
    vendor_res = await db.execute(select(Vendor).where(Vendor.id == vendor_id, Vendor.tenant_id == current_user.tenant_id))
    vendor = vendor_res.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    model_res = await db.execute(select(AIModel).where(AIModel.vendor_id == vendor_id, AIModel.tenant_id == current_user.tenant_id))
    models = model_res.scalars().all()
    model_ids = [m.id for m in models]

    system_ids = set()
    if model_ids:
        link_res = await db.execute(select(AISystemModelLink.system_id).where(AISystemModelLink.model_id.in_(model_ids)))
        system_ids.update(row[0] for row in link_res.all())
    for m in models:
        if m.system_id:
            system_ids.add(m.system_id)

    systems = []
    if system_ids:
        sys_res = await db.execute(select(AISystem).where(AISystem.id.in_(system_ids), AISystem.tenant_id == current_user.tenant_id))
        systems = [
            {"id": s.id, "name": s.name, "risk_classification": s.risk_classification, "lifecycle_status": s.lifecycle_status}
            for s in sys_res.scalars().all()
        ]

    high_risk_systems = [s for s in systems if "High" in (s["risk_classification"] or "") or "Prohibited" in (s["risk_classification"] or "")]

    return {
        "vendor_id": vendor.id,
        "vendor_name": vendor.name,
        "vendor_risk_rating": vendor.risk_rating,
        "dependent_models": [{"id": m.id, "name": m.name} for m in models],
        "dependent_systems_count": len(systems),
        "dependent_systems": systems,
        "high_risk_systems_count": len(high_risk_systems),
        "high_risk_systems": high_risk_systems,
    }
