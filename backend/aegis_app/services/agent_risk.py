"""
Explainable Agent Risk Scoring.

A simple, documented, additive heuristic - not a black box, not a fabricated
"AI risk score." Each factor is a concrete permission/autonomy attribute on
the agent record. This mirrors the existing compliance scoring pattern in
services/scoring.py (weighted, capped, fully reproducible from stored fields).
"""

from typing import Dict, Any

# Points contributed by each capability. Weighted toward the actions with the
# largest real-world blast radius (financial actions, code execution, write
# access to source control) over lower-risk ones (read-only data access).
CAPABILITY_WEIGHTS = {
    "has_payment_access": 25,
    "has_code_execution": 20,
    "has_git_write_access": 18,
    "can_invoke_other_agents": 15,
    "has_database_access": 12,
    "accesses_pii": 12,
    "has_external_communication_access": 10,
    "has_external_web_access": 8,
    "has_git_access": 5,
    "has_email_access": 5,
}

AUTONOMY_WEIGHTS = {
    "Supervised": 0,
    "Semi-Autonomous": 10,
    "Fully Autonomous": 25,
}


def calculate_agent_risk_score(agent: Dict[str, Any]) -> float:
    """
    Returns a 0-100 explainable risk score. Formula:
      sum(capability weights for enabled capabilities)
      + autonomy weight
      + 15 if no human approval gate is configured
      - 10 if a kill switch is active (partial mitigation, not elimination)
    Capped at 0-100.
    """
    score = 0.0
    for field, weight in CAPABILITY_WEIGHTS.items():
        if agent.get(field):
            score += weight

    score += AUTONOMY_WEIGHTS.get(agent.get("autonomy_level", "Supervised"), 0)

    if not agent.get("human_approval_required", True):
        score += 15

    if agent.get("kill_switch_active", True):
        score -= 10

    return max(0.0, min(100.0, round(score, 1)))
