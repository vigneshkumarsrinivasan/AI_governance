# User Flow Validation Report

_2026-09-08. Fixes the "I can only see Acme and cannot add another company" blocker and implements the primary governance journey. Executed against the live app + `pytest`._

## The blocker, reproduced

Logged in as a seeded Acme user (`ciso@acmefinancial.com`): the header showed a static `[ Acme Financial Services ]` pill with **no dropdown, no "Add company", no way to switch or create**. A user was permanently bound to one tenant (`User.tenant_id` is a single value and there was no membership model, no `/organizations` API, no company UI). The only way to get a second company was to log out and sign up a brand-new account.

## What was implemented (backend + DB + API + frontend)

### Backend
| Change | Detail |
|---|---|
| `organization_memberships` table (migration `b2c3d4e5f6a7`) | user ↔ tenant with a per-tenant role; backfilled one row per existing user; signup + demo seed now create memberships |
| `POST /api/v1/organizations` | creates a **new tenant + org + profile + membership**, makes the caller **Tenant Admin**, switches them in, returns a fresh JWT. Client never supplies a tenant id. |
| `GET /api/v1/organizations/mine` | the companies this user may switch to (name, role, is_demo, is_active) |
| `POST /api/v1/organizations/switch` | verifies membership, updates `User.tenant_id/organization_id/role`, returns a fresh JWT. 403 for a non-member. |
| `GET /api/v1/organizations/current` | active company + portfolio stats (AI systems, high-risk, applicable frameworks, open findings, assessments) |
| `PATCH /api/v1/organizations/current` | edit active company (Tenant Admin only) |
| Assessment approval workflow (migration) | `approval_status` (NOT_SUBMITTED→SUBMITTED→APPROVED/REJECTED) + `submitted_by/at`, `approved_by/at`, `approval_notes`; `POST /assessments/{id}/approval` (`submit`/`approve`/`reject`), RBAC-gated, audited |
| Per-system workflow engine | `services/workflow.py`; `GET /ai-systems/{id}/workflow` + `GET /ai-systems/workflow/portfolio` — 9-step state (Inventory→…→Report) + the single **next action**, from real DB state |

### Frontend
| Change | Detail |
|---|---|
| **Company selector** in the global header (both advanced + simple shells) | `[ Company ▼ ]` with DEMO badge, lists your companies with roles, a check on the active one, **+ Add company** |
| **Create Company** 2-step modal | name, legal name, HQ, industry, size, operating countries → `POST /organizations` → auto-switches; validation ("Company name is required."), not a raw 500 |
| **Company switching** | swaps the token, `refreshCurrentUser()`, resets to Dashboard, full `loadPlatformData()` — no previous company's data lingers; the simple shell is re-keyed on `organization_id` so it fully remounts |
| **First-time / empty state** | active company with 0 AI systems → *"{Company} is ready. … Start by registering your first AI system."* + button, instead of a zero-filled dashboard |
| **"Needs attention"** dashboard section | groups the portfolio by next action ("3 AI systems need an applicability review → Assess applicability") — clickable |
| **AI Systems Inventory** | new **Governance Progress** (X/9 bar + open-findings badge) and **Next Action** columns; each row has a working next-action button that routes to the right step |
| **AI System detail** | 9-step workflow status bar + a **"Continue governance: {next step}"** button |
| **Assessments tab** (new) | start an assessment for a system+framework; list with readiness + approval status; detail modal with the **Submit for approval / Approve / Reject** buttons and per-requirement status |

## Step-by-step validation

| Step | Before | After | Test | Result |
|---|---|---|---|---|
| **Create Company** | No UI, no API; user stuck on Acme | Header "+ Add company" → 2-step modal → `POST /organizations` creates isolated tenant, caller = Tenant Admin, auto-switched | `test_company_journey_e2e::test_create_two_companies_switch_and_isolate`; browser: modal → "Nova … is ready" empty state | **PASS** |
| **Switch Company** | Not possible | Selector dropdown → switch → new token + full reload; dashboard/registry/findings/reports all follow | `::test_create_two_companies…` (switch A↔B, list per-company systems); browser: Nova → back to Acme, real data returns | **PASS** |
| **Multi-company user** | One tenant per user | Membership table; one user in 3 companies with different roles; selector lists only authorized ones | `test_company_journey_e2e` (First Co + Nova + HealthAI for one user) | **PASS** |
| **Tenant Isolation** | (already enforced) | Health context → Nova system id = 404; Nova list shows only Nova's; switch to a non-member org = 403 | `::test_create_two_companies…` + `full_e2e.py` isolation block (62/62) | **PASS** |
| **Add AI System** | Wizard existed; no next-step guidance | After add, workflow next action = "Assess applicability"; "Add your first AI system" from empty state | `::test_full_governance_journey_new_company` | **PASS** |
| **Assess Applicability** | Per-system engine existed, not tied to the journey | `intake-evaluate` persists a decision; workflow recognises it (by id or system name); next action advances to "Start assessment" | `::test_full_governance_journey_new_company` (asserts `next_action` transitions) | **PASS** |
| **Start Assessment** | Backend only, **no UI** | New Assessments tab; `POST /assessments` pre-populates the real requirement set; opens the detail modal | `::test_full_governance_journey_new_company`; browser tab renders | **PASS** |
| **Assign / test Controls** | `PUT /controls/{id}` existed | Marking a control Ineffective auto-raises a "Failed Control" finding; recovery auto-resolves it (prior pass) | `test_findings_remediation` + `::test_full_governance_journey_new_company` | **PASS** |
| **Add Evidence** | Existed; review states; auto-finding on reject (prior pass) | Unchanged; wired into the workflow (`next_action` = "add_evidence" when missing) | `test_findings_remediation`, `test_customer_acceptance_e2e` | **PASS** |
| **Fix Findings / Remediation** | `POST /findings` + `POST /remediations` (prior pass); completing tasks resolves the finding | Unchanged; workflow next action = "fix_findings" while open | `::test_full_governance_journey_new_company` | **PASS** |
| **Submit for Approval** | Did not exist | `POST /assessments/{id}/approval {decision:"submit"}` → SUBMITTED, status "Under Review", audited; UI button in the assessment modal | `::test_full_governance_journey_new_company`, `::test_approval_rbac` (409 on double-submit) | **PASS** |
| **Approve** | Did not exist | `{decision:"approve"}` → APPROVED + status "Completed" + `approved_by`; requires Tenant Admin / Governance Lead / Compliance / CISO / Legal; audited | `::test_full_governance_journey_new_company` (asserts APPROVED + audit `ASSESSMENT_APPROVE`) | **PASS** |
| **Generate Report** | `/reports/executive` existed | After approval the assessment modal shows "Generate report →"; report reflects the real company name + data | `::test_full_governance_journey_new_company` (`rep.organization.name == "Nova Journey Ltd"`) | **PASS** |
| **Next-action engine** | None | `services/workflow.py` + `/ai-systems/{id}/workflow` + portfolio endpoint; drives Dashboard "Needs attention", inventory column, detail "Continue governance" | `::test_full_governance_journey_new_company` (asserts each transition) | **PASS** |
| **Demo isolation** | Acme was the only tenant | Acme flagged `is_demo`; DEMO badge in selector; a created company is `is_demo=false`; switching never mixes data | browser + `test_company_journey_e2e` | **PASS** |
| **Error handling** | — | `POST /organizations` with blank name → 422 with a field message; modal shows "Company name is required.", not a 500 | manual + schema validation | **PASS** |

## Regression

- **Backend: 61/61 pass** (`pytest`) — 57 prior + 4 new (`test_company_journey_e2e.py`: create-two-companies-switch-isolate, full-journey, approval-rbac, signup-membership).
- **Live E2E script (`scripts/live_customer_e2e.py`): 62/62 pass.**
- **Frontend: `tsc --noEmit` clean.**
- No existing route, table, framework, control, permission, workflow or API removed. All prior features (SME onboarding, applicability engine, trust score, cross-linking, real regulatory content, findings/remediation, dashboard drill-through) intact.

## Not done this pass (documented, not blockers for the core journey)

Role-specific dashboards; My Tasks / task list; notifications & email; global search; breadcrumbs; org-level evidence reuse mapped down to systems; per-requirement assessment UI beyond the first 40; company Users / Legal Entities / Business Units management screens (business-unit API exists; no dedicated UI); "archive company"; mobile layout pass; control-testing as a distinct design/operating-effectiveness screen (effectiveness is captured on the control, which drives findings). The 7-step create-company wizard in the spec is implemented as a 2-step essentials modal (details + locations) — legal entities / business units / governance contacts / regulatory baseline are captured later via onboarding + org-structure APIs.
