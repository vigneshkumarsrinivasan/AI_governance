# Platform Validation Report

_Run date: 2026-09-06. Evidence is re-runnable — commands cited inline._

This is an **evidence-based** validation: the application was built, migrated,
started, and driven through real workflows over HTTP. Nothing here is taken from
comments, READMEs, or UI appearance.

Companion reports: [`SECURITY_VALIDATION_REPORT.md`](SECURITY_VALIDATION_REPORT.md),
[`E2E_TEST_REPORT.md`](E2E_TEST_REPORT.md),
[`PRODUCTION_READINESS_REPORT.md`](PRODUCTION_READINESS_REPORT.md),
[`COMPLIANCE_PLATFORM_VALIDATION_REPORT.md`](COMPLIANCE_PLATFORM_VALIDATION_REPORT.md)
(regulatory content detail).

---

## 1. Method

| Step | Command | Result |
|---|---|---|
| Backend deps | `pip install -r backend/requirements.txt` | ok |
| Fresh migration | `DATABASE_URL=sqlite+aiosqlite:///fresh.db alembic upgrade head` | 2 migrations apply clean |
| Schema drift | `alembic revision --autogenerate` | **0** table/column diffs (models == migrations) |
| Backend unit/integration | `python -m pytest -q` | **41 passed**, 0 failed |
| web-ui typecheck+build | `cd web-ui && npx tsc -b && npm run build` | clean, 319 kB bundle |
| frontend typecheck | `cd frontend && npx tsc --noEmit` | clean |
| Backend boot | `uvicorn aegis_app.main:app` | `/health` → `{"status":"healthy","database":"connected"}` |
| Live E2E driver | `scratchpad/validate.py` (62 assertions over HTTP) | **62 passed**, 0 failed |
| Frontend nav | Playwright, 12 sidebar tabs | 0 crashes, 0 console errors |

---

## 2. Fixes applied during this validation

| # | Severity | Issue | Fix | Regression test |
|---|---|---|---|---|
| 1 | **P1** | Assessments generated from the legacy hand-authored JSON (~2–10 questions/framework), not the ingested regulatory content | `api/assessments.py` now loads the full source-traceable requirement set from `regulatory_requirements` for any ingested framework (EU AI Act → 419, NIST 800-53 → 1,014, GDPR → 238, …); legacy JSON is the fallback only | `test_assessment_uses_ingested_regulatory_requirements` |
| 2 | P2 | No security response headers | Added OWASP baseline headers middleware (`X-Content-Type-Options`, `X-Frame-Options: DENY`, `CSP: default-src 'none'`, `Referrer-Policy`, HSTS in prod) in `main.py` | verified via `curl -D-` |
| 3 | P2 | `ingest --all --inventory` / `--all --report` short-circuited after the first flag | Rewrote CLI flag composition in `regulatory/ingest.py` | — |
| 4 | P2 | Frameworks UI tab showed legacy counts (DORA "2 requirements") | web-ui `Authoritative Frameworks` tab wired to `/api/v1/regulatory/*` with detail + requirement + source-citation drill-down | — |

No test was skipped, disabled, or weakened to pass.

---

## 3. Feature matrix

Status: **PASS** (works, verified) · **PASS-LIM** (works with a stated limitation) ·
**NOT_IMPL** (not in the codebase) · **NOT_CONF** (present, needs external credentials).

| Feature | Backend | Frontend | DB | Security | E2E | Status |
|---|---|---|---|---|---|---|
| Auth (signup/login/JWT/me) | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** |
| RBAC (server-side role tiers) | ✓ | ✓ (hint only) | — | ✓ | ✓ | **PASS** — viewer write → 403 (`test_rbac_viewer_cannot_write_but_admin_can`) |
| Multi-tenant isolation | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** — 0 leaks over 26 cross-tenant attempts |
| AI System Registry | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** — CRUD + lifecycle |
| Model Registry (+ versions, M:N) | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** |
| Agent Registry (+ permission graph) | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** |
| Vendor Registry (+ impact graph) | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** |
| Org structure (BU / product) | ✓ | partial | ✓ | ✓ | ✓ | **PASS-LIM** — API complete, limited UI |
| Applicability / classification engine | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** — versioned rule engine, results differ per system (see §4) |
| Regulatory ingestion (17 frameworks) | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** — 16/17 ingested & VALIDATED, 1 blocked (800-161). Detail: companion report |
| Regulatory knowledge browser + search + citations | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** |
| Unified Control Library + crosswalk | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS-LIM** — 50 controls, legacy hand-authored mappings; `regulatory_requirement_control_maps` table exists but **0 mappings** to the ingested requirements |
| Assessments | ✓ | view-only | ✓ | ✓ | ✓ | **PASS-LIM** — now source-traceable (fix #1); no create-UI in frontend; scoring is `Yes/Partial/N-A` weighting, not the full control+evidence+effectiveness determination |
| Evidence management (upload/hash/review/download-token) | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** — SHA-256, tenant-bound signed download, MIME allowlist (`test_evidence_*`) |
| Evidence → multi-control reuse | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** (legacy control library) |
| Risk register (inherent/residual/accept) | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** — acceptance gated to `RISK_ACCEPTANCE_APPROVAL` roles |
| Findings + Remediation | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** |
| Control testing (design/operating effectiveness → finding) | partial | partial | ✓ | ✓ | partial | **PASS-LIM** — status fields + finding creation exist; no dedicated "run test → auto-finding on FAIL" endpoint |
| Audit log | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** — write actions logged (`AuditEvent`); append-only by convention, not DB-enforced immutability |
| Dashboard KPIs | ✓ | ✓ | ✓ | — | ✓ | **PASS** — reconciled against DB (total/high-risk/genai counts exact; readiness computed, not hardcoded) |
| Executive report | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS-LIM** — JSON only; no PDF/CSV/XLSX export |
| Governance Copilot | ✓ | ✓ | ✓ | ✓ | partial | **PASS-LIM** — `AI_PROVIDER=rules` default (deterministic, no external LLM), grounded in tenant data; tenant-scoped (no leak observed); RAG over the **legacy** framework JSON, not `regulatory_*` |
| AI Verify adapter | ✓ (scaffold) | — | — | ✓ | partial | **PASS-LIM** — capability registry + result-import/normalize API; **does not execute** the AI Verify engine |
| MITRE ATLAS threat modelling | data ✓ | — | ✓ | — | partial | **PASS-LIM** — ATLAS v2026.08 ingested (16 tactics/114 techniques/83 sub/39 mitigations/72 case studies); no "generate threat model for system X" endpoint yet |
| Security overview / kill-switch | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** — kill-switch gated to `OPERATIONAL_CONTROL` |
| GitHub / Jira / AWS / Azure / Databricks integration | — | — | — | — | — | **NOT_IMPL** — no connector modules exist |
| Automated evidence collection | — | — | — | — | — | **NOT_IMPL** |
| Shadow AI discovery | — | — | — | — | — | **NOT_IMPL** |
| Agent telemetry ingestion / trace hierarchy | — | — | — | — | — | **NOT_IMPL** |
| Policy-to-code / runtime governance enforcement | — | — | — | — | — | **NOT_IMPL** — `agent_risk.py` scores permission breadth; no policy DSL or runtime interceptor |
| Red-team / evaluation engine | — | — | — | — | — | **NOT_IMPL** |
| Vendor portal / Auditor portal | — | — | — | — | — | **NOT_IMPL** — no external-party auth or scoped views |
| User management / invitation API | — | — | — | — | — | **NOT_IMPL** — only the tenant founder exists; additional users need direct DB insert |
| Regulatory change management (version diff → reassess) | partial | — | ✓ | — | partial | **PASS-LIM** — `FrameworkVersion` immutable-on-publish + `SourceChangeEvent` on hash change; no scheduled monitor job, no customer-reassessment trigger |
| Background workers / queue / cache | — | — | — | — | — | **NOT_IMPL** — no Celery/RQ/Redis; ingestion is a synchronous CLI |
| Backup / restore / DR | — | — | — | — | — | **NOT_IMPL** — no automation or tested runbook |

---

## 4. Applicability engine — differentiation proof (spec §15–§22)

`POST /ai-systems/intake-evaluate`, five systems, same tenant:

| System | Jurisdiction | Key facts | `risk_level` | EU AI Act class | Rules fired |
|---|---|---|---|---|---|
| Recruitment AI | DE | decides on individuals, domain=employment | **High Risk** | High-Risk (Annex III) | `EU-AIA-ANNEXIII-AUTOMATED-DECISIONS`, `GDPR-AUTOMATED-PROFILING`, … |
| GenAI Chatbot | DE | interacts w/ humans, synthetic content | **Specific Transparency** | Article 50 | `EU-AIA-ART50-TRANSPARENCY`, `GDPR-PERSONAL-DATA-EU`, … |
| Code Copilot | **US only** | no individual decisions | **Minimal Risk** | Minimal / No Specific Legal Risk | baseline only — **`eu_ai_act` and GDPR correctly excluded** |
| Autonomous IT Agent | DE | tools, code exec, no human approval | Specific Transparency | Article 50 | `AGENTIC-AUTONOMOUS-EXECUTION` → `agent_security_required=true`, `owasp_agentic_ai` added |
| Medical triage AI | FR | decides on individuals, domain=healthcare, sensitive data | **High Risk** | High-Risk (Annex III) | `EU-AIA-ANNEXIII-AUTOMATED-DECISIONS`, … |

Results are **not** one-size-fits-all. Every decision carries `rules_fired` provenance
and `ruleset_version`, and is persisted as an immutable `ApplicabilityDecision`.

**Limitation:** the intake schema silently ignores unknown fields (Pydantic default).
A client that sends the wrong field names gets a default (Minimal Risk) classification
with no error. The real frontend sends the correct shape; recommend `extra="forbid"`
on `IntakeQuestionnaireInput`.

---

## 5. Framework matrix

See [`COMPLIANCE_PLATFORM_VALIDATION_REPORT.md`](COMPLIANCE_PLATFORM_VALIDATION_REPORT.md) §3 for the full table. Summary:

| | Count |
|---|---:|
| Frameworks in manifest | 17 |
| Ingested from operator docs + official repos, structurally VALIDATED | **16** |
| Blocked (NIST 800-161 — should be an 800-53 overlay) | 1 |
| Total source-traceable normalized requirements | **~3,443** |
| Assessable via `POST /assessments` against the real requirement set | **16** (verified live for eu_ai_act, gdpr, nist_ai_rmf, mitre_atlas, owasp_llm, nist_sp_800_53) |
| Frameworks at `PRODUCTION_READY` | **0** — human requirement verification, control mapping and applicability rules are all at 0% |

---

## 6. Test summary (actual counts)

```
Backend pytest:            41 passed, 0 failed, 0 error
  test_api_security.py      7   (auth, RBAC, cross-tenant, evidence token, file-type)
  test_backend.py           7
  test_graph.py             7
  test_registries.py        4
  test_regulatory_ingestion 13
  test_workflows.py         3
Live E2E driver:           62 passed, 0 failed
  auth 7 · RBAC 1 · core workflow 13 · tenant isolation 26 · IDOR 4 · applicability 4 · regulatory API 7
Frontend nav (Playwright):  12 tabs, 0 crash, 0 console error
web-ui build:               PASS (tsc + vite)   npm audit: 0 vulnerabilities
frontend tsc:               PASS
Schema drift:               0
```

---

## 7. Honest status

### What fully works
Auth, RBAC (server-enforced), **multi-tenant isolation** (0 leaks found), the four
registries + dependency graphs, the versioned applicability engine, regulatory
ingestion + browser + search + source citations (16 frameworks), **assessments
against the real requirement set**, evidence (hash + signed download + review),
risk/findings/remediation, audit logging, the dashboard (numbers reconcile),
the executive report (JSON), the rules-based Copilot (tenant-scoped).

### What works with limitations
Assessments (no create-UI; naive scoring). Unified control mapping (legacy
content; 0 mappings onto the ingested requirements). Copilot & ATLAS & AI Verify
(present but not wired end-to-end / no execution). Reports (JSON only). Regulatory
change management (detection yes, orchestration no). Org structure (API > UI).

### What does not work / is not implemented
GitHub/Jira/AWS/Azure/Databricks connectors, automated evidence collection,
Shadow AI discovery, agent telemetry, policy-to-code, runtime enforcement,
red-team engine, vendor portal, auditor portal, user-invitation API, background
workers/queue/cache, backup/restore automation, DR.

### What requires configuration
`SECRET_KEY` (prod boot refuses the default), `DATABASE_URL` → PostgreSQL for
prod, `AI_PROVIDER` + `AI_API_KEY` for generative Copilot, `STORAGE_BACKEND=s3`
+ bucket for durable evidence, `BACKEND_CORS_ORIGINS` for the real frontend host.

### Before real customer use
1. Map the ~3,443 ingested requirements to the Unified Control Library (0 today).
2. Human-verify requirements used in scoring (all `MACHINE_EXTRACTED`).
3. Author applicability rules against the ingested requirement keys (rules today
   reference the legacy `EU-AIA-ART-09`-style keys).
4. Build a user-management / invitation flow (only the founder exists).
5. Point the Copilot RAG at `regulatory_*`.
6. Real compliance-determination logic (spec §53): applicable + control + evidence
   accepted + effectiveness + no blocking finding.
7. Retire the legacy `data/frameworks/*.json` once every consumer is migrated.

### Before public production
External penetration test · legal review of the platform's regulatory
interpretations · India DPDP / Gazette reproduction-licence review · PostgreSQL +
managed backups + tested restore · background worker + scheduled source-monitor ·
DR runbook + exercise · load test at target scale (not yet run) · SSO/MFA ·
CI security gates (secret scan, container scan, `npm audit`, SAST) — CI today runs
lint + tests + migration check + non-blocking `pip-audit` only.

**This platform is a strong internal-pilot / design-partner candidate. It is NOT
production-ready for unsupervised external customers** — see
[`PRODUCTION_READINESS_REPORT.md`](PRODUCTION_READINESS_REPORT.md) for the gate table.
