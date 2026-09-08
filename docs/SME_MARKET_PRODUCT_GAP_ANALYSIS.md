# SME / Mid-Market Product Gap Analysis

_Author: repositioning pass, 2026-09-08. Based on direct inspection of the repo, DB, live API, and UI. No feature is proposed for removal._

## 0. Positioning shift

| | Today | Target |
|---|---|---|
| Framing | "AegisAI Governance OS" — enterprise AI governance suite | **"AI Trust & Compliance Platform"** — "Use AI safely. Pass customer reviews. Meet regulations. Win enterprise customers." |
| Primary user | AI Governance Lead / CISO at a regulated enterprise | Founder / CTO / security lead at a 10–250-person B2B AI/SaaS company |
| First run | Enterprise dashboard assuming a populated tenant | 5-minute onboarding → applicability result → AI Trust Score → "what to do next" |
| Depth | Full framework/control/evidence/workflow machinery | **Same machinery, hidden behind Simple mode; exposed under Advanced** |

## 1. Existing capabilities inventory (PRESERVE ALL)

### Backend (FastAPI, async SQLAlchemy, 20 API routers, 72 routes)

| Capability | Where | State |
|---|---|---|
| Auth: signup, login, JWT (bcrypt, 24h), `/auth/me` | `api/auth.py`, `core/security.py` | ✅ working |
| Multi-tenant isolation (tenant_id on every business table) | `models/models.py` | ✅ working, regression-tested |
| RBAC role checks | `core/permissions.py`, 12/20 routers | ⚠️ partial coverage |
| Organization / BusinessUnit / AIProduct hierarchy | `models.py` | ✅ working |
| AI System registry + intake evaluation | `api/ai_systems.py` | ✅ working |
| Model registry + version history + system links | `api/model_registry.py` | ✅ working |
| Agent registry + permission graph + risk score | `api/agent_registry.py`, `services/agent_risk.py` | ✅ working |
| Vendor registry + impact analysis + regulatory exposure | `api/vendor_registry.py`, `api/graph.py` | ✅ working |
| **Per-system applicability rule engine** (versioned JSON, 13 rules, rule-level provenance, persisted `ApplicabilityDecision` with review workflow, decision statuses APPLICABLE…LEGAL_REVIEW_REQUIRED) | `services/rule_engine.py`, `services/applicability.py`, `data/applicability_rules.json` | ✅ working — **but system-scoped only, not company-scoped** |
| Unified Control Library (27 controls) + crosswalk mappings (27 → framework requirements) | `data/unified_controls.json`, `data/crosswalk_mappings.json`, `services/crosswalk.py` | ✅ working (demo-scale) |
| Customer control state (status + effectiveness + notes + owner) | `CustomerControl` model, `api/controls.py` | ✅ working |
| Explainable scoring (implementation / evidence / effectiveness / readiness, finding deductions) | `services/scoring.py` | ✅ working — **used by dashboard, not rolled up as an "AI Trust Score"** |
| Assessments + responses (per requirement) + review workflow | `api/assessments.py`, `Assessment*` models | ⚠️ backend works; **no UI**; create-flow now prefers ingested regulatory reqs (recent change) |
| Evidence: upload, hash, tenant-bound signed download (TTL), MIME allowlist, review workflow, control mapping, separation of duties | `api/evidence.py`, `services/storage.py` | ✅ working |
| Risk register + inherent/residual + acceptance workflow | `api/risks.py`, `Risk` model | ✅ working |
| Findings + remediation tasks + SLA | `api/findings.py`, `Finding`/`RemediationTask` | ✅ working |
| Regulatory knowledge graph queries (requirement→systems, vendor exposure, multi-framework controls, shared high-risk models, agent tool dependents) | `api/graph.py` | ✅ working |
| **Regulatory ingestion subsystem** — 16 frameworks / 18 versions / 3,211 source-traceable requirements / 7,970 hierarchy nodes / 251 definitions / SHA-256 artifacts / licence gate / 4-layer validation / immutable published versions | `aegis_app/regulatory/**`, `regulatory_*` tables, `api/regulatory.py` | ✅ ingested + structurally validated — **DRAFT, not wired to UI/reports/Copilot; 0 control maps; 0 applicability rules; 0 human-verified** |
| Governance Copilot (deterministic, rules-based, grounded in tenant data + crosswalk, cites sources, no LLM) | `services/copilot.py`, `api/copilot.py` | ✅ working — grounded on legacy demo frameworks |
| Executive report (JSON) | `api/reports.py`, `services/report_generator.py` | ⚠️ demo-data-scoped; no PDF/CSV; one report type |
| Audit events | `AuditEvent` model, `api/audit.py` | ⚠️ partial event coverage |
| Policy documents model | `PolicyDocument` model | ⚠️ model only, no generation UI |
| Incident reports model | `IncidentReport` model | ⚠️ model only |
| Security overview + agent kill-switch | `api/security.py` | ✅ working (kill-switch is an endpoint, detect-only elsewhere) |
| Prod-config fail-closed guard | `core/config.py::validate_production_settings` | ✅ working |
| Alembic migrations (2: baseline + regulatory) | `alembic/versions/` | ✅ single head |

### Frontend (Next.js 14, single `page.tsx`, 2,716 lines, 15 nav items)

Dashboard · AI Systems Inventory · Intake & Classification · Unified Controls · 17-Framework Crosswalk · Models · Agents · Vendors · Governance Graph · Authoritative Frameworks · Evidence Vault · AI Security & Agents · Risk Register & SLA · Executive Reports · Audit Trail. Login/signup screen. Copilot slide-over. All calls go to legacy `/frameworks` etc. — **the frontend never calls `/api/v1/regulatory/*`.**

### Tests
41 backend tests, all passing (`pytest`). Tenant-isolation cases in `test_graph.py`, `test_registries.py`, `test_api_security.py`, `test_backend.py`. No frontend tests. No E2E.

## 2. Framework status (PRESERVE ALL — none removed)

All 19 required framework families are present in at least the ingestion manifest. Ingested + structurally validated: EU AI Act, GDPR, EU CRA, NIS2, DORA, NIST AI RMF, NIST AI 600-1, NIST CSF 2.0, SSDF 800-218, NIST 800-53, OWASP LLM (2025+2026), OWASP Agentic, UK AI Cyber Code, India DPDP (Rules), MITRE ATLAS, Singapore AI Verify. **Not imported: NIST SP 800-218A, NIST SP 800-161** (see `MISSING_OR_UNIMPORTED_SOURCES.md`). Legacy demo JSON for 17 frameworks remains the UI's source and is **retained**.

## 3. Missing SME capabilities (this repositioning)

| # | Capability | Section | Backend | Frontend | DB | Priority |
|---|---|---|---|---|---|---|
| 1 | Company onboarding questionnaire (not per-system) | 5 | new `onboarding` router | new wizard | new `organization_profiles` | **P1** |
| 2 | **Company-level applicability engine** → framework exposure map (direct / indirect-supply-chain / contractual / recommended / not-applicable / insufficient-info, each with confidence + reasoning + source article + open questions) | 6, 23, 24 | new `company_rule_engine` + `data/company_applicability_rules.json` | exposure panel | reuse `applicability_decisions` (scope=`organization`) | **P1** |
| 3 | Compliance Profile dashboard + **AI Trust Score** (company rollup of real control/evidence/finding state across dimensions: AI Governance, AI Security, Privacy, Vendor Risk, Agent Security, Secure Development) | 7, 22 | new `sme` router `/trust-score` | SME home | none (computed) | **P1** |
| 4 | "What should I do next?" prioritized actions from real gaps (unregistered providers, missing policies, control status, open findings, missing evidence) | 16 | `/sme/next-actions` | actions list | none (computed) | **P1** |
| 5 | Simple/Advanced UI mode toggle + progressive-disclosure SME nav | 4, 28 | `ui_mode` on user | mode switch + SME shell | `users.ui_mode` | **P1** |
| 6 | Quick-add flows for AI tool / model / agent / vendor with auto-linking | 9, 10 | extend existing create endpoints w/ `quick_add` | quick-add modals | none | **P2** |
| 7 | SOC 2 / ISO 27001 / ISO 42001 as **metadata-only** frameworks + UC mappings, architecture-ready for licensed content | 3, 19 | framework registry entries `content_availability=METADATA_ONLY` | framework list badges | `regulatory_sources` rows | **P2** |
| 8 | Sector starter packs (B2B AI SaaS, FinTech, HealthTech, HRTech, India IT, CRA product) | 19 | `data/starter_packs.json` + apply endpoint | pack picker in onboarding | none | **P2** |
| 9 | Policy generation (10 templates, company context, versioned, acknowledgement, evidence) | 17 | `data/policy_templates/` + `policy` router | policy editor | extend `PolicyDocument` | **P2** |
| 10 | AI Trust Pack (one-click customer-facing export, secure link, expiry, access control) | 14 | `trust_pack` router + renderer | pack builder | new `trust_packs` | **P2** |
| 11 | Trust Center (customer-facing, public/NDA/authenticated tiers) | 15 | public router + access tiers | public micro-site | new `trust_center_*` | **P3** |
| 12 | Customer questionnaire automation (upload, map to controls/evidence, propose answers, human approval) | 13 | `questionnaire` router + matcher | questionnaire workspace | new `questionnaires`, `questionnaire_items` | **P2/P3** |
| 13 | Free public lead-gen assessment | 21 | unauthenticated `/public/assessment` | standalone page | ephemeral | **P3** |
| 14 | Enterprise Sales Readiness dashboard | 27 | `/sme/sales-readiness` | panel | computed | **P2** |
| 15 | Automated evidence connectors (GitHub, AWS, Azure, GCP, M365, Workspace, Jira, Slack) | 18 | connector framework + per-connector | connector settings | new `connectors`, `connector_evidence` | **P3** |
| 16 | Shadow AI discovery (M365/Workspace/GitHub/Slack/cloud/expense signals) | 11 | discovery workers | findings feed | new `shadow_ai_signals` | **P3/P4** |
| 17 | Enhanced vendor intelligence (training-on-data flag, sub-processors, regions, DPA, retention, approved/prohibited use) | 10 | extend `Vendor` model | vendor detail | migrate `Vendor` | **P2** |
| 18 | Agent telemetry ingestion + runtime policy-to-code + runtime governance modes | 12, (Phase 4) | new subsystem | agent runtime views | new `agent_events`, `runtime_policies` | **P4** |
| 19 | Automated AI evaluations / red-team suites (prompt injection, PII leak, tool misuse…) | 12, (Phase 4) | eval engine | eval runs | new `evaluations` | **P4** |
| 20 | Billing/entitlement architecture (FREE/STARTER/GROWTH/REGULATED/ENTERPRISE), usage limits, invitations, trial | 20 | `plans`, entitlement middleware | plan/usage UI | new `plans`, `entitlements`, `invitations` | **P2/P5** |
| 21 | SSO (OIDC) / SCIM | 20, (Phase 5) | auth provider abstraction | SSO config | new `sso_configs` | **P5** |
| 22 | Report export (PDF/CSV/XLSX) + more report types + auditor evidence pack + historical reproducibility | 22, (Phase 5) | renderers | report picker | version snapshots | **P3/P5** |

## 4. Required DB changes (all additive, safe migrations)

Phase 1: `organization_profiles` (1:1 org, JSON questionnaire + derived profile); `users.ui_mode` (default `"advanced"` so existing users are unchanged); `applicability_decisions.scope` (default `"system"`) + nullable `open_questions`, `framework_exposure` JSON.

Later phases add tables listed in §3; **no existing table is altered destructively, no ID scheme changes, no framework IDs removed.**

## 5. Security / infra gaps (from `ENTERPRISE_PRODUCTION_READINESS_REPORT.md`)

Backup/restore (none), load test (none), SAST/dependency/container scan (not in CI), full RBAC matrix, `/ready` + metrics + error tracking, independent pen-test, SSO/MFA/lockout/reset, PostgreSQL-in-anger. These gate large-enterprise GA, not SME pilot.

## 6. Testing gaps

No frontend/component tests, no E2E, no applicability-engine property tests beyond the per-system happy path, no cross-tenant sweep of every endpoint, no performance baseline.

## 7. Implementation order (this pass delivers Phase 1 core)

**This session:** §3 items 1–5 + 7 (metadata frameworks) — backend + migration + tests + SME UI surface + gap doc.
**Documented as roadmap with architecture notes:** everything else, in the Phase 2–5 order from the brief.
