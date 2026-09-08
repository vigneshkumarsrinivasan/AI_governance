# ENTERPRISE PRODUCTION READINESS REPORT

_Final enterprise validation — 2026-09-08. Method: direct inspection of the live database, live API (`:8010`), live UI (`:3001`), source files, and `pytest`. README claims, seed data, and prior status reports were treated as untrusted per instruction._

---

## FINAL RELEASE CLASSIFICATION: **INTERNAL_TESTING_READY**

Not `PILOT_READY`. The regulatory content — the core of the product — is ingested and structurally sound but **not verified, not mapped, not applied, and not exposed to users**. A large enterprise using this today would see ~10 placeholder requirements per framework, cannot run an assessment from the UI, and would get a "readiness %" derived from demo data.

---

## Gate results

| Area | Verdict | Evidence |
|---|---|---|
| **REGULATORY CONTENT** | ❌ **FAIL** | 16 frameworks ingested with 3,211 source-traceable requirements + full hierarchy + source text + licence checks — genuinely good. **But** 0 % human-verified (release gate = 100 %), all `published_status=DRAFT`, `is_current=0`. The system's own validation layer records 55 `FAIL` rows for `requirements_human_verified`, `control_mapping_coverage`, `applicability_rule_coverage`. 2 supplied frameworks (800-218A, 800-161) not imported at all. DPDP Act 2023 text never supplied. |
| **FRAMEWORK COMPLETENESS** | ⚠️ **PARTIAL** | Structure is faithful where ingested (EU AI Act: 113 articles, 13 chapters, 13 annexes, 180 recitals, 68 definitions — matches the Regulation). OWASP LLM/Agentic imported flat (no mitigations/scenarios). MITRE ATLAS duplicated (5.6.0 + 2026.08). |
| **APPLICABILITY** | ❌ **FAIL** | `regulatory_applicability_rules` = 0 rows. `applicability_decisions` = 0 rows. No scoping logic against the ingested requirement keys. Legacy `applicability_rules.json` (demo) is the only applicability content. Parts 11–18 cannot pass. |
| **CONTROL MAPPINGS** | ❌ **FAIL** | `regulatory_requirement_control_maps` = 0 rows. No requirement from any ingested framework maps to the Unified Control Library. Parts 28–29 fail. |
| **EVIDENCE** | ⚠️ **PARTIAL** | Evidence engine works (hash, tenant-bound signed download, MIME allowlist, review workflow, separation of duties — `test_workflows.py` passes). But evidence expectations are not linked to real requirements/controls (0 maps). Evidence lifecycle states from Part 30 partially implemented. |
| **ASSESSMENTS** | ❌ **FAIL** | No Assessments page in the UI (`frontend/src/app/page.tsx` has 15 nav items; Assessments is not one). Backend `create_assessment` now pre-populates from real `regulatory_requirements` (uncommitted change, regression test passing) but cannot be driven end-to-end by a user. Scoring is answer-weighting, not the applicability+control+evidence+effectiveness determination of Part 32. |
| **AI REGISTRY** | ✅ **PASS (core)** | `ai_systems`, `ai_models`, `ai_agents`, `vendors` tables + CRUD APIs + dependency graph; `test_registries.py` and `test_graph.py` pass, including tenant-isolation cases. |
| **MODEL GOVERNANCE** | ⚠️ **PARTIAL** | Model registry + links + dependents work. `model_version_history` = 0 rows; version/change workflow (Part 45) unproven. |
| **AGENT GOVERNANCE** | ⚠️ **PARTIAL** | Agent registry, permission graph, dependency graph, risk score exist and are tested. OWASP-Agentic / MITRE-ATLAS mapping (Part 37), runtime policy, human-approval gating **not wired** (0 mapping rows; no runtime governance module). |
| **VENDOR GOVERNANCE** | ⚠️ **PARTIAL** | Vendor registry + impact endpoint + regulatory-exposure graph work. **No vendor portal** (Part 38) — no invitation/questionnaire/upload/review workflow, no UI. |
| **INTEGRATIONS** | ❌ **CONFIG_REQUIRED / NOT IMPLEMENTED** | No GitHub/Jira/AWS/Azure/Databricks connector code. `AI_PROVIDER` defaults to `rules` (no external LLM). Automated evidence collection (Part 40), Shadow AI discovery (Part 41), telemetry ingestion (Part 42) — no implementing modules found. |
| **SHADOW AI** | ❌ **FAIL** | Not implemented. No discovery sources, no `shadow_ai_*` tables, no UI. |
| **RUNTIME GOVERNANCE** | ❌ **FAIL** | Not implemented. No policy-to-code engine (Part 43), no ALLOW/WARN/BLOCK enforcement (Part 44). Nav item "AI Security & Agents" is a read-only view + kill-switch endpoint. |
| **EVALUATIONS / RED-TEAM** | ❌ **FAIL** | No evaluation engine, no configured test suites (prompt injection, PII leakage, etc.), no `evaluations` table. Part 46 cannot pass. |
| **COPILOT** | ⚠️ **PARTIAL** | Deterministic rules-based Copilot grounded in live tenant data + crosswalk — it does not hallucinate requirements (good design). **But** it cites the demo `data/frameworks/*.json` "17 Standards", not the 3,211 ingested requirements. Answers to "show source" resolve to demo content. |
| **REPORTING** | ⚠️ **PARTIAL** | `/reports/executive` produces JSON from `crosswalk_service` (demo data). No EU AI Act / NIST AI RMF / GenAI Security / GDPR / CRA / NIS2 / DORA / DPDP / ATLAS / AI Verify report types (Part 49). No PDF/CSV/XLSX. No auditor evidence pack. No historical reproducibility mechanism (Part 50). |
| **MULTI-TENANCY** | ⚠️ **PASS (tested surface) / UNVERIFIED (full)** | Tenant-isolation regression tests exist and pass in `test_graph.py`, `test_registries.py`, `test_api_security.py`, `test_backend.py`. A full P0 cross-tenant sweep across every endpoint, export, evidence URL, Copilot, and report (Part 54) was **not** executed this run. No leak found in what was tested. |
| **RBAC** | ⚠️ **PARTIAL** | Server-side role checks present in 12/20 API routers. `test_workflows.py` confirms reviewer≠uploader and risk-acceptance role gating. No user-invitation flow, no MFA/SSO, no lockout/reset. Full 16-role matrix (Part 55) not exercised. |
| **SECURITY** | ⚠️ **PARTIAL** | Security headers now emitted (CSP `default-src 'none'`, X-Frame-Options DENY, nosniff, Referrer-Policy) via uncommitted `main.py` middleware — verified live. `test_api_security.py` (7 tests) covers auth, IDOR/tenant, injection basics — passes. No independent pen-test. Full Part 56/57 fuzzing not run. |
| **BACKUP / RESTORE** | ❌ **FAIL** | No backup automation, no tested restore. SQLite dev DB. Part 61 fails by definition. |
| **OBSERVABILITY** | ⚠️ **PARTIAL** | `/health` with DB check works. No `/ready`, no worker/queue/Redis/storage health, no metrics endpoint, no error-tracking hook. Logging is uvicorn default + some structured logs. |
| **PERFORMANCE** | ❌ **NOT DONE** | No load test. Target scale (10k systems / 1M mappings) never simulated. Graph endpoints not profiled for N+1. |
| **DEPLOYMENT** | ⚠️ **PARTIAL** | `docker-compose.yml` (Postgres + backend + Next.js) exists; prod-config guard (`validate_production_settings`) refuses default secret / demo seed / SQLite in `ENVIRONMENT=production`. Alembic migrations present (`alembic_version` = 1 head). No TLS, no secrets manager, no HA, no CD. Startup still calls `Base.metadata.create_all` (Part 60 — acceptable only if migrations own the schema in prod). |

---

## P0 release gates (MUST pass)

| Gate | Status |
|---|---|
| Tenant isolation | ⚠️ PASS on tested surface; full sweep not done |
| Authentication | ✅ PASS (JWT, bcrypt, 24h expiry, `auto_error` login) |
| RBAC | ⚠️ PARTIAL (enforced where present; not comprehensive) |
| Database migrations | ✅ PASS (Alembic, single head) — ⚠️ `create_all` still runs at startup |
| Regulatory source integrity | ✅ PASS (SHA-256 artifacts, licence gate, count reconciliation) |
| Framework completeness | ❌ FAIL (2 not imported; 16 DRAFT/unverified) |
| Source traceability | ⚠️ PARTIAL (requirement→article→source text present; requirement→control→evidence→report chain broken at control mapping = 0) |
| Evidence security | ✅ PASS (tenant-bound signed URLs, TTL, MIME allowlist, hash) |
| Audit logging | ⚠️ PARTIAL (`audit_events` table + some writes; not all Part 66 events covered — only 3 rows after full demo seed) |
| No critical secret leak | ✅ PASS (no secrets in code or git history; dev SECRET_KEY gated in prod) |
| No critical vulnerability | ⚠️ UNKNOWN (no SAST / dependency scan / container scan run this pass) |
| Backup / restore | ❌ FAIL |
| Core E2E workflow | ❌ FAIL (no assessment UI; regulatory content not in user path) |

**P0 result: FAIL** (framework completeness, backup/restore, core E2E, + partials).

## P1 gates (before large-enterprise GA)

| Gate | Status |
|---|---|
| Applicability validation | ❌ FAIL (0 rules) |
| Control mapping quality | ❌ FAIL (0 mappings) |
| Assessment integrity | ❌ FAIL (no UI, demo scoring) |
| Report reproducibility | ❌ FAIL (no versioned historical reports) |
| Vendor security | ❌ FAIL (no vendor portal) |
| Runtime telemetry security | ❌ FAIL (no telemetry) |
| Copilot grounding | ⚠️ PARTIAL (grounded, but on demo content) |
| Regulatory versioning | ⚠️ PARTIAL (`regulatory_framework_versions` + `regulatory_source_change_events` exist, 2 change events; diff/impact/reassessment not exercised) |
| Performance baseline | ❌ NOT DONE |
| Observability | ⚠️ PARTIAL |

**P1 result: FAIL.**

---

## What is genuinely solid (do not discount)

- The **regulatory ingestion pipeline** is real engineering: manifest-driven, per-source SHA-256 artifacts, licence classification with a redistribution gate, multi-parser (EU docx / NIST PDF / OSCAL / MITRE YAML / OWASP), deep hierarchy extraction, source-text storage bounded by licence, count reconciliation, a 4-layer validation harness (SOURCE / SEMANTIC / STRUCTURAL / COMPLIANCE), and immutable published versions.
- **Tenant isolation** on the tested surface, **evidence handling**, **registry + graph** features, **auth**, and the **deterministic (non-hallucinating) Copilot design**.
- **41/41 backend tests pass.**

## The core problem in one sentence

The ingestion subsystem produced a verified, source-traceable regulatory library — and then nothing downstream (UI, assessments, control mappings, applicability rules, reports, Copilot) was connected to it, so end users still operate entirely on ~170 hand-authored demo requirements.
