"""
SME onboarding + company-level applicability (spec sections 5, 6, 19, 23, 24).

New, additive surface. Nothing here replaces the per-AI-system intake flow in
api/ai_systems.py - that stays exactly as it was. This module adds the
company-wide questionnaire, the company applicability engine result, and the
sector starter packs.

Every applicability determination is persisted as an ApplicabilityDecision
(scope="organization") so it is reproducible and reviewable, and it is always
labelled by regulation_type (legal / certification / voluntary / best-practice)
and confidence (never false certainty).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_app.core.database import get_db
from aegis_app.core.config import settings
from aegis_app.api.deps import get_current_user
from aegis_app.models.models import User, Organization, OrganizationProfile, ApplicabilityDecision, AuditEvent
from aegis_app.schemas.schemas import (
    OnboardingProfileInput, CompanyApplicabilityResponse, FrameworkExposureItem,
)
from aegis_app.services.company_applicability import company_applicability_engine

router = APIRouter(prefix="/onboarding", tags=["SME Onboarding"])

_DATA = Path(__file__).resolve().parent.parent / "data"
_PROFILE_FACT_FIELDS = [
    "headquarters_country", "operating_countries", "employee_count", "industry",
    "sells_to_enterprises", "sells_to_government", "sells_to_financial_institutions", "sells_to_healthcare",
    "develops_ai_products", "deploys_ai_internally", "uses_generative_ai", "builds_ai_agents", "uses_rag",
    "uses_third_party_models", "makes_decisions_about_people", "decision_domains", "uses_biometrics",
    "ai_providers", "data_types", "sells_software", "is_saas", "sells_connected_hardware", "is_iot",
    "has_embedded_software", "is_cybersecurity_product", "product_marketed_in_eu",
    "soc2_required", "iso27001_required", "gets_security_questionnaires", "existing_certifications",
    "has_compliance_staff", "has_security_staff", "starter_pack",
]


def _profile_to_dict(p: OrganizationProfile) -> Dict[str, Any]:
    return {f: getattr(p, f) for f in _PROFILE_FACT_FIELDS} | {
        "id": p.id,
        "organization_id": p.organization_id,
        "answers": p.answers or {},
        "completed": bool(p.completed_at),
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


async def _get_profile(db: AsyncSession, user: User) -> OrganizationProfile | None:
    row = await db.execute(
        select(OrganizationProfile).where(OrganizationProfile.organization_id == user.organization_id)
    )
    return row.scalars().first()


@router.get("/profile")
async def get_profile(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    prof = await _get_profile(db, current_user)
    if not prof:
        return {"exists": False, "profile": OnboardingProfileInput().model_dump()}
    return {"exists": True, "profile": _profile_to_dict(prof)}


@router.put("/profile")
async def upsert_profile(
    payload: OnboardingProfileInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    prof = await _get_profile(db, current_user)
    if not prof:
        prof = OrganizationProfile(
            tenant_id=current_user.tenant_id,
            organization_id=current_user.organization_id,
        )
        db.add(prof)

    data = payload.model_dump()
    for f in _PROFILE_FACT_FIELDS:
        if f in data and data[f] is not None:
            setattr(prof, f, data[f])
    prof.answers = data.get("answers") or data
    if payload.completed and not prof.completed_at:
        prof.completed_at = datetime.now(timezone.utc)

    # Keep the Organization row's coarse fields in sync so existing enterprise
    # screens that read Organization (dashboard, reports) reflect onboarding too.
    org = (await db.execute(select(Organization).where(Organization.id == current_user.organization_id))).scalars().first()
    if org:
        if payload.company_name:
            org.name = payload.company_name
        org.industry = payload.industry or org.industry
        org.headquarters_country = payload.headquarters_country or org.headquarters_country
        org.countries_operating = payload.operating_countries or org.countries_operating
        org.employee_count = payload.employee_count or org.employee_count
        org.is_financial_institution = payload.sells_to_financial_institutions or org.is_financial_institution
        org.eu_market_exposure = company_applicability_engine.build_facts(data)["eu_exposed"]

    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="UPSERT_ONBOARDING_PROFILE", object_type="OrganizationProfile",
        object_id=current_user.organization_id, changes={"completed": bool(payload.completed)},
    ))
    await db.commit()
    await db.refresh(prof)
    return {"exists": True, "profile": _profile_to_dict(prof)}


@router.get("/applicability", response_model=CompanyApplicabilityResponse)
async def company_applicability(
    persist: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prof = await _get_profile(db, current_user)
    if not prof:
        raise HTTPException(status_code=404, detail="Complete onboarding first (PUT /onboarding/profile)")

    profile_dict = _profile_to_dict(prof)
    outcome = company_applicability_engine.evaluate(profile_dict)
    now = datetime.now(timezone.utc)

    decision_id = None
    if persist:
        org = (await db.execute(select(Organization).where(Organization.id == current_user.organization_id))).scalars().first()
        # supersede the previous org-scope decision rather than overwrite it (spec: history never lost)
        prev = (await db.execute(
            select(ApplicabilityDecision).where(
                ApplicabilityDecision.organization_id == current_user.organization_id,
                ApplicabilityDecision.scope == "organization",
                ApplicabilityDecision.superseded_by_id.is_(None),
            )
        )).scalars().all()
        top = outcome["exposures"][0] if outcome["exposures"] else None
        decision = ApplicabilityDecision(
            tenant_id=current_user.tenant_id,
            organization_id=current_user.organization_id,
            system_id=None,
            system_name=f"{org.name if org else 'Organization'} (company-wide)",
            input_snapshot=profile_dict,
            scope="organization",
            decision_status=(top["decision_status"] if top else "UNKNOWN"),
            risk_level="N/A (company-level)",
            eu_ai_act_classification=next(
                (e["exposure_label"] for e in outcome["exposures"] if e["framework_key"] == "eu_ai_act"),
                "Not triggered",
            ),
            rationale="Company-wide framework exposure from onboarding questionnaire. See framework_exposure for the per-framework reasoning.",
            recommended_frameworks=[e["framework_key"] for e in outcome["exposures"]],
            required_controls=[],
            rules_fired=outcome["rules_fired"],
            confidence="Rule-Based (company)",
            unresolved_questions=outcome["open_questions"],
            framework_exposure=outcome["exposures"],
            open_questions=outcome["open_questions"],
            requires_legal_review=outcome["legal_review_recommended"],
            ruleset_version=outcome["ruleset_version"],
        )
        db.add(decision)
        await db.flush()
        for p in prev:
            p.superseded_by_id = decision.id
        await db.commit()
        decision_id = decision.id

    return CompanyApplicabilityResponse(
        ruleset_version=outcome["ruleset_version"],
        generated_at=now,
        profile_complete=bool(prof.completed_at),
        exposures=[FrameworkExposureItem(**e) for e in outcome["exposures"]],
        legal_review_recommended=outcome["legal_review_recommended"],
        legal_review_frameworks=outcome["legal_review_frameworks"],
        open_questions=outcome["open_questions"],
        summary=outcome["summary"],
        disclaimer=settings.LEGAL_DISCLAIMER,
        decision_id=decision_id,
    )


@router.get("/starter-packs")
async def starter_packs(current_user: User = Depends(get_current_user)):
    with open(_DATA / "starter_packs.json", "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/frameworks-catalog")
async def frameworks_catalog(current_user: User = Depends(get_current_user)):
    """Unified catalog the SME UI shows: commercial (SOC2/ISO) metadata-only
    frameworks + a pointer to the full regulatory catalog. Preserves the
    existing /frameworks and /regulatory/frameworks endpoints untouched."""
    with open(_DATA / "commercial_frameworks.json", "r", encoding="utf-8") as f:
        commercial = json.load(f)
    return {
        "commercial_frameworks": commercial["frameworks"],
        "note": commercial["note"],
        "regulatory_catalog_endpoint": "/api/v1/regulatory/frameworks",
        "legacy_catalog_endpoint": "/api/v1/frameworks",
    }
