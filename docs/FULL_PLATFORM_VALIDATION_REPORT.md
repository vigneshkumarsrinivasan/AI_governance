# Full Platform Validation Report

_Run 2026-09-08. Live backend (`:8010`) + Next.js UI (`:3001`) + SQLite. Method: real customer journeys via API/UI, `pytest`, headless-browser checks. No feature removed. This is the regression baseline._

## Part 1 — System inventory (regression baseline)

### A. Capabilities found (present + working unless noted)
Auth (JWT/bcrypt) · multi-tenant isolation · RBAC (18-role matrix, `core/permissions.py`) · Organization/BusinessUnit/AIProduct hierarchy · **SME onboarding + company applicability engine + AI Trust Score + next-actions** (added prior pass) · AI System registry + per-system intake engine (13 versioned rules) · Model registry (+version history, +system links) · Agent registry (+permission graph, +risk score) · Vendor registry (+impact, +regulatory-exposure graph, full AI-provider intelligence fields) · Unified Control Library (27) + crosswalk mappings · Customer control state (status+effectiveness) · Explainable scoring · Assessments (now driven by **real ingested regulatory requirements** — EU AI Act = 419) · Evidence (upload, SHA-256, tenant-bound signed download w/ TTL, MIME allowlist, review workflow, separation of duties) · **Findings (manual + auto from failed control / rejected evidence) + Remediation tasks + close workflow** (added this pass) · Risk register (inherent/residual, acceptance workflow w/ justification+expiry) · Regulatory knowledge-graph queries · Regulatory ingestion subsystem (16 frameworks/18 versions, 3,211 source-traceable requirements, SHA-256 artifacts, licence gate, 4-layer validation) · Governance Copilot (deterministic, rules-based, tenant-grounded, cited) · Executive report (JSON) · Audit trail · Security overview + agent kill-switch · Prod-config fail-closed guard.

### B. APIs — **82 routes** (was 80; +`POST /findings`, `PUT /findings/{id}`, `POST /remediations`; all pre-existing routes retained). Full list in `openapi.json`.

### C. Database entities — **36 tables** (`organization_profiles` added prior pass; none removed). Row counts captured in the E2E report.

### D. Frontend routes — single SPA. Simple mode: Home / What applies to us / What to do next / Frameworks. Advanced mode: Dashboard · AI Systems Inventory · Intake & Classification · Unified Controls · 17-Framework Crosswalk · Models · Agents · Vendors · Governance Graph · Authoritative Frameworks · Evidence Vault · AI Security & Agents · Risk Register & SLA (**now with Findings + New Finding + Remediation**) · Executive Reports · Audit Trail. Reciprocal mode toggles.

### E. Integrations — **none configured**. `AI_PROVIDER=rules` (no external LLM). No GitHub/AWS/Azure/GCP/Jira/Slack connectors implemented. Object storage: local filesystem (S3 code path exists, unconfigured).

### F. Regulatory / framework content — 19 families. Ingested + structurally validated: EU AI Act, GDPR, EU CRA, NIS2, DORA, NIST AI RMF, NIST AI 600-1, NIST CSF 2.0, SSDF 800-218, NIST 800-53, OWASP LLM (2025+2026), OWASP Agentic, UK AI Cyber Code, India DPDP (Rules), MITRE ATLAS, Singapore AI Verify. **Not imported: NIST SP 800-218A, NIST SP 800-161.** SOC 2 / ISO 27001 / ISO 42001: metadata + control mappings only (copyright-safe). All 16 ingested versions are `published_status=DRAFT`, 0 human-verified, 0 unified-control maps on ingested keys, 0 applicability rules on ingested keys (unchanged — see `ENTERPRISE_PRODUCTION_READINESS_REPORT.md`).

### G. Enterprise features — business units, org hierarchy, full framework/control/evidence/assessment depth, knowledge graph, workflows, audit, regulatory versioning subsystem, RBAC.

### H. SME features — onboarding wizard, company applicability, AI Trust Score, next-actions, sales-readiness, starter packs, simple-mode shell.

### I. Security controls — JWT auth, bcrypt, tenant_id scoping on every business table + query, RBAC dependency tiers, separation of duties on evidence review, security-headers middleware (CSP/X-Frame/nosniff/Referrer-Policy), signed time-limited evidence download tokens, MIME allowlist + size cap on uploads, prod-config guard, deterministic (non-injectable) copilot.

### J. Tests — **56 passing** (`pytest`): api_security 7, backend 7, findings_remediation 5 (new), graph 7, registries 4, regulatory_ingestion 13, sme_onboarding 10, workflows 3. Frontend: `tsc --noEmit` clean; no component/E2E test framework configured. Ad-hoc live E2E script: **62/62 checks pass**.

## Part 2 — Non-removal check

| Baseline artifact | Before | After | Status |
|---|---|---|---|
| API routes | 80 | 82 (+3, 0 removed) | ✅ |
| DB tables | 36 | 36 | ✅ |
| DB columns | — | +0 this pass | ✅ |
| Framework families | 19 | 19 | ✅ |
| Unified controls | 27 | 27 | ✅ |
| Report types | 1 (executive JSON) | 1 | ✅ (no removal) |
| Roles / permissions | 18 / 6 tiers | 18 / 6 tiers (+`require_finding_write` derived) | ✅ |
| Assessments | backend + regulatory-req wiring | unchanged | ✅ |
| Migrations | 3 heads-chain, valid | 3, valid | ✅ |

**No frontend route 404s, no API removed, no table/field dropped, no framework/control/assessment/report/integration/permission/workflow removed.**

## Part 3 — Defects found & fixed this pass

| # | Defect | Severity | Fix | Regression test |
|---|---|---|---|---|
| 1 | No way for a customer to raise a Finding (only the seed script could). `/findings` was GET-only. | P1 | `POST /findings` (RBAC: governance+security+audit roles), `PUT /findings/{id}` for progress/close (row never deleted). | `test_findings_remediation.py::test_manual_finding_and_remediation_lifecycle` |
| 2 | Failed control test did not create a finding — the "control fails → finding → risk → remediation" loop (spec §16/§26/§32) was broken. | P1 | `PUT /controls/{id}` with `effectiveness=Ineffective` auto-raises a "Failed Control" finding (Critical for security domains); recovery auto-resolves it; deduped. | `::test_failed_control_autocreates_and_recovers_finding` |
| 3 | No way to create a Remediation task (only GET + status PUT). | P1 | `POST /remediations` linked to a finding; moves finding → Remediating; completing all tasks → finding Resolved. Works with no Jira. | `::test_manual_finding_and_remediation_lifecycle` |
| 4 | Rejected/insufficient evidence did not raise a finding — deliberately weak evidence could sit unflagged (spec §15). | P1 | `PUT /evidence/{id}/review` with `Rejected`/`Insufficient` auto-raises a "Missing Evidence" finding per mapped control. | `::test_rejected_evidence_autocreates_finding` |
| 5 | Reports tab showed hardcoded demo prose ("ACME FINANCIAL SERVICES", "retail banking and credit underwriting", fixed "Loan Decision AI" narrative) to every tenant (spec §50/§71). | P1 | Report header + narrative now generated from live tenant data (org name, real system counts, real risk mix, real scores). | Browser check + `full_e2e` dashboard assertions |
| 6 | Dashboard hero hardcoded "Acme Financial" for all tenants. | P2 | Uses `currentUser.organization_name` (fixed prior pass, re-verified). | — |
| 7 | Copilot default answer echoed the raw user query verbatim into the response. | P3 (hygiene) | Removed the echo; answer no longer reflects untrusted input. | `full_e2e` injection check |
| 8 | Findings/remediation had no UI — dead end for a real user. | P1 | Risk Register tab now lists findings, has "+ New Finding" inline form, "+ Remediation" and "Resolve" per finding. | Browser check |

## Part 4 — Not implemented (documented, not defects to auto-build)

No Redis / background workers / schedulers / notification system / email service · no Assessments UI page (backend works, driven via API) · no vendor portal · no Trust Pack / Trust Center / questionnaire automation (roadmap) · no Shadow AI / runtime governance / agent telemetry / automated evaluations · no PDF/CSV/XLSX/ZIP export (JSON only) · no billing/entitlements · no SSO/SCIM/MFA/password-reset/email-verification · no backup automation · no load test at 5,000-system scale · no mobile/accessibility audit. NIST 800-218A + 800-161 not ingested. Ingested regulatory content still not wired to Copilot/reports/crosswalk (assessments now use it).
