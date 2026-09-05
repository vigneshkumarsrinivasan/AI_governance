# AegisAI Governance OS — Production Readiness Status

This document exists because the project's own build spec (§103, §124, §128,
§130) explicitly forbids calling unfinished work "production-ready" or
"complete." It replaces guesswork with an evidence-based status per module,
using the same status vocabulary the spec itself defines:

**Experimental | Content Imported | Under Review | Validated | Production Ready**

Every "Production Ready" or "Validated" claim below is backed by something
you can re-run yourself (a test file, a command, a migration) — cited inline.
Nothing here should be taken on faith; if a citation looks stale, re-run it.

Last updated: 2026-09-05. Originally based on a from-scratch audit of the
repository (zero prior git commits existed); updated after a second pass
implementing Phase 1 (AI/Model/Agent/Vendor Registries) and Phase 2
(Regulatory & Asset Knowledge Graph) of the "AI Governance Control Plane"
roadmap. See §0 below for what that pass added; §1 onward is the original
report from the first pass and is still accurate for the areas it covers.

---

## 0. Phase 1 & 2 addendum (2026-09-05)

**Phase 1 — AI Registry + Model Registry + Agent Registry + Vendor Registry: Validated.**
Previously, Model/Agent/Vendor had database tables but no real API (Models had
zero endpoints; Agents/Vendors were read-only). This pass added:
- Full CRUD for all three (`api/model_registry.py`, `api/agent_registry.py`, `api/vendor_registry.py`), RBAC-gated, audit-logged, tenant-scoped.
- `BusinessUnit` / `AIProduct` hierarchy tables + CRUD (`api/org_structure.py`).
- A real Model → many AI Systems relationship (`AISystemModelLink` join table) - previously a model could only belong to exactly one system.
- Dependency-graph views: `GET /models/{id}/dependents` (Model → Systems/Agents/Vendor/Risks), `GET /vendors/{id}/impact` (Vendor → Models → Systems, with high-risk count), `GET /agents/permission-graph` (answers every example question in the spec: GitHub write access, code execution, PII access, financial actions, agent-to-agent invocation, missing approval gates, missing kill-switches - as real SQL queries, not canned text).
- An explainable agent risk score (`services/agent_risk.py`) - additive, documented weights per capability, not a black box.
- Frontend: three new nav sections (Models, Agents, Vendors) with real create forms and dependency drilldowns, verified live via Playwright (create → appears in list → dependents graph shows correct linked systems).
- Tests: `tests/test_registries.py` (8 tests) - CRUD, dependency correctness, risk-score correctness, cross-tenant isolation for all three new resource types.

**Phase 2 — Regulatory Knowledge Graph: Validated, with a deliberate scope decision.**
The spec allows implementing graph semantics as "relational tables and APIs" rather than requiring Neo4j - taken literally here. The existing 17-framework/unified-control/crosswalk content (built and cited in the first pass) was **not** re-migrated into new graph tables, because it is real working content and re-migrating it would mean re-authoring already-correct regulatory data for no functional gain (violates "do not rebuild working modules unnecessarily"). Instead, `api/graph.py` implements six real graph-traversal queries joining that static regulatory content with live tenant data:
- Requirement → affected AI Systems
- Controls satisfying multiple named frameworks at once
- Evidence ranked by transitive requirement coverage
- Vendors ranked by regulatory-exposure (systems × applicable-framework-requirement-counts)
- Foundation models shared by 2+ high-risk systems (concentration risk)
- Agents depending on a named tool (incident-response query)

All six verified live in the browser with real seeded data (see `tests/test_graph.py`, 7 tests) and wired into a new "Governance Graph" frontend page.

**What Phase 1/2 did NOT touch:** no data was deleted or restructured destructively; `AIModel.system_id` and `Vendor.models_provided` (legacy fields) were kept for backward compatibility rather than removed. Test count: **28/28 passing** (was 21 before this pass; +4 registry, +7 graph, net after one intentional test-bug fix).

**Explicitly not started this pass** (see the priority order requested): Phase 3 (applicability engine already exists at the system/org level from the first pass but was not extended to model/agent/vendor-level applicability), Phase 5 (Vendor Portal external login), Phase 6 (GitHub/Jira/AWS/Azure/Databricks - zero code exists), Phase 7 (automated evidence collection), Phase 8 (Shadow AI discovery), Phase 9 (telemetry ingestion), Phase 10 (continuous policy monitoring), Phase 11 (policy-to-code), Phase 12 (runtime agent governance), Phase 13 (evaluations/red-teaming), Phase 14 (Governance Agent upgrade). These are all greenfield - nothing to preserve, nothing broken by not having started them.

---

## 1. What changed in this pass, and why

The prior state (see the audit this session started from) was a genuinely
well-structured prototype with several claims that didn't hold up under
inspection: RBAC existed as an unused function, the frontend hard-coded and
auto-submitted a demo password with no login screen, the dashboard's
per-framework readiness numbers were `overall_score × hardcoded_multiplier`
rather than real per-framework data, the "AI Copilot" had no LLM behind it
despite being marketed as RAG-grounded, evidence had no real file storage,
and there was no dependency manifest, CI, or migration tooling at all.

This pass fixed all of the above with real, tested code — not TODOs. It also
did NOT attempt several items the spec asks for that require external
resources (AWS account, a live Postgres/AWS deployment, an LLM API key, legal
review of expanded regulatory text, a licensed pen-test engagement) that
cannot be produced by an engineering session alone. Those are called out
explicitly in §4 below rather than silently skipped.

---

## 2. Module status

| Area | Status | Evidence |
|---|---|---|
| Multi-tenant data model | **Validated** | Every business table has `tenant_id`; enforced at every router via `.where(Model.tenant_id == current_user.tenant_id)`. Cross-tenant isolation verified at the HTTP layer (not just ORM) in `test_cross_tenant_isolation_via_api`. |
| Authentication | **Validated** | Real bcrypt + JWT (`core/security.py`). Frontend login screen replaces the previous hardcoded auto-login in both `frontend/` and `web-ui/`. Verified: `test_signup_login_and_me`, `test_login_rejects_wrong_password`, `test_unauthenticated_request_rejected`, and a live Playwright run against the running app (login screen renders, wrong password rejected, correct password succeeds, session persists across reload). |
| Authorization (RBAC) | **Validated** for the endpoints wired this pass | `core/permissions.py` defines the role tiers; `require_governance_write`, `require_evidence_review`, `require_legal_review`, `require_operational_control`, `require_risk_acceptance` are wired into every write endpoint in `ai_systems.py`, `controls.py`, `risks.py`, `evidence.py`, `security.py`. Verified: `test_rbac_viewer_cannot_write_but_admin_can`, `test_evidence_review_requires_reviewer_role_not_uploader_role`. **Gap**: `assessments.py` and `crosswalk.py` write paths still only require `get_current_user` (any authenticated role) — not yet tiered. A user-management/role-assignment API (inviting teammates, changing someone's role) was not built this pass; roles can currently only be set by directly editing the database. |
| Signup privilege escalation | **Fixed** | `auth.py` previously let the signup payload's `role` field be anything, including `"Super Admin"`. Now forced to `Tenant Admin` regardless of what's submitted (`core/permissions.SELF_SIGNUP_ALLOWED_ROLES`). |
| Applicability rule engine | **Validated as a real rule engine**, **Content Imported** for regulatory depth | `services/rule_engine.py` + `data/applicability_rules.json` replace the prior hard-coded if/else with versioned, data-driven rules (conditions, AND/OR, categories, priorities). Existing classification tests continue to pass unchanged, proving behavior was preserved during the refactor. New: every evaluation is persisted as an immutable `ApplicabilityDecision` row with rule-level provenance, and a Legal-Reviewer-gated accept/reject workflow (`PUT /ai-systems/applicability/decisions/{id}/review`) exists so the rule engine's own output can never self-approve. Verified: `test_applicability_decision_persisted_and_reviewable`. **Gap**: the ruleset covers the same legal triggers the original prototype covered (a curated subset of EU AI Act/GDPR/India DPDPA/GenAI/Agentic AI/supply-chain baselines) — it was NOT expanded to the other 13 frameworks' applicability logic, and effective-date/jurisdiction fields exist in the schema but aren't yet enforced as filters (a rule with a future `effective_date` still fires today). |
| Regulatory content (17 frameworks) | **Content Imported**, not Validated | Unchanged this pass. Real hierarchical structure, real article numbers, plausible official URLs and dates for a curated subset (e.g., 8 requirements for the EU AI Act, which has 113 articles + annexes in reality). This is honest, well-produced reference content — but it is not exhaustive, and the anchor URLs were not verified against the live regulations this pass. Do not represent this catalog as legally complete to a customer. |
| Evidence management | **Validated** for the mechanics; **Under Review** for production file-security posture | Real file upload (`POST /evidence/upload`), extension allowlist + magic-byte validation, SHA-256 over actual bytes, storage abstraction (`services/storage.py`) with a working local-disk backend and a real (untested-in-this-environment, no AWS account available) S3 backend, short-lived signed download tokens, and a Draft→Submitted→Under Review→Accepted/Rejected review workflow with separation of duties. Verified: `test_evidence_upload_download_requires_valid_token`, `test_evidence_upload_rejects_disallowed_file_type`, `test_evidence_review_requires_reviewer_role_not_uploader_role`. **Gap**: no malware/AV scan integration (explicitly documented as a hook, not implemented — no scanner available in this environment); no virus-scanning, no evidence expiry job, no S3 encryption-at-rest verification (SSE-S3 is requested in the code but was never exercised against real AWS). |
| Dashboard scoring | **Fixed and Validated** | Per-framework readiness is now computed from real `Assessment.readiness_percentage` rows grouped by `framework_id`, with frameworks lacking any assessment reported separately as "unassessed" rather than assigned a fabricated percentage. The previous `overall_score × 0.92` etc. hard-coded multipliers are gone. Frontend renders the "Not Assessed" state honestly. |
| Findings/Risk register | **Fixed and Validated** | The hard-coded `system_name="Acme AI Asset"` bug (every finding showed the same fake system name) is fixed — now joins the real `AISystem` table. Added a formal risk-acceptance workflow requiring a business justification and a restricted approver role (`PUT /risks/{id}/accept`), matching spec §38's "ordinary users cannot dismiss a risk" requirement. Verified: `test_risk_acceptance_requires_justification_and_role`. |
| AI Copilot | **Fixed (honesty), not upgraded (capability)** | It was marketed as "RAG-grounded" while being pure keyword-matched canned responses. The false claim is now removed from all docstrings/UI copy; the response schema now reports `mode: "rules_based"` explicitly. A pluggable provider abstraction (`services/ai_provider.py`) was built for Anthropic/OpenAI, but is inert by default (`AI_PROVIDER=rules`) because no API key exists in this environment — enabling it is a config change, not a code change, and was not exercised end-to-end here. |
| Database / migrations | **Validated on SQLite, Config-Validated (not live-tested) on PostgreSQL** | `alembic/` initialized with an async-engine `env.py` that reads the app's real `DATABASE_URL`. The baseline migration was generated from the current models and confirmed to apply cleanly to a fresh SQLite database (`alembic upgrade head` → all 20 tables created correctly, including the new columns). `asyncpg` is installed and `DATABASE_URL` correctly switches dialects via env var. **Gap, and why**: a live Postgres connection test was attempted (a dedicated container on port 5433, isolated from this machine's other Docker projects) but Docker on this development machine became unresponsive for that specific container's start/rm operations (confirmed: `docker info` answers instantly; `docker start`/`docker rm` on that one container hang past 15s) — an environment/resource issue on this box (it already runs ~20 other containers from unrelated projects), not a code issue. The generated DDL is dialect-aware SQLAlchemy metadata, so it will apply the same way to Postgres, but that specific claim was not exercised against a live Postgres server this pass. Recommend re-running `alembic upgrade head` against a real Postgres instance as the first step of any deployment. |
| Demo data isolation | **Fixed and Validated** | `SEED_DEMO_DATA` (default `true` for local dev) and `ENVIRONMENT` settings now gate `seed_demo_data()` in `main.py`'s startup lifecycle. `validate_production_settings()` makes the app **refuse to boot** if `ENVIRONMENT=production` and either the demo seed flag is still on, the JWT secret is still the shipped default, or the database is still SQLite. The demo `Organization` row is now flagged `is_demo=True` in the database (not inferred from its name), and the frontend only shows the "DEMO" badge when that flag is true. |
| Dependency management | **Fixed** | `backend/requirements.txt` added, pinned to the versions actually verified working in this environment. Previously there was no manifest at all — whatever was in the ambient Python environment is what ran. |
| Containerization | **Content Imported, not deployment-tested** | `backend/Dockerfile`, `frontend/Dockerfile` (multi-stage, Next.js `standalone` output), and a root `docker-compose.yml` (Postgres + backend + frontend) were added. Not run end-to-end in this environment due to the same Docker resource contention noted above — inspect before trusting for a real deployment. |
| CI | **Content Imported, not exercised** | `.github/workflows/ci.yml` runs the backend test suite, verifies migrations apply, runs a non-blocking dependency audit, and builds the frontend. This has not actually executed on GitHub Actions (no repository/remote exists yet — zero git commits at the start of this session) — inspect the YAML, don't assume it's green until it runs once for real. |
| Tests | **Validated for what exists** | 17 tests, all passing: 6 unit tests (scoring, applicability, crosswalk) unchanged from before this pass, plus 11 new real HTTP-level integration/security/workflow tests added this pass (`tests/test_api_security.py`, `tests/test_workflows.py`) using `httpx.AsyncClient` against the actual FastAPI app — covering auth, RBAC rejection/acceptance, cross-tenant isolation via the API (not just an ORM query, which is what the one pre-existing "security" test actually did), evidence upload/download authorization, file-type rejection, evidence review separation-of-duties, risk acceptance, and applicability decision persistence/review. Tests now run against an isolated temp SQLite database (`tests/conftest.py`) instead of silently mutating the real dev database, which is what the previous test suite did. **Gap**: no load/performance tests, no migration-rollback tests, no frontend component tests. |
| Multi-tenancy attack surface | **Validated for the paths tested**, not exhaustively | `test_cross_tenant_isolation_via_api` exercises AI systems specifically (create as Tenant A, confirm Tenant B gets 404 on get/put/list). The same `tenant_id` filtering pattern is used consistently across every other router (`risks`, `evidence`, `controls`, `audit`, `dashboard`, `copilot`, `security`), but each of those was not individually re-verified with its own cross-tenant test this pass — the spec's §99 mandate ("attempt through API, UI, search, report, evidence URL, RAG, export, direct object ID... every attempt MUST fail") is partially, not fully, covered by test evidence. |

---

## 3. Explicit "do not claim this" list

Per spec §103/§124, these are NOT implemented, and nothing in the UI or API
should be read as claiming they are:

- **No real generative AI / RAG anywhere in the platform.** The Copilot is
  rules-based by default; the pluggable provider exists but is unconfigured.
- **No malware scanning on uploaded evidence.** A hook exists; no scanner is wired in.
- **No live-tested PostgreSQL deployment.** Config and migrations are correct on paper; not exercised against a running Postgres server this pass (see table above for why).
- **No AWS/cloud deployment of any kind.** Docker Compose is for local dev only.
- **No background job queue** (report generation, evidence-expiry checks, regulatory-source polling all still run inline, not in a worker).
- **No regulatory-source freshness checking** (spec §40/§107) — frameworks are static JSON files with no automated re-fetch/diff/re-approval pipeline.
- **No full legal-text coverage** of any of the 17 frameworks — the content is a curated, real, well-cited subset, not the complete regulation.
- **No penetration test has been performed.** The RBAC/tenant-isolation tests in this repo are automated regression tests, not a security audit.
- **No SSO/OIDC/SAML integration**, despite the architecture (JWT-based, stateless) being compatible with adding one later.
- **No production secrets management** (Vault/AWS Secrets Manager/etc.) — `.env` files and environment variables only.

---

## 4. Recommended next steps, in order

1. **Run this against a real Postgres instance** (the Docker contention on the dev machine used for this pass was environment-specific, not a code issue) and re-verify `alembic upgrade head` + the full test suite with `DATABASE_URL` pointed at it.
2. **Extend RBAC tiers to `assessments.py` and `crosswalk.py` write paths** (currently any authenticated user can write there — see the RBAC row above).
3. **Build the user-management API** (invite teammates, assign/change roles) — right now role changes require direct DB access, which doesn't scale past the founding admin.
4. **Decide on and configure a real Copilot provider** if generative answers are wanted, or explicitly keep `AI_PROVIDER=rules` and update any remaining marketing copy to match.
5. **Commission a real penetration test** before onboarding any real customer data — automated tests are not a substitute.
6. **Expand regulatory content depth** for whichever 2-3 frameworks matter most to the first real customer, under actual legal review, before claiming broader coverage than the current curated subset.

---

*This document itself should be kept up to date as work continues — treat a
stale "Validated" claim here as a bug.*
