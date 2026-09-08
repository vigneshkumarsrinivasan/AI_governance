"""
Per-AI-system governance workflow / next-action engine (spec sections 27, 41, 64).

The primary journey is:
  1 Inventory -> 2 Applicability -> 3 Assessment -> 4 Controls -> 5 Evidence
  -> 6 Testing -> 7 Remediation -> 8 Approval -> 9 Report -> (Monitor)

`compute_workflow` returns the state of each step for one AI system plus the
single next action a user should take, derived entirely from database state.
"""

from typing import Any, Dict, List

STEP_KEYS = [
    "inventory", "applicability", "assessment", "controls",
    "evidence", "testing", "remediation", "approval", "report",
]

STEP_LABELS = {
    "inventory": "Inventory",
    "applicability": "Applicability",
    "assessment": "Assessment",
    "controls": "Controls",
    "evidence": "Evidence",
    "testing": "Testing",
    "remediation": "Remediation",
    "approval": "Approval",
    "report": "Report",
}

# action_key -> (label, helper text, target tab in the SPA)
ACTIONS = {
    "assess_applicability": ("Assess applicability",
        "Determine which regulations and frameworks may apply to this AI system.", "intake"),
    "start_assessment": ("Start assessment",
        "Evaluate the applicable requirements and identify the controls and evidence needed.", "assessments"),
    "continue_assessment": ("Continue assessment",
        "Answer the remaining requirements for this AI system.", "assessments"),
    "add_evidence": ("Add evidence",
        "Provide proof that the mapped controls are implemented.", "evidence"),
    "test_controls": ("Test controls",
        "Verify that the implemented controls operate effectively.", "controls"),
    "fix_findings": ("Fix findings",
        "Resolve the open findings before this assessment can be approved.", "risks"),
    "submit_for_approval": ("Submit for approval",
        "The assessment is complete - route it for owner, compliance and legal sign-off.", "assessments"),
    "await_approval": ("Awaiting approval",
        "Submitted - an approver needs to review and sign off.", "assessments"),
    "generate_report": ("Generate report",
        "The assessment is approved - produce the board-ready report.", "reports"),
    "monitor": ("Monitor",
        "Governance is complete for now. Watch for model, vendor, evidence-expiry and regulatory changes.", "dashboard"),
}


def compute_workflow(
    *,
    system: Dict[str, Any],
    applicability_decisions: List[Dict[str, Any]],
    assessments: List[Dict[str, Any]],
    tenant_controls: List[Dict[str, Any]],
    tenant_evidence_count: int,
    open_findings_for_system: List[Dict[str, Any]],
) -> Dict[str, Any]:
    has_applicability = len(applicability_decisions) > 0
    system_assessments = [a for a in assessments if a.get("system_id") == system["id"]]
    has_assessment = len(system_assessments) > 0

    # assessment answer progress (responses whose status is a real answer)
    answered = 0
    total = 0
    approval_status = "NOT_SUBMITTED"
    readiness = 0.0
    for a in system_assessments:
        total += a.get("response_total", 0)
        answered += a.get("response_answered", 0)
        approval_status = a.get("approval_status", approval_status)
        readiness = max(readiness, a.get("readiness_percentage", 0.0))
    assessment_progress = round(100 * answered / total, 0) if total else 0

    implemented = sum(1 for c in tenant_controls if c.get("status") in ("Implemented", "Tested"))
    tested = sum(1 for c in tenant_controls if c.get("effectiveness") in ("Effective", "Partially Effective", "Ineffective")
                 and c.get("status") in ("Implemented", "Tested"))
    open_findings = [f for f in open_findings_for_system if f.get("status") not in ("Resolved", "Accepted Risk")]

    steps = {
        "inventory": "done",
        "applicability": "done" if has_applicability else "todo",
        "assessment": "done" if (has_assessment and assessment_progress >= 100)
                      else "active" if has_assessment else "todo",
        "controls": "done" if implemented > 0 else ("active" if has_assessment else "todo"),
        "evidence": "done" if tenant_evidence_count > 0 else ("active" if implemented > 0 else "todo"),
        "testing": "done" if tested > 0 else ("active" if tenant_evidence_count > 0 else "todo"),
        "remediation": "active" if open_findings else ("done" if tested > 0 else "todo"),
        "approval": "done" if approval_status == "APPROVED"
                    else "active" if approval_status == "SUBMITTED" else "todo",
        "report": "done" if approval_status == "APPROVED" else "todo",
    }

    # single next action
    if not has_applicability:
        action = "assess_applicability"
    elif not has_assessment:
        action = "start_assessment"
    elif assessment_progress < 100:
        action = "continue_assessment" if tenant_evidence_count > 0 else "add_evidence"
    elif open_findings:
        action = "fix_findings"
    elif tenant_evidence_count == 0:
        action = "add_evidence"
    elif tested == 0:
        action = "test_controls"
    elif approval_status == "NOT_SUBMITTED" or approval_status == "REJECTED":
        action = "submit_for_approval"
    elif approval_status == "SUBMITTED":
        action = "await_approval"
    elif approval_status == "APPROVED":
        action = "generate_report"
    else:
        action = "monitor"

    label, helper, tab = ACTIONS[action]
    done_count = sum(1 for s in steps.values() if s == "done")

    return {
        "system_id": system["id"],
        "system_name": system.get("name"),
        "steps": [
            {"key": k, "label": STEP_LABELS[k], "state": steps[k]} for k in STEP_KEYS
        ],
        "completed_steps": done_count,
        "total_steps": len(STEP_KEYS),
        "readiness_percentage": readiness,
        "assessment_progress": assessment_progress,
        "open_findings": len(open_findings),
        "next_action": {
            "key": action, "label": label, "helper": helper, "target_tab": tab,
        },
    }
