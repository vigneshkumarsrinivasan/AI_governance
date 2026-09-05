"""
Explainable Multi-Dimensional Compliance Readiness Scoring Service.
Calculates transparent readiness without arbitrary unexplainable scores.
"""

from typing import Dict, Any, List

def calculate_compliance_scores(
    controls: List[Dict[str, Any]],
    evidence_count_per_control: Dict[str, int],
    open_findings: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Computes distinct, explainable dimensions:
    1. Implementation Score (0-100)
    2. Evidence Completeness Score (0-100)
    3. Control Effectiveness Score (0-100)
    4. Overall Readiness Percentage (0-100)
    """
    total_controls = len(controls)
    if total_controls == 0:
        return {
            "overall_readiness": 0.0,
            "implementation_score": 0.0,
            "evidence_score": 0.0,
            "effectiveness_score": 0.0,
            "finding_deduction": 0.0
        }

    # 1. Implementation Score Calculation
    impl_points = 0.0
    for c in controls:
        status = c.get("status", "Not Started")
        if status in ["Implemented", "Tested"]:
            impl_points += 1.0
        elif status == "In Progress":
            impl_points += 0.5
        elif status == "Accepted Risk":
            impl_points += 0.75
        elif status == "Exempt":
            impl_points += 1.0
        else:
            impl_points += 0.0
            
    implementation_score = round((impl_points / total_controls) * 100.0, 1)

    # 2. Evidence Completeness Score
    controls_with_evidence = sum(
        1 for c in controls if evidence_count_per_control.get(c.get("control_id", c.get("id", "")), 0) > 0
    )
    evidence_score = round((controls_with_evidence / total_controls) * 100.0, 1)

    # 3. Control Effectiveness Score
    eff_points = 0.0
    for c in controls:
        eff = c.get("effectiveness", "Partially Effective")
        if eff == "Effective":
            eff_points += 1.0
        elif eff == "Partially Effective":
            eff_points += 0.5
        else:
            eff_points += 0.0
            
    effectiveness_score = round((eff_points / total_controls) * 100.0, 1)

    # 4. Finding Deduction
    critical_count = sum(1 for f in open_findings if f.get("severity") == "Critical")
    high_count = sum(1 for f in open_findings if f.get("severity") == "High")
    finding_deduction = min(30.0, (critical_count * 5.0) + (high_count * 2.0))

    # Overall weighted readiness
    raw_readiness = (
        (0.40 * implementation_score) +
        (0.35 * evidence_score) +
        (0.25 * effectiveness_score) -
        finding_deduction
    )
    overall_readiness = round(max(0.0, min(100.0, raw_readiness)), 1)

    return {
        "overall_readiness": overall_readiness,
        "implementation_score": implementation_score,
        "evidence_score": evidence_score,
        "effectiveness_score": effectiveness_score,
        "finding_deduction": finding_deduction
    }
