"""
Organizational hierarchy: Business Units and AI Products.
Organization -> Business Unit -> AI Product -> AI System.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.models.models import BusinessUnit, AIProduct, User, AuditEvent
from aegis_app.schemas.schemas import BusinessUnitCreate, BusinessUnitResponse, AIProductCreate, AIProductResponse
from aegis_app.api.deps import get_current_user, require_governance_write

router = APIRouter(tags=["Organization Structure"])


@router.get("/business-units", response_model=List[BusinessUnitResponse])
async def list_business_units(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(BusinessUnit).where(BusinessUnit.tenant_id == current_user.tenant_id))
    return result.scalars().all()


@router.post("/business-units", response_model=BusinessUnitResponse)
async def create_business_unit(
    payload: BusinessUnitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    bu = BusinessUnit(
        tenant_id=current_user.tenant_id,
        organization_id=current_user.organization_id or current_user.tenant_id,
        **payload.model_dump()
    )
    db.add(bu)
    await db.flush()
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="CREATE_BUSINESS_UNIT", object_type="BusinessUnit", object_id=bu.id, changes={"name": bu.name}
    ))
    await db.commit()
    await db.refresh(bu)
    return bu


@router.get("/ai-products", response_model=List[AIProductResponse])
async def list_ai_products(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(AIProduct).where(AIProduct.tenant_id == current_user.tenant_id))
    return result.scalars().all()


@router.post("/ai-products", response_model=AIProductResponse)
async def create_ai_product(
    payload: AIProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    product = AIProduct(
        tenant_id=current_user.tenant_id,
        organization_id=current_user.organization_id or current_user.tenant_id,
        **payload.model_dump()
    )
    db.add(product)
    await db.flush()
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="CREATE_AI_PRODUCT", object_type="AIProduct", object_id=product.id, changes={"name": product.name}
    ))
    await db.commit()
    await db.refresh(product)
    return product
