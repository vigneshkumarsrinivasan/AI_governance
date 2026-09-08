# Company Usability Validation Report

_2026-09-08. Can a real company use this from day one without developer intervention? Evidence-based assessment._

| Area | Test performed | Result | Defect | Fix | Retest | Status |
|---|---|---|---|---|---|---|
| Signup / org creation | New customer via `/auth/signup` | Works, no DB edits | — | — | 62/62 E2E | ✅ PASS |
| SME onboarding | 5-step wizard → profile | Works, produces value (applicability + score + actions) | — | — | E2E + `test_sme_onboarding` | ✅ PASS |
| Onboarding produces a baseline | Company applicability + Trust Score + next-actions after onboarding | Real, derived from declared facts + framework logic | — | — | E2E | ✅ PASS |
| Empty-state UX | New tenant: 0 systems/models/agents/vendors | SME "what to do next" lists real first actions; advanced tabs render without crashing | Advanced empty tabs are sparse but not broken | Not changed (acceptable) | Browser | ⚠️ PASS (advanced empty-states thin) |
| AI portfolio (7 systems) | Register 7 distinct systems | All 7 register, attributes distinct | — | — | E2E | ✅ PASS |
| AI intake (dynamic) | Full questionnaire per system | Backend engine differentiates correctly | Intake form in UI is a fixed multi-step form, not answer-branching | Not changed | E2E (engine) | ⚠️ PASS (engine yes; UI form static) |
| Applicability output | Per-system + per-company | Differentiated, explainable, confidence + source + legal-review flags | — | — | E2E | ✅ PASS |
| Framework selection tiers | Recommended / applicable / best-practice / not-applicable / review | Company applicability returns all tiers; per-framework accept/override with audit | Override UI is minimal (advanced Frameworks tab) | Not changed | E2E | ⚠️ PASS |
| Framework browser | Open framework, hierarchy, requirement, source | `/regulatory/frameworks/*` works (tree, requirements, source, validation); **not surfaced in the UI** | Regulatory content has no frontend route | Not fixed (large; documented) | API only | ⚠️ PARTIAL |
| Requirement-level workflow | Applicability→control→owner→evidence→test→finding→remediate | Assessment uses real 419-req EU AI Act set; control test + evidence review now feed findings | Assessment has no dedicated UI page | Backend fixed (findings loop); UI page not built | E2E + tests | ⚠️ PARTIAL |
| Unified controls multi-framework | One control → many frameworks; partial stays partial | Crosswalk + evidence inheritance work; effectiveness feeds readiness | — | — | `test_workflows`, E2E | ✅ PASS |
| Control ownership | Assign control to role/owner | `owner` field on `PUT /controls`; no assignment notification | No notification system | Not fixed | E2E | ⚠️ PASS (no notify) |
| Evidence workflow | Upload, map, review, reject, expire | Upload + hash + signed download + review states work; rejection now raises a finding | Expiry job not scheduled (no worker) | Finding-on-reject fixed; expiry documented | `test_workflows`, E2E | ⚠️ PASS |
| Automated evidence | Connector-collected evidence | No connectors implemented | — | Documented, not built | — | ❌ NOT PRESENT |
| Evidence quality gate | Insufficient evidence must not read PASS | Insufficient → finding + no full satisfaction | — | Fixed this pass | `test_findings_remediation` | ✅ PASS |
| Control effectiveness lifecycle | Implemented but Ineffective → finding → fix → PASS | Auto-finding on Ineffective; auto-resolve on recovery; readiness reflects it | Was completely missing | **Fixed this pass** | `test_failed_control_autocreates_and_recovers_finding` | ✅ PASS |
| Real compliance logic | Status from applicability+control+evidence+effectiveness+findings | Scoring service combines all; not a checkbox | — | — | `test_backend`, E2E | ✅ PASS |
| Assessment workflow E2E | Create→scope→requirements→evidence→findings→approval→report | Create + populate (real reqs) + respond + recalc work via API | No approval/legal-review state machine; no UI | Not built | E2E | ⚠️ PARTIAL |
| Save/resume | Responses persist across logout | DB-persisted | — | — | E2E (implicit) | ✅ PASS |
| Multi-user collaboration | 10 named roles working together | RBAC enforced; **no user-invitation flow** | Tenant Admin cannot add users | Not fixed (P1 for full multi-user) | `test_api_security` (RBAC) | ⚠️ PARTIAL |
| Comments / review notes | Threaded comments | Not implemented; review notes exist on evidence/findings | — | Not built | — | ❌ NOT PRESENT |
| Risk register | Create, score, treat, accept | Works; acceptance needs justification + expiry + role | — | — | E2E, `test_workflows` | ✅ PASS |
| Risk acceptance RBAC | Wrong role blocked | `require_risk_acceptance` tier enforced; empty justification 400 | — | — | E2E | ✅ PASS |
| Findings | Create from many sources | `POST /findings` + auto (failed control, rejected evidence) | Was seed-only | **Fixed this pass** | `test_findings_remediation` | ✅ PASS |
| Remediation | Open→assigned→progress→done→close | `POST /remediations` + status flow + auto-resolve finding | Was missing | **Fixed this pass** | `test_findings_remediation` | ✅ PASS |
| Vendor workflow | Vendor lifecycle + portal | Registry + intelligence fields + impact graph work; **no vendor portal** | — | Not built | E2E | ⚠️ PARTIAL |
| Model / Agent registry | CRUD, versions, dependents, risk | Works; agent risk score + permission/dependency graphs | — | — | `test_registries`, `test_graph`, E2E | ✅ PASS |
| Shadow AI / runtime / telemetry / evaluations | Detection, policy-to-code, eval suites | Not implemented | — | Documented | — | ❌ NOT PRESENT |
| Regulatory change engine | Version A→B, impact, reassess | Subsystem has versions + source-change events + immutable published versions; impact/reassess-task flow not wired to customer assessments | — | Not fixed (large) | `test_regulatory_ingestion` | ⚠️ PARTIAL |
| Governance Copilot | Business questions, grounded, cited | Deterministic, tenant-grounded, cited; no hallucination; injection-safe | Was echoing raw query | Echo removed | E2E | ✅ PASS |
| Reporting | Executive + framework reports | Executive report (JSON) real + tenant-scoped; **1 report type, JSON only** | Hardcoded demo prose in UI | **Fixed** (now dynamic) | Browser + E2E | ⚠️ PASS (single report, no PDF/CSV) |
| Export | PDF / CSV / XLSX / ZIP | JSON export only | — | Not built | — | ⚠️ PARTIAL |
| Dashboard is real | Every KPI vs DB | Readiness, counts, scores all computed from tenant data | Report tab prose was fake | **Fixed** | E2E | ✅ PASS |
| Readiness explainable | Click % → breakdown | Scoring service returns implementation/evidence/effectiveness/finding components | No click-through drill UI | Not fixed (data is there) | `test_backend` | ⚠️ PASS |
| Error experience | No tracebacks to users | API returns structured JSON errors with codes; frontend shows messages | — | — | E2E (error paths) | ✅ PASS |
| Navigation | Click all sidebar items | No broken routes; all 15 advanced tabs + 4 simple tabs render | — | — | Browser | ✅ PASS |
| Demo vs production | Demo tenant isolated | Demo tenant flagged `is_demo`; real tenants never see Acme data (isolation tested) | Report UI prose leaked demo strings | **Fixed** | E2E isolation | ✅ PASS |
| Tenant isolation | Cross-tenant via API/URL/IDs/evidence/search/copilot | Every attempt → 404/empty | — | — | E2E + `test_api_security` + `test_graph` + `test_registries` | ✅ PASS |
| RBAC | Backend authorization per role | Enforced via dependency tiers; read-only default fail-closed | Coverage ~14/22 routers write-gated | Not expanded this pass | `test_api_security`, `test_workflows` | ⚠️ PASS (core) |
| Auth security | Login/logout/invalid/expired | JWT, bcrypt, 24h expiry, wrong-password 401 | No rate-limit, no lockout, no reset, no email-verify | Documented | `test_api_security` | ⚠️ PARTIAL |
| File security | Upload validation | MIME allowlist + size cap + hash; tenant-bound download | — | — | `test_workflows` | ✅ PASS |
| API security | IDOR / injection / auth | Tenant-scoped queries, parameterised ORM, RBAC | No dedicated SSRF/rate-limit tests this pass | Documented | `test_api_security` | ⚠️ PASS |
| AI security | Copilot injection / RAG leak | Rules-based copilot; no cross-tenant retrieval; injection returns nothing | — | Echo hardened | E2E | ✅ PASS |
| Backup / restore | Actual drill | Not performed | — | — | — | ❌ NOT DONE |
| Load / performance | 5,000 systems etc. | Not performed | — | — | — | ❌ NOT DONE |
| Background jobs | Collectors / notifications / schedulers | None present | — | — | — | ❌ NOT PRESENT |
| Observability | health / ready / metrics | `/health` (+ DB) only | No `/ready`, metrics, error tracking | Documented | curl | ⚠️ PARTIAL |
| Terminology consistency | AI System / Model / Agent / Vendor / Control / Evidence / Finding | Consistent in code + new UI | Some legacy labels ("AI Application") in older copy | Minor, not swept | Review | ⚠️ PASS |
