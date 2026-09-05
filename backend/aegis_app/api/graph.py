"""
Regulatory & Asset Knowledge Graph — query endpoints.

Design note: the 17 authoritative frameworks/requirements/unified-controls/
crosswalk-mapping content already exists as curated, cited, real data
(services/crosswalk.py, data/*.json) built and verified in an earlier pass.
Per the platform's own build rules ("do not rebuild working modules
unnecessarily", "do not fabricate regulatory data"), this module does NOT
re-model that content into new database tables - doing so would mean
re-authoring/re-migrating real regulatory content for no functional gain.

Instead, this module implements genuine graph *traversal queries* by joining
that static regulatory knowledge with the tenant's live database records
(AISystem, AIModel, Vendor, Evidence, Risk, AIAgent) - which is exactly what
the spec itself permits: "Do not require Neo4j initially if PostgreSQL is
sufficient. Implement graph semantics using relational tables and APIs."

Every endpoint here answers one of the spec's example questions with a real
computed query, not a canned response.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.models.models import AISystem, AIModel, AISystemModelLink, Vendor, Evidence, EvidenceControlMap, AIAgent, User
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.api.deps import get_current_user

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


@router.get("/requirement/{requirement_id}/affected-systems", response_model=Dict[str, Any])
async def requirement_affected_systems(
    requirement_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Graph edge: Requirement <- SUBJECT_TO <- AISystem.
    Finds which framework owns this requirement, then returns every AI System
    in this tenant whose applicable_frameworks includes that framework.
    """
    owning_framework = None
    requirement_meta = None
    for fw in crosswalk_service.get_all_frameworks_raw():
        for ch in fw.get("chapters", []):
            for req in ch.get("requirements", []):
                if req["id"] == requirement_id:
                    owning_framework = fw
                    requirement_meta = req
                    break
    if not owning_framework:
        raise HTTPException(status_code=404, detail="Requirement not found in any loaded framework")

    result = await db.execute(select(AISystem).where(AISystem.tenant_id == current_user.tenant_id))
    all_systems = result.scalars().all()
    affected = [
        {"id": s.id, "name": s.name, "risk_classification": s.risk_classification}
        for s in all_systems if owning_framework["id"] in (s.applicable_frameworks or [])
    ]

    return {
        "requirement_id": requirement_id,
        "requirement_title": requirement_meta.get("title"),
        "framework_id": owning_framework["id"],
        "framework_name": owning_framework["short_name"],
        "affected_systems_count": len(affected),
        "affected_systems": affected,
    }


@router.get("/controls/multi-framework", response_model=List[Dict[str, Any]])
async def controls_satisfying_multiple_frameworks(
    frameworks: str = Query(..., description="Comma-separated framework IDs, e.g. eu_ai_act,nist_ai_rmf,owasp_llm"),
    current_user: User = Depends(get_current_user)
):
    """
    Graph traversal: UnifiedControl -[MAPS_TO]-> Requirement -[CONTAINS]-> Framework,
    filtered to controls whose mappings cover ALL requested frameworks at once.
    """
    requested = set(f.strip() for f in frameworks.split(",") if f.strip())
    if not requested:
        raise HTTPException(status_code=400, detail="Provide at least one framework id")

    matrix = crosswalk_service.get_crosswalk_matrix()
    matching = []
    for row in matrix:
        covered = {m["framework_id"] for m in row["mappings"]}
        if requested.issubset(covered):
            matching.append({
                "control_id": row["control_id"],
                "control_code": row["control_code"],
                "control_title": row["control_title"],
                "domain": row["domain"],
                "covers_frameworks": sorted(covered),
            })
    return matching


@router.get("/evidence/highest-coverage", response_model=List[Dict[str, Any]])
async def evidence_with_highest_requirement_coverage(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Graph traversal: Evidence -[SUPPORTS]-> UnifiedControl -[MAPS_TO]-> Requirement.
    Ranks this tenant's evidence by how many distinct regulatory requirements
    it transitively satisfies through its control mappings.
    """
    result = await db.execute(
        select(Evidence).where(Evidence.tenant_id == current_user.tenant_id)
    )
    evidence_items = result.scalars().all()

    ranked = []
    for ev in evidence_items:
        map_res = await db.execute(select(EvidenceControlMap.control_id).where(EvidenceControlMap.evidence_id == ev.id))
        control_ids = [row[0] for row in map_res.all()]
        if not control_ids:
            continue
        coverage = crosswalk_service.resolve_evidence_coverage(control_ids)
        ranked.append({
            "evidence_id": ev.id,
            "title": ev.title,
            "approval_status": ev.approval_status,
            "mapped_controls_count": len(control_ids),
            "satisfied_requirements_count": coverage["satisfied_requirements_count"],
            "satisfied_frameworks_count": coverage["satisfied_frameworks_count"],
        })

    ranked.sort(key=lambda x: x["satisfied_requirements_count"], reverse=True)
    return ranked[:limit]


@router.get("/vendors/regulatory-exposure", response_model=List[Dict[str, Any]])
async def vendors_by_regulatory_exposure(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Graph traversal: Vendor -[PROVIDES]-> Model -> AISystem -[SUBJECT_TO]-> Requirement.
    Ranks vendors by the total count of (system x applicable-framework-requirement)
    combinations their models are exposed to - i.e. which vendor's failure/exit
    would create the largest regulatory surface to reassess.
    """
    vendor_res = await db.execute(select(Vendor).where(Vendor.tenant_id == current_user.tenant_id))
    vendors = vendor_res.scalars().all()

    fw_requirement_counts = {
        fw["id"]: sum(len(ch.get("requirements", [])) for ch in fw.get("chapters", []))
        for fw in crosswalk_service.get_all_frameworks_raw()
    }

    exposure = []
    for v in vendors:
        model_res = await db.execute(select(AIModel.id).where(AIModel.vendor_id == v.id, AIModel.tenant_id == current_user.tenant_id))
        model_ids = [row[0] for row in model_res.all()]
        if not model_ids:
            exposure.append({"vendor_id": v.id, "vendor_name": v.name, "risk_rating": v.risk_rating,
                              "dependent_systems_count": 0, "regulatory_requirement_exposure": 0})
            continue

        link_res = await db.execute(select(AISystemModelLink.system_id).where(AISystemModelLink.model_id.in_(model_ids)))
        system_ids = set(row[0] for row in link_res.all())
        legacy_res = await db.execute(select(AIModel.system_id).where(AIModel.id.in_(model_ids), AIModel.system_id.isnot(None)))
        system_ids.update(row[0] for row in legacy_res.all())

        total_exposure = 0
        if system_ids:
            sys_res = await db.execute(select(AISystem.applicable_frameworks).where(AISystem.id.in_(system_ids)))
            for row in sys_res.all():
                for fw_id in (row[0] or []):
                    total_exposure += fw_requirement_counts.get(fw_id, 0)

        exposure.append({
            "vendor_id": v.id, "vendor_name": v.name, "risk_rating": v.risk_rating,
            "dependent_systems_count": len(system_ids),
            "regulatory_requirement_exposure": total_exposure,
        })

    exposure.sort(key=lambda x: x["regulatory_requirement_exposure"], reverse=True)
    return exposure


@router.get("/models/shared-high-risk", response_model=List[Dict[str, Any]])
async def high_risk_systems_sharing_a_model(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Graph traversal: AISystem -[USES]-> Model <-[USES]- AISystem.
    Finds foundation models used by more than one high-risk system in this
    tenant - a concentration-risk view (one model outage/incident affects
    multiple high-risk systems at once).
    """
    model_res = await db.execute(select(AIModel).where(AIModel.tenant_id == current_user.tenant_id))
    models = model_res.scalars().all()

    clusters = []
    for m in models:
        link_res = await db.execute(select(AISystemModelLink.system_id).where(AISystemModelLink.model_id == m.id))
        system_ids = set(row[0] for row in link_res.all())
        if m.system_id:
            system_ids.add(m.system_id)
        if len(system_ids) < 2:
            continue

        sys_res = await db.execute(select(AISystem).where(AISystem.id.in_(system_ids), AISystem.tenant_id == current_user.tenant_id))
        systems = sys_res.scalars().all()
        high_risk = [s for s in systems if "High" in (s.risk_classification or "") or "Prohibited" in (s.risk_classification or "")]
        if len(high_risk) >= 2:
            clusters.append({
                "model_id": m.id, "model_name": m.name, "provider": m.provider,
                "high_risk_systems_count": len(high_risk),
                "high_risk_systems": [{"id": s.id, "name": s.name} for s in high_risk],
            })

    clusters.sort(key=lambda x: x["high_risk_systems_count"], reverse=True)
    return clusters


@router.get("/agents/tool-dependents", response_model=Dict[str, Any])
async def agents_depending_on_tool(
    tool: str = Query(..., description="Tool name to check, e.g. 'jira_api_client' or a compromised dependency name"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Graph traversal: Agent -[USES]-> Tool. Answers "which agents depend on a
    (potentially compromised) tool" - the exact incident-response query the
    spec asks for, e.g. after a supply-chain advisory names a library/tool.
    """
    result = await db.execute(select(AIAgent).where(AIAgent.tenant_id == current_user.tenant_id))
    agents = result.scalars().all()
    dependents = [
        {"id": a.id, "name": a.name, "risk_score": a.risk_score, "status": a.status}
        for a in agents if tool.lower() in [t.lower() for t in (a.tools or [])]
    ]
    return {"tool": tool, "dependent_agents_count": len(dependents), "dependent_agents": dependents}
