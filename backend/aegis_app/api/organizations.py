"""
Company / Organization management (spec sections 1-5, 29-32, 69).

Fixes the "I can only see Acme and cannot add another company" blocker:
  * POST   /organizations           - create a new company (own tenant), become its Tenant Admin
  * GET    /organizations/mine      - the companies this user can switch to
  * POST   /organizations/switch    - change the active company (returns a fresh token)
  * GET    /organizations/current   - the active company + portfolio stats
  * PATCH  /organizations/current   - edit the active company

Every company is a separate tenant. The backend allocates the tenant id - the
client never supplies one. All company-scoped records use current_user.tenant_id,
which switching updates.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_app.core.database import get_db
from aegis_app.core.security import create_access_token
from aegis_app.core.permissions import SELF_SIGNUP_ALLOWED_ROLES
from aegis_app.api.deps import get_current_user
from aegis_app.models.models import (
    User, Tenant, Organization, OrganizationMembership, OrganizationProfile,
    AISystem, Finding, Assessment, AuditEvent,
)

router = APIRouter(prefix="/organizations", tags=["Companies"])


_EMP_MID = {"1-10": 5, "11-50": 30, "51-250": 150, "251-1000": 600,
            "1001-5000": 3000, "5001-10000": 7500, "10000+": 15000}


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    website: Optional[str] = Field(default=None, max_length=255)
    company_type: Optional[str] = None
    industry: Optional[str] = None
    employee_range: Optional[str] = None
    employee_count: Optional[int] = None
    headquarters_country: Optional[str] = None          # NO default - must be chosen
    operating_countries: List[str] = Field(default_factory=list)
    ai_deployment_countries: List[str] = Field(default_factory=list)
    customer_countries: List[str] = Field(default_factory=list)
    uses_ai: bool = True
    uses_genai: bool = False
    uses_agents: bool = False
    is_financial_institution: bool = False
    is_critical_infrastructure: bool = False
    is_software_vendor: bool = False
    eu_market_exposure: bool = False
    processes_personal_data: bool = True
    governance_contacts: dict = Field(default_factory=dict)

    @field_validator("website")
    @classmethod
    def _website_ok(cls, v):
        if v and not re.match(r"^https?://.+\..+", v.strip()):
            raise ValueError("Enter a valid URL, e.g. https://example.com")
        return v.strip() if v else v


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    website: Optional[str] = Field(default=None, max_length=255)
    company_type: Optional[str] = None
    industry: Optional[str] = None
    employee_range: Optional[str] = None
    employee_count: Optional[int] = None
    headquarters_country: Optional[str] = None
    operating_countries: Optional[List[str]] = None
    ai_deployment_countries: Optional[List[str]] = None
    customer_countries: Optional[List[str]] = None
    is_financial_institution: Optional[bool] = None
    is_critical_infrastructure: Optional[bool] = None
    is_software_vendor: Optional[bool] = None
    eu_market_exposure: Optional[bool] = None
    processes_personal_data: Optional[bool] = None
    governance_contacts: Optional[dict] = None


class SwitchInput(BaseModel):
    organization_id: str


async def _memberships(db: AsyncSession, user_id: str) -> List[OrganizationMembership]:
    return (await db.execute(
        select(OrganizationMembership).where(OrganizationMembership.user_id == user_id)
    )).scalars().all()


async def _ensure_self_membership(db: AsyncSession, user: User) -> None:
    """Older users predate the membership table; make sure they have one for
    their current tenant so the company selector is never empty."""
    existing = (await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.tenant_id == user.tenant_id,
        )
    )).scalars().first()
    if not existing and user.tenant_id:
        db.add(OrganizationMembership(
            user_id=user.id, tenant_id=user.tenant_id,
            organization_id=user.organization_id or user.tenant_id,
            role=user.role, is_default=True,
        ))
        await db.flush()


def _org_summary(org: Organization, role: str, is_active: bool) -> Dict[str, Any]:
    return {
        "organization_id": org.id,
        "tenant_id": org.tenant_id,
        "name": org.name,
        "legal_name": org.legal_name,
        "website": org.website,
        "company_type": org.company_type,
        "industry": org.industry,
        "headquarters_country": org.headquarters_country,
        "employee_count": org.employee_count,
        "employee_range": org.employee_range,
        "is_demo": bool(org.is_demo),
        "role": role,
        "is_active": is_active,
    }


@router.get("/mine")
async def my_companies(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _ensure_self_membership(db, current_user)
    await db.commit()
    ms = await _memberships(db, current_user.id)
    org_ids = [m.organization_id for m in ms]
    orgs = {o.id: o for o in (await db.execute(
        select(Organization).where(Organization.id.in_(org_ids))
    )).scalars().all()}
    out = []
    for m in ms:
        o = orgs.get(m.organization_id)
        if o:
            out.append(_org_summary(o, m.role, o.tenant_id == current_user.tenant_id))
    out.sort(key=lambda x: (not x["is_active"], x["is_demo"], x["name"].lower()))
    return {"companies": out, "active_tenant_id": current_user.tenant_id}


@router.post("", status_code=201)
async def create_company(
    payload: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant = Tenant(name=payload.name)
    db.add(tenant)
    await db.flush()

    eu = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
          "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE", "IS", "LI", "NO"}
    all_countries = set(map(str.upper, (payload.operating_countries or []) + (payload.ai_deployment_countries or []) + (payload.customer_countries or [])))
    emp = payload.employee_count or _EMP_MID.get(payload.employee_range or "", 25)
    org = Organization(
        tenant_id=tenant.id,
        name=payload.name,
        legal_name=payload.legal_name,
        website=payload.website,
        company_type=payload.company_type,
        industry=payload.industry or "other",
        headquarters_country=payload.headquarters_country or "",
        countries_operating=payload.operating_countries or [],
        ai_deployment_countries=payload.ai_deployment_countries or [],
        customer_countries=payload.customer_countries or [],
        employee_count=emp,
        employee_range=payload.employee_range,
        is_financial_institution=payload.is_financial_institution,
        is_critical_infrastructure=payload.is_critical_infrastructure,
        is_software_vendor=payload.is_software_vendor,
        processes_personal_data=payload.processes_personal_data,
        governance_contacts=payload.governance_contacts or {},
        eu_market_exposure=payload.eu_market_exposure or bool(all_countries & eu),
        is_demo=False,
    )
    db.add(org)
    await db.flush()

    # A freshly-created company also gets a starter profile row so the SME
    # applicability engine has something to work with.
    db.add(OrganizationProfile(
        tenant_id=tenant.id, organization_id=org.id,
        headquarters_country=payload.headquarters_country or "",
        operating_countries=payload.operating_countries or [],
        employee_count=emp,
        industry=payload.industry or "other",
        develops_ai_products=payload.uses_ai,
        uses_generative_ai=payload.uses_genai,
        builds_ai_agents=payload.uses_agents,
        product_marketed_in_eu=payload.eu_market_exposure,
        data_types=(["personal"] if payload.processes_personal_data else []),
        answers={"legal_name": payload.legal_name, "website": payload.website,
                 "company_type": payload.company_type, "governance_contacts": payload.governance_contacts},
    ))

    db.add(OrganizationMembership(
        user_id=current_user.id, tenant_id=tenant.id, organization_id=org.id,
        role="Tenant Admin", is_default=False,
    ))

    # Switch the creator into the new company immediately (spec section 3 step 7).
    current_user.tenant_id = tenant.id
    current_user.organization_id = org.id
    current_user.role = "Tenant Admin"

    db.add(AuditEvent(
        tenant_id=tenant.id, actor_id=current_user.id, actor_email=current_user.email,
        action="CREATE_COMPANY", object_type="Organization", object_id=org.id,
        changes={"name": payload.name, "hq": payload.headquarters_country, "industry": payload.industry},
    ))
    await db.commit()
    await db.refresh(current_user)

    token = create_access_token(data={"sub": current_user.id, "tenant_id": tenant.id, "role": current_user.role})
    return {
        "company": _org_summary(org, "Tenant Admin", True),
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/switch")
async def switch_company(
    payload: SwitchInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = (await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.organization_id == payload.organization_id,
        )
    )).scalars().first()
    if not m:
        raise HTTPException(status_code=403, detail="You are not a member of that company")

    org = (await db.execute(select(Organization).where(Organization.id == m.organization_id))).scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Company not found")

    current_user.tenant_id = m.tenant_id
    current_user.organization_id = m.organization_id
    current_user.role = m.role
    db.add(AuditEvent(
        tenant_id=m.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="SWITCH_COMPANY", object_type="Organization", object_id=org.id, changes={"to": org.name},
    ))
    await db.commit()
    await db.refresh(current_user)

    token = create_access_token(data={"sub": current_user.id, "tenant_id": m.tenant_id, "role": m.role})
    return {
        "company": _org_summary(org, m.role, True),
        "access_token": token,
        "token_type": "bearer",
        "role": m.role,
    }


@router.get("/current")
async def current_company(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = (await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )).scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="No active company")

    tid = current_user.tenant_id
    n_sys = (await db.execute(select(func.count(AISystem.id)).where(AISystem.tenant_id == tid))).scalar() or 0
    systems = (await db.execute(select(AISystem).where(AISystem.tenant_id == tid))).scalars().all()
    high_risk = sum(1 for s in systems if "High" in (s.risk_classification or ""))
    open_findings = (await db.execute(
        select(func.count(Finding.id)).where(Finding.tenant_id == tid, Finding.status.notin_(("Resolved", "Accepted Risk")))
    )).scalar() or 0
    n_assess = (await db.execute(select(func.count(Assessment.id)).where(Assessment.tenant_id == tid))).scalar() or 0
    applicable_fw = sorted({fk for s in systems for fk in (s.applicable_frameworks or [])})

    return {
        **_org_summary(org, current_user.role, True),
        "countries_operating": org.countries_operating or [],
        "ai_deployment_countries": org.ai_deployment_countries or [],
        "customer_countries": org.customer_countries or [],
        "is_financial_institution": org.is_financial_institution,
        "is_critical_infrastructure": org.is_critical_infrastructure,
        "is_software_vendor": org.is_software_vendor,
        "processes_personal_data": org.processes_personal_data,
        "governance_contacts": org.governance_contacts or {},
        "eu_market_exposure": org.eu_market_exposure,
        "portfolio": {
            "ai_systems": n_sys,
            "high_risk_systems": high_risk,
            "applicable_frameworks": applicable_fw,
            "open_findings": open_findings,
            "assessments": n_assess,
        },
    }


@router.patch("/current")
async def update_current_company(
    payload: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("Tenant Admin", "Super Admin"):
        raise HTTPException(status_code=403, detail="Only a Tenant Admin can edit the company")
    org = (await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )).scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="No active company")

    data = payload.model_dump(exclude_none=True)
    if "operating_countries" in data:
        org.countries_operating = data.pop("operating_countries")
    if "employee_range" in data and "employee_count" not in data:
        org.employee_count = _EMP_MID.get(data["employee_range"], org.employee_count)
    for k, v in data.items():
        if hasattr(org, k):
            setattr(org, k, v)
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="UPDATE_COMPANY", object_type="Organization", object_id=org.id, changes=data,
    ))
    await db.commit()
    await db.refresh(org)
    return _org_summary(org, current_user.role, True)
