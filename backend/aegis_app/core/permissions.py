"""
Role-based access control matrix.

Roles are stored as a plain string on User.role (see models.py). This module is
the single source of truth for what each role is allowed to do, so that
authorization logic lives in one place instead of being re-invented (or
forgotten) per endpoint. "Super Admin" bypasses every check (enforced in
deps.require_roles) and is not listed in the tiers below.

Any role not present in any tier below is treated as read-only by default
(fails closed): an unrecognized role can view tenant-scoped data through the
GET endpoints but cannot perform any write action.
"""

from typing import List

ALL_ROLES: List[str] = [
    "Super Admin",
    "Tenant Admin",
    "AI Governance Lead",
    "Compliance Manager",
    "Risk Manager",
    "CISO/Security",
    "Security Manager",
    "Privacy/DPO",
    "Legal Reviewer",
    "AI Engineer",
    "Model Owner",
    "System Owner",
    "Control Owner",
    "Evidence Owner",
    "Auditor",
    "Consultant",
    "Executive Viewer",
    "Viewer",
]

# Roles allowed to self-select at signup (organization founder). Everything else
# (Super Admin, Auditor, Legal Reviewer, etc.) must be granted by an existing
# Tenant Admin / Super Admin after the tenant exists - never chosen by an
# unauthenticated caller during signup.
SELF_SIGNUP_ALLOWED_ROLES: List[str] = ["Tenant Admin"]

# Can create/update AI systems, controls, risks, vendors, policies - the
# day-to-day governance write surface.
GOVERNANCE_WRITE: List[str] = [
    "Tenant Admin", "AI Governance Lead", "Compliance Manager", "Risk Manager",
    "CISO/Security", "Security Manager", "AI Engineer", "Model Owner",
    "System Owner", "Control Owner", "Evidence Owner", "Privacy/DPO",
]

# Can upload evidence.
EVIDENCE_WRITE: List[str] = GOVERNANCE_WRITE

# Can review/approve/reject submitted evidence and applicability decisions.
# Deliberately excludes the roles that typically submit evidence, to preserve
# separation of duties between preparer and reviewer.
EVIDENCE_REVIEW: List[str] = [
    "Tenant Admin", "Compliance Manager", "Auditor", "Legal Reviewer", "CISO/Security",
]

# Can accept/reject/modify a "LEGAL REVIEW REQUIRED" applicability decision
# (spec #75) - the rule engine's own output can never do this.
LEGAL_REVIEW: List[str] = ["Tenant Admin", "Legal Reviewer", "Compliance Manager"]

# Can trigger an agent kill-switch or other emergency operational control.
OPERATIONAL_CONTROL: List[str] = [
    "Tenant Admin", "CISO/Security", "Security Manager", "AI Engineer", "System Owner",
]

# Can accept a risk (formal risk acceptance workflow, spec #38).
RISK_ACCEPTANCE_APPROVAL: List[str] = [
    "Tenant Admin", "Risk Manager", "CISO/Security", "Compliance Manager",
]

# Read-only roles - listed for documentation; they are the default posture for
# any role not appearing in a write tier above, so no special dependency is
# needed to enforce them, but router code can check `role in READ_ONLY` to
# render UI hints.
READ_ONLY: List[str] = ["Auditor", "Viewer", "Executive Viewer", "Consultant"]
