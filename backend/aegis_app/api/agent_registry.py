"""
Agent Registry Endpoints.

Full CRUD for autonomous AI agents, plus the Agent Permission Graph and
Agent Dependency Graph query views the spec requires (e.g. "which agents
have write access to GitHub", "which agents have no human approval gate").

Note: GET /security/agents and POST /security/agents/{id}/kill-switch
(api/security.py) continue to work unchanged for backward compatibility with
the existing frontend Security tab - this router is the new, complete
registry surface (create/update/delete/permission-graph) that didn't exist
before.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.models.models import AIAgent, AISystem, User, AuditEvent
from aegis_app.schemas.schemas import AgentCreate, AgentUpdate, AgentResponse
from aegis_app.services.agent_risk import calculate_agent_risk_score
from aegis_app.api.deps import get_current_user, require_governance_write, require_operational_control

router = APIRouter(prefix="/agents", tags=["Agent Registry"])


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(AIAgent).where(AIAgent.tenant_id == current_user.tenant_id).order_by(AIAgent.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=AgentResponse)
async def create_agent(
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    sys_res = await db.execute(select(AISystem).where(AISystem.id == payload.system_id, AISystem.tenant_id == current_user.tenant_id))
    if not sys_res.scalars().first():
        raise HTTPException(status_code=404, detail="AI System not found for this tenant")

    data = payload.model_dump()
    data["risk_score"] = calculate_agent_risk_score({**data, "kill_switch_active": True})
    agent = AIAgent(tenant_id=current_user.tenant_id, kill_switch_active=True, **data)
    db.add(agent)
    await db.flush()

    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="CREATE_AGENT", object_type="AIAgent", object_id=agent.id,
        changes={"name": agent.name, "risk_score": agent.risk_score, "autonomy_level": agent.autonomy_level}
    ))
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/permission-graph", response_model=Dict[str, Any])
async def agent_permission_graph(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Answers the spec's example governance questions directly from the
    Agent Registry data - real queries, not canned answers.
    """
    result = await db.execute(select(AIAgent).where(AIAgent.tenant_id == current_user.tenant_id))
    agents = result.scalars().all()

    def summarize(a: AIAgent) -> Dict[str, Any]:
        return {"id": a.id, "name": a.name, "risk_score": a.risk_score, "autonomy_level": a.autonomy_level}

    return {
        "total_agents": len(agents),
        "agents_with_github_write": [summarize(a) for a in agents if a.has_git_write_access],
        "agents_with_code_execution": [summarize(a) for a in agents if a.has_code_execution],
        "agents_with_pii_access": [summarize(a) for a in agents if a.accesses_pii],
        "agents_with_financial_actions": [summarize(a) for a in agents if a.has_payment_access],
        "agents_that_can_invoke_other_agents": [summarize(a) for a in agents if a.can_invoke_other_agents],
        "agents_without_human_approval_gate": [summarize(a) for a in agents if not a.human_approval_required],
        "agents_with_no_kill_switch": [summarize(a) for a in agents if not a.kill_switch_active],
        "highest_risk_agents": sorted([summarize(a) for a in agents], key=lambda x: x["risk_score"], reverse=True)[:10],
    }


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(AIAgent).where(AIAgent.id == agent_id, AIAgent.tenant_id == current_user.tenant_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/dependents", response_model=Dict[str, Any])
async def get_agent_dependents(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Agent Dependency Graph: parent agent, child agents, owning system, model used."""
    result = await db.execute(select(AIAgent).where(AIAgent.id == agent_id, AIAgent.tenant_id == current_user.tenant_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    children_res = await db.execute(select(AIAgent).where(AIAgent.parent_agent_id == agent_id, AIAgent.tenant_id == current_user.tenant_id))
    children = [{"id": c.id, "name": c.name, "risk_score": c.risk_score} for c in children_res.scalars().all()]

    parent = None
    if agent.parent_agent_id:
        p_res = await db.execute(select(AIAgent).where(AIAgent.id == agent.parent_agent_id))
        p = p_res.scalars().first()
        parent = {"id": p.id, "name": p.name} if p else None

    return {"agent_id": agent.id, "agent_name": agent.name, "parent_agent": parent, "child_agents": children}


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_governance_write)
):
    result = await db.execute(select(AIAgent).where(AIAgent.id == agent_id, AIAgent.tenant_id == current_user.tenant_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    # Any permission/autonomy change must recompute the risk score - this is
    # exactly the kind of drift Continuous Policy Monitoring (a later phase)
    # will watch for; today it is at least recalculated on every edit rather
    # than going stale.
    current_state = {
        "has_code_execution": agent.has_code_execution, "has_database_access": agent.has_database_access,
        "has_payment_access": agent.has_payment_access, "has_email_access": agent.has_email_access,
        "has_git_access": agent.has_git_access, "has_git_write_access": agent.has_git_write_access,
        "has_external_web_access": agent.has_external_web_access,
        "has_external_communication_access": agent.has_external_communication_access,
        "can_invoke_other_agents": agent.can_invoke_other_agents, "accesses_pii": agent.accesses_pii,
        "autonomy_level": agent.autonomy_level, "human_approval_required": agent.human_approval_required,
        "kill_switch_active": agent.kill_switch_active,
    }
    agent.risk_score = calculate_agent_risk_score(current_state)

    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="UPDATE_AGENT", object_type="AIAgent", object_id=agent.id,
        changes={**update_data, "recalculated_risk_score": agent.risk_score}
    ))
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", response_model=Dict[str, str])
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operational_control)
):
    result = await db.execute(select(AIAgent).where(AIAgent.id == agent_id, AIAgent.tenant_id == current_user.tenant_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await db.delete(agent)
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_id=current_user.id, actor_email=current_user.email,
        action="DELETE_AGENT", object_type="AIAgent", object_id=agent_id, changes={"name": agent.name}
    ))
    await db.commit()
    return {"status": "deleted", "id": agent_id}
