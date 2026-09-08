"""
AI Trust Score (spec sections 7, 22, 27).

A company-level rollup of the SAME control/evidence/finding/effectiveness state
the enterprise dashboard already uses (services/scoring.py) - grouped into six
plain-language dimensions a founder understands. Nothing here invents a number:
every dimension score is `calculate_compliance_scores` run over the real
CustomerControl rows in that dimension, and `has_data` is False (score 0, basis
explains why) when a tenant has no controls yet.
"""

from typing import Any, Dict, List

from aegis_app.services.scoring import calculate_compliance_scores

# unified-control domain -> Trust Score dimension
DIMENSION_MAP: Dict[str, str] = {
    "AI Governance": "ai_governance",
    "Accountability": "ai_governance",
    "AI Inventory": "ai_governance",
    "Risk Management": "ai_governance",
    "Transparency": "ai_governance",
    "Testing & Validation": "ai_governance",
    "Fairness & Bias": "ai_governance",
    "Prompt Security": "ai_security",
    "Model Security": "ai_security",
    "Accuracy & Robustness": "ai_security",
    "Privacy": "privacy",
    "Vendor Management": "vendor_risk",
    "Supply Chain Security": "vendor_risk",
    "Agent Security": "agent_security",
    "Human Oversight": "agent_security",
    "Secure Development": "secure_development",
    "Logging": "secure_development",
    "Incident Management": "secure_development",
    "Vulnerability Management": "secure_development",
    "Resilience": "secure_development",
}

DIMENSION_LABELS = {
    "ai_governance": "AI Governance",
    "ai_security": "AI Security",
    "privacy": "Privacy",
    "vendor_risk": "Vendor Risk",
    "agent_security": "Agent Security",
    "secure_development": "Secure Development",
}


def compute_trust_score(
    unified_controls: List[Dict[str, Any]],
    customer_control_state: Dict[str, Dict[str, Any]],
    evidence_counts: Dict[str, int],
    open_findings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    unified_controls: [{code, domain, ...}] from unified_controls.json
    customer_control_state: {control_code: {"status":..., "effectiveness":...}} - the tenant's real CustomerControl rows
    evidence_counts: {control_code: n}
    open_findings: [{"severity":..., "status":...}] tenant's open findings
    """
    # bucket controls by dimension, attaching the tenant's real state (or the
    # "Not Started" default for a control the tenant has not begun)
    by_dim: Dict[str, List[Dict[str, Any]]] = {d: [] for d in DIMENSION_LABELS}
    for uc in unified_controls:
        dim = DIMENSION_MAP.get(uc.get("domain", ""), "ai_governance")
        code = uc.get("code") or uc.get("control_id") or uc.get("id")
        state = customer_control_state.get(code, {})
        by_dim[dim].append({
            "control_id": code,
            "status": state.get("status", "Not Started"),
            "effectiveness": state.get("effectiveness", "Ineffective"),
        })

    has_any_state = len(customer_control_state) > 0
    dimensions = []
    dim_scores_present = []
    for key, label in DIMENSION_LABELS.items():
        ctrls = by_dim[key]
        # findings scoped to this dimension's controls (plus unscoped findings spread lightly)
        dim_control_ids = {c["control_id"] for c in ctrls}
        dim_findings = [f for f in open_findings if f.get("control_id") in dim_control_ids]
        s = calculate_compliance_scores(ctrls, evidence_counts, dim_findings)
        started = sum(1 for c in ctrls if c["status"] != "Not Started")
        if started == 0:
            basis = f"0 of {len(ctrls)} {label} controls started"
            score = 0.0
        else:
            basis = (f"{started}/{len(ctrls)} controls started, "
                     f"impl {s['implementation_score']}%, evidence {s['evidence_score']}%, "
                     f"effectiveness {s['effectiveness_score']}%")
            score = s["overall_readiness"]
            dim_scores_present.append(score)
        dimensions.append({"key": key, "label": label, "score": score, "basis": basis})

    if dim_scores_present:
        overall = round(sum(dim_scores_present) / len(dim_scores_present), 1)
    else:
        overall = 0.0

    return {
        "ai_trust_score": overall,
        "dimensions": dimensions,
        "has_data": has_any_state,
        "method": ("Mean of the started dimensions; each dimension = implementation 40% + evidence 35% "
                   "+ effectiveness 25% - findings, over that dimension's unified controls. "
                   "Dimensions with no started controls score 0 and are excluded from the mean."),
    }
