"""
SME experience endpoints (spec sections 7, 16, 22, 27).

Additive. These compute over the SAME tenant data the enterprise screens use -
no new source of truth, no fabricated numbers. If a tenant has no controls /
registry entries yet, the responses say so (has_data=false, empty action list
with an explanatory count) rather than inventing a score.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_app.core.database import get_db
from aegis_app.api.deps import get_current_user
from aegis_app.models.models import (
    User, AISystem, AIModel, AIAgent, Vendor, CustomerControl, Evidence,
    EvidenceControlMap, Finding, PolicyDocument, OrganizationProfile, Assessment,
)
from aegis_app.schemas.schemas import (
    TrustScoreResponse, TrustScoreDimension, NextActionsResponse, NextAction,
)
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.services.trust_score import compute_trust_score

router = APIRouter(prefix="/sme", tags=["SME Experience"])

_PROVIDER_LABELS = {
    "openai": "OpenAI", "anthropic": "Anthropic", "google": "Google Gemini",
    "azure_openai": "Microsoft Azure OpenAI", "aws_bedrock": "AWS Bedrock",
    "meta": "Meta", "mistral": "Mistral", "cohere": "Cohere",
    "huggingface": "Hugging Face", "self_hosted": "Self-hosted / open-source models",
}


async def _tenant_control_state(db: AsyncSession, tenant_id: str) -> Dict[str, Dict[str, Any]]:
    rows = (await db.execute(
        select(CustomerControl).where(CustomerControl.tenant_id == tenant_id)
    )).scalars().all()
    return {c.control_id: {"status": c.status, "effectiveness": c.effectiveness} for c in rows}


async def _evidence_counts(db: AsyncSession, tenant_id: str) -> Dict[str, int]:
    rows = (await db.execute(
        select(EvidenceControlMap.control_id, func.count(EvidenceControlMap.id))
        .join(Evidence, Evidence.id == EvidenceControlMap.evidence_id)
        .where(Evidence.tenant_id == tenant_id)
        .group_by(EvidenceControlMap.control_id)
    )).all()
    return {r[0]: r[1] for r in rows}


@router.get("/trust-score", response_model=TrustScoreResponse)
async def trust_score(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    tid = current_user.tenant_id
    control_state = await _tenant_control_state(db, tid)
    evidence_counts = await _evidence_counts(db, tid)

    findings = (await db.execute(select(Finding).where(Finding.tenant_id == tid))).scalars().all()
    open_findings = [
        {"severity": f.severity, "status": f.status, "control_id": f.control_id}
        for f in findings if f.status not in ("Resolved", "Accepted Risk")
    ]

    unified = crosswalk_service.get_unified_controls()
    result = compute_trust_score(unified, control_state, evidence_counts, open_findings)

    n_sys = (await db.execute(select(func.count(AISystem.id)).where(AISystem.tenant_id == tid))).scalar() or 0
    n_model = (await db.execute(select(func.count(AIModel.id)).where(AIModel.tenant_id == tid))).scalar() or 0
    n_agent = (await db.execute(select(func.count(AIAgent.id)).where(AIAgent.tenant_id == tid))).scalar() or 0
    n_vendor = (await db.execute(select(func.count(Vendor.id)).where(Vendor.tenant_id == tid))).scalar() or 0

    implemented = sum(1 for s in control_state.values() if s["status"] in ("Implemented", "Tested"))
    with_ev = sum(1 for code in control_state if evidence_counts.get(code, 0) > 0)

    # evidence freshness: mean age in days of this tenant's evidence
    ev_dates = (await db.execute(
        select(Evidence.created_at).where(Evidence.tenant_id == tid)
    )).scalars().all()
    freshness = None
    if ev_dates:
        now = datetime.now(timezone.utc)
        ages = []
        for d in ev_dates:
            if d is None:
                continue
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            ages.append((now - d).days)
        if ages:
            freshness = round(sum(ages) / len(ages), 1)

    sev_counts: Dict[str, int] = {}
    for f in open_findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1

    return TrustScoreResponse(
        ai_trust_score=result["ai_trust_score"],
        computed_at=datetime.now(timezone.utc),
        dimensions=[TrustScoreDimension(**d) for d in result["dimensions"]],
        controls_total=len(unified),
        controls_implemented=implemented,
        controls_with_evidence=with_ev,
        open_findings=sev_counts,
        evidence_freshness_days=freshness,
        inventory={"ai_systems": n_sys, "models": n_model, "agents": n_agent, "vendors": n_vendor},
        method=result["method"],
        has_data=result["has_data"],
    )


@router.get("/next-actions", response_model=NextActionsResponse)
async def next_actions(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    tid = current_user.tenant_id
    actions: List[NextAction] = []

    prof = (await db.execute(
        select(OrganizationProfile).where(OrganizationProfile.organization_id == current_user.organization_id)
    )).scalars().first()

    vendors = (await db.execute(select(Vendor).where(Vendor.tenant_id == tid))).scalars().all()
    vendor_names_lc = {v.name.lower() for v in vendors}
    models = (await db.execute(select(AIModel).where(AIModel.tenant_id == tid))).scalars().all()
    agents = (await db.execute(select(AIAgent).where(AIAgent.tenant_id == tid))).scalars().all()
    policies = (await db.execute(select(PolicyDocument).where(PolicyDocument.tenant_id == tid))).scalars().all()
    findings = (await db.execute(select(Finding).where(Finding.tenant_id == tid))).scalars().all()
    control_state = await _tenant_control_state(db, tid)
    evidence_counts = await _evidence_counts(db, tid)

    # 1. AI providers declared in onboarding but not in the Vendor registry
    declared_providers = list((prof.ai_providers if prof else []) or [])
    for prov in declared_providers:
        label = _PROVIDER_LABELS.get(prov, prov.replace("_", " ").title())
        if not any(label.lower() in vn or vn in label.lower() for vn in vendor_names_lc):
            actions.append(NextAction(
                id=f"register-vendor-{prov}",
                title=f"Register {label} in your Vendor Registry",
                why_it_matters=(f"You told us you use {label}, but it is not in your vendor list. "
                                "Enterprise security reviews and GDPR/DPDP both expect a documented, "
                                "risk-assessed record of every AI provider that can touch your data."),
                risk="HIGH",
                bucket="TODAY",
                estimated_minutes=15,
                affected_areas=["GDPR", "EU AI Act", "NIST AI RMF", "OWASP GenAI", "Vendor Risk"],
                steps=[
                    f"Add {label} to Vendor Registry",
                    "Record data processing role, regions, retention and training-on-data setting",
                    "Attach the DPA / security documentation",
                    "Set approved and prohibited use cases",
                ],
                actions=["Register", "Assign"],
                source="onboarding_profile",
            ))

    # 2. No AI acceptable-use / GenAI usage policy
    policy_types = " ".join((p.policy_type or "") + " " + (p.title or "") for p in policies).lower()
    if not any(k in policy_types for k in ("acceptable use", "ai use", "generative ai", "ai usage")):
        actions.append(NextAction(
            id="policy-ai-acceptable-use",
            title="Approve an employee AI Acceptable Use policy",
            why_it_matters=("Without a written, acknowledged AI usage policy, staff may send customer or "
                            "confidential data to unapproved AI tools. This is the single most common "
                            "gap flagged in enterprise AI questionnaires."),
            risk="CRITICAL",
            bucket="TODAY",
            estimated_minutes=10,
            affected_areas=["GDPR", "EU AI Act", "NIST AI RMF", "ISO 42001"],
            steps=[
                "Generate the Acceptable AI Use policy from the template",
                "Edit for your company context",
                "Route for approval",
                "Collect employee acknowledgements",
                "Store the approved policy as evidence",
            ],
            actions=["Generate Policy", "Assign", "Upload Evidence"],
            source="policy_gap",
        ))

    # 3. Agents with production DB/code access and no human approval gate
    for a in agents:
        envs = [e.lower() for e in (a.environments or [])]
        risky = (a.has_database_access or a.has_code_execution or a.has_payment_access)
        if "production" in envs and risky and not a.human_approval_required:
            actions.append(NextAction(
                id=f"agent-guardrail-{a.id}",
                title=f"Add a human-approval gate to agent '{a.name}'",
                why_it_matters=(f"Agent '{a.name}' runs in production with "
                                f"{'database ' if a.has_database_access else ''}"
                                f"{'code-execution ' if a.has_code_execution else ''}"
                                f"{'payment ' if a.has_payment_access else ''}access and no human approval. "
                                "This is 'excessive agency' (OWASP Agentic AI01) - a top agent risk."),
                risk="CRITICAL",
                bucket="TODAY",
                estimated_minutes=30,
                affected_areas=["OWASP Agentic", "MITRE ATLAS", "NIST AI RMF", "Agent Security"],
                steps=[
                    "Open the agent in Agent Registry",
                    "Enable 'human approval required' for state-changing actions",
                    "Scope tool permissions to least privilege",
                    "Verify the kill-switch is active",
                ],
                actions=["Fix", "Assign"],
                source="agent_registry",
            ))

    # 4. Open Critical/High findings
    for f in findings:
        if f.status in ("Resolved", "Accepted Risk"):
            continue
        if f.severity not in ("Critical", "High"):
            continue
        actions.append(NextAction(
            id=f"finding-{f.id}",
            title=f"Resolve finding: {f.title}",
            why_it_matters=f.description or "An open compliance/security finding is reducing your AI Trust Score.",
            risk=f.severity.upper(),
            bucket="TODAY" if f.severity == "Critical" else "THIS_WEEK",
            estimated_minutes=60,
            affected_areas=[f.control_id] if f.control_id else ["Findings"],
            steps=["Open the finding", "Assign an owner and due date", "Complete remediation", "Attach closure evidence", "Review and close"],
            actions=["Remediate", "Assign", "Upload Evidence"],
            source="finding",
        ))

    # 5. Models with no linked vendor
    for m in models:
        if not m.vendor_id:
            actions.append(NextAction(
                id=f"model-vendor-{m.id}",
                title=f"Link model '{m.name}' to a vendor",
                why_it_matters="A model with no vendor record has no due-diligence, DPA or data-handling trail behind it.",
                risk="MEDIUM",
                bucket="THIS_WEEK",
                estimated_minutes=10,
                affected_areas=["Supply Chain Security", "Vendor Risk", "NIST SP 800-161"],
                steps=["Open the model in Model Registry", "Select or create its vendor", "Confirm hosting type and data handling"],
                actions=["Fix", "Assign"],
                source="model_registry",
            ))

    # 6. Required controls not started (grouped)
    not_started = [code for code, s in control_state.items() if s["status"] == "Not Started"]
    if not control_state:
        unified = crosswalk_service.get_unified_controls()
        actions.append(NextAction(
            id="controls-bootstrap",
            title=f"Start your {len(unified)} unified AI controls",
            why_it_matters=("You have not begun tracking any controls yet. The unified control library lets one "
                            "piece of evidence satisfy many frameworks at once."),
            risk="HIGH",
            bucket="THIS_WEEK",
            estimated_minutes=45,
            affected_areas=["All frameworks"],
            steps=["Open Compliance → Controls", "Set an owner per control", "Mark current status honestly", "Attach any evidence you already have"],
            actions=["Assign"],
            source="controls",
        ))
    elif not_started:
        actions.append(NextAction(
            id="controls-not-started",
            title=f"{len(not_started)} controls are still 'Not Started'",
            why_it_matters="Unstarted controls pull down every framework readiness score they map to.",
            risk="MEDIUM",
            bucket="NEXT",
            estimated_minutes=30,
            affected_areas=["All frameworks"],
            steps=["Filter Controls by 'Not Started'", "Assign owners", "Set target dates"],
            actions=["Assign"],
            source="controls",
        ))

    # 7. Implemented controls with no evidence
    missing_ev = [code for code, s in control_state.items()
                  if s["status"] in ("Implemented", "Tested") and evidence_counts.get(code, 0) == 0]
    if missing_ev:
        actions.append(NextAction(
            id="evidence-gap",
            title=f"Attach evidence to {len(missing_ev)} implemented control(s)",
            why_it_matters="A control marked implemented with no evidence will not pass an auditor or customer review.",
            risk="MEDIUM",
            bucket="NEXT",
            estimated_minutes=20,
            affected_areas=["Evidence", "Auditor Review"],
            steps=["Open each implemented control", "Upload the policy/config/log that proves it", "Map the evidence to the control"],
            actions=["Upload Evidence"],
            source="evidence_gap",
        ))

    order = {"TODAY": 0, "THIS_WEEK": 1, "NEXT": 2}
    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    actions.sort(key=lambda a: (order.get(a.bucket, 9), risk_order.get(a.risk, 9)))

    counts: Dict[str, int] = {}
    for a in actions:
        counts[a.bucket] = counts.get(a.bucket, 0) + 1

    return NextActionsResponse(generated_at=datetime.now(timezone.utc), actions=actions, counts=counts)


@router.get("/sales-readiness")
async def sales_readiness(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Enterprise Sales Readiness (spec section 27) - which common procurement
    blockers are still open, derived from real state."""
    tid = current_user.tenant_id
    control_state = await _tenant_control_state(db, tid)
    evidence_counts = await _evidence_counts(db, tid)
    policies = (await db.execute(select(PolicyDocument).where(PolicyDocument.tenant_id == tid))).scalars().all()
    vendors = (await db.execute(select(Vendor).where(Vendor.tenant_id == tid))).scalars().all()
    systems = (await db.execute(select(func.count(AISystem.id)).where(AISystem.tenant_id == tid))).scalar() or 0
    ptypes = " ".join((p.policy_type or "") + " " + (p.title or "") for p in policies).lower()

    checklist = [
        {"item": "AI acceptable use policy", "met": any(k in ptypes for k in ("acceptable use", "ai use", "generative ai")), "blocks_procurement": True},
        {"item": "AI system inventory populated", "met": systems > 0, "blocks_procurement": True},
        {"item": "Vendor / AI provider risk review", "met": any(v.risk_rating and v.dpa_signed for v in vendors), "blocks_procurement": True},
        {"item": "DPA in place with AI providers", "met": all(v.dpa_signed for v in vendors) and len(vendors) > 0, "blocks_procurement": True},
        {"item": "AI incident response process", "met": any("incident" in ptypes for _ in [0]) or control_state.get("UC-AI-INC-001", {}).get("status") in ("Implemented", "Tested"), "blocks_procurement": True},
        {"item": "Security logging for AI activity", "met": control_state.get("UC-AI-LOG-001", {}).get("status") in ("Implemented", "Tested"), "blocks_procurement": False},
        {"item": "SOC 2 / ISO 27001 evidence", "met": any(("soc 2" in (c or "").lower() or "iso 27001" in (c or "").lower()) for v in vendors for c in (v.certifications or [])), "blocks_procurement": False},
    ]
    blocking_open = [c["item"] for c in checklist if c["blocks_procurement"] and not c["met"]]
    met = sum(1 for c in checklist if c["met"])
    return {
        "readiness_percentage": round(100 * met / len(checklist), 1),
        "checklist": checklist,
        "likely_procurement_blockers": blocking_open,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
