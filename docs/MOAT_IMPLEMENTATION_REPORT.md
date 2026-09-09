# AI Governance Autopilot — Moat Implementation Report

**Philosophy:** *Govern once. Prove everywhere.*
**Date:** 2026-09-09
**Scope of this pass:** P0 "Unified Governance Knowledge Graph" moat (MOAT 1 + 2) and the
8 additional high-value moats, implemented as production code paths (not mocks), plus the
frontend surface, tests, regression, and this report.

> **Reading guide.** This report distinguishes *fully implemented* (code + API + UI + tests +
> real data flowing) from *architecture-ready* (schema + service exist, not yet surfaced) from
> *not started*. Nothing below is described as working unless it is exercised by a passing test
> or a reproducible API call shown in this document.

---

## 1. Executive Summary

The platform already had a strong **regulatory ingestion subsystem** (17 frameworks, 18 versions,
**3,031 source-traceable requirements** with citations and provenance) and a **27-control Unified
Control Library** — but the two were disconnected. There was no way for a company to implement a
control once and see the effect across every framework it is obligated under, and no reviewed
mapping layer between the two.

This pass builds that connective tissue:

1. **Unified Governance Knowledge Graph (MOAT 1).** A reviewed mapping layer
   (`regulatory_requirement_control_maps`) now links the 27 Unified Controls to the real
   regulatory requirements. Three sources feed it, with different authority:
   - **Expert-curated** (`authoritative_control_mappings.json`, 54 mappings) → `EXPERT_REVIEWED`
   - **Hand-authored crosswalk** (`crosswalk_mappings.json`) → `APPROVED`
   - **AI proposer** (`control_mapper.py`, 173 candidates) → `AI_SUGGESTED` — **never authoritative**
2. **Cross-framework deduplication + compliance inheritance (MOAT 2).** A new coverage engine
   (`coverage.py`) computes, per requirement, whether it is `COVERED` / `PARTIALLY_COVERED` /
   `NOT_COVERED` / `NOT_MAPPED` — **and a one-sentence explanation of why**. A requirement is
   *never* covered merely because it is mapped, or because a sibling framework's requirement is
   covered. The mapped control must itself be **implemented + effective + freshly evidenced +
   free of a blocking finding, in that tenant**.
3. **Mapping validation workflow (Additional MOAT 2).** AI candidates move through
   `AI_SUGGESTED → NEEDS_REVIEW → EXPERT_REVIEWED → APPROVED` (or `REJECTED` / `DEPRECATED`),
   gated by a `LEGAL_REVIEW`-class role. Only `EXPERT_REVIEWED` / `APPROVED` count toward coverage.
4. **Immutable governance history (Additional MOAT 4, 5, 6).** Append-only
   `control_effectiveness_events`, `governance_decisions`, and content-hashed
   `governance_snapshots` (written on assessment approval).
5. **Frontend.** A new **Framework Coverage** console shows overall readiness, per-framework
   readiness bars, the per-requirement covered/why list, and the AI mapping review queue with
   approve/reject.

**Verdict (section 21): `SME PILOT READY`** for the governance-graph capability on the ingested
frameworks; the platform as a whole remains `LIMITED PILOT READY` pending the P1 items in
section 20.

---

## 2. Architecture Reviewed

| Layer | What exists | Health |
|---|---|---|
| Regulatory ingestion (`aegis_app/regulatory/`) | manifest + licence gate, per-framework parsers, 3-layer validation, immutable source artifacts, 17 frameworks / 3,031 requirements | **Strong.** Source-traceable, provenance-carrying. |
| Framework versions | `regulatory_framework_versions` — 18 rows | **Caveat:** `is_current` is `False` on all 18 rows (see §12). Coverage falls back to newest-by-`created_at`; correct today, fragile. |
| Unified Control Library | `data/unified_controls.json` (27), `data/crosswalk_mappings.json` | Stable, file-backed. |
| Mapping layer | `regulatory_requirement_control_maps` — **was 0 rows, now 231** | **New this pass.** |
| Coverage engine | `services/coverage.py` — **new** | Deterministic, explainable, tenant-scoped. |
| AI proposer | `services/control_mapper.py` — **new** | Curated anchor/support term model, word-boundary matched, MITRE ATLAS excluded. |
| Multi-tenant isolation | `tenant_id` on every business table; `get_current_user` reads `user.tenant_id` | Verified by tests + live E2E (62/62). |
| Governance history | 4 new tables (`control_effectiveness_events`, `compliance_inheritance`, `governance_decisions`, `governance_snapshots`) | **New this pass.** |

---

## 3. Existing Features (preserved — nothing removed)

All pre-existing tabs and endpoints remain: Executive Dashboard, AI Systems Inventory, Intake &
Classification, Unified Controls, 17-Framework Crosswalk, Models / Agents / Vendors registries,
Governance Graph, Assessments + approval workflow, Authoritative Frameworks browser, Evidence
Vault, AI Security & Agents, Risk Register & SLA, Executive Reports, Audit Trail, Copilot,
SME simple mode, onboarding, company switcher / multi-company membership.

Regression (§11) confirms the pre-existing suite is **unchanged and green (64/64)**; the live
customer E2E is **62/62**.

---

## 4. Moats — Fully Implemented

| # | Moat | Evidence |
|---|---|---|
| **1** | **Unified Governance Knowledge Graph** | `control_mapper.py` + `authoritative_control_mappings.json`; `GET /api/v1/unified-controls` returns each control with `reach.requirements` / `reach.frameworks` / `candidate_mappings_pending_review`. 231 mapping rows across 9 frameworks. |
| **2** | **Cross-framework control dedup + compliance inheritance** | `coverage.py`; `GET /api/v1/coverage/framework/{key}` and `/coverage/summary`. Per-requirement status + explanation string. Tests: `test_mapping_alone_never_covers`, `test_implemented_effective_evidenced_is_covered`, `test_no_cross_framework_inheritance`. |
| **Add-2** | **Mapping validation workflow** | `MAPPING_STATES` + `AUTHORITATIVE_MAPPING_STATES` in `models/regulatory.py`; `PUT /api/v1/control-mappings/{id}/review` with RBAC. Test: `test_mapping_review_transition_and_rbac` (Viewer → 403; Admin → 200; coverage updates). |
| **Add-1** | **Regulatory provenance on mappings** | 8 new columns: `mapping_source`, `mapping_version`, `effective_date`, `superseded_by_id`, `legal_review_status`, `expert_reviewed_by`, `expert_reviewed_at`, `last_reviewed_at`. Every row records how it was produced. |
| **Add-4** | **Control effectiveness history (append-only)** | `control_effectiveness_events` table; `POST /api/v1/unified-controls/{code}/status` writes a new event every time (never updates). `GET /{code}/history`. Test: `test_control_status_history_is_append_only`. |
| **Add-5** | **Decision provenance** | `governance_decisions` table; a row is written on assessment approval (`decided_by`, `decided_by_role`, `rationale`, `context`). |
| **Add-6** | **Immutable governance snapshots** | `governance_snapshots` table with `content_hash = sha256(payload)`; written on assessment approval (`api/assessments.py`), capturing framework, readiness, answered count, AI system lifecycle, evidence ids, open findings at approval, approver. |
| **3** | **Evidence reuse engine** | `coverage.evidence_reuse()`; `GET /api/v1/evidence/{id}/reuse` → unified controls, reviewed requirements, frameworks, AI systems one evidence object supports. |
| — | **AI proposer safety** | MITRE ATLAS excluded (threat KB, not obligations); word-boundary matching (`_phrase_in`) so `"rag"` never matches `storage`, `"raci"` never matches `racial`. Tests: `test_phrase_in_left_boundary_blocks_substrings`, `test_proposer_is_idempotent_and_candidate_only`. |

---

## 5. Moats — Partially Implemented

| # | Moat | Done | Remaining |
|---|---|---|---|
| **Add-3** | **Compliance inheritance from a shared scope** (org policy / vendor / infra → AI systems) | `compliance_inheritance` table + `GET/POST /api/v1/inheritance`; the coverage engine reads org-level inheritance (`applies_to_system_id IS NULL`) and credits a control as implemented (and effective if `verified_state=VERIFIED`). | Per-system inheritance resolution, an "inherited vs. direct" UI badge, and a verification workflow that expires `ASSERTED` inheritance. |
| **Add-7** | **AI lifecycle governance** | `AISystem.lifecycle_status` exists and is captured in approval snapshots. | Lifecycle state machine (DRAFT → PILOT → PRODUCTION → RETIRING → RETIRED) with gate checks and required-evidence-per-stage. |
| **11** | **Full traceability** | Requirement → source citation → mapping (with provenance) → control → evidence → finding is fully linked and queryable. | A single "trace" endpoint that returns the whole chain for one requirement in one call. |
| **Dashboard** | **Action-oriented governance dashboard** | Coverage summary + "why not ready" explanation list is live in the new Coverage console. | Fold the coverage readiness + next-mapping-review-actions into the Executive Dashboard tiles. |

---

## 6. Moats — Architecture-Ready (schema/service exists, not surfaced)

- **Add-8 Governance-as-code foundation** — `governance_snapshots` payloads are already
  deterministic JSON with a content hash; a `GET /governance/export` (YAML) and a diff endpoint
  are a thin layer on top. Not built this pass.
- **Regulatory versioning / change-impact (MOAT: change-impact foundation)** — `FrameworkVersion`
  + `superseded_by_id` on mappings give the substrate for "requirement X changed in version N+1,
  here are the affected controls". No diff engine yet.
- **Control testing lifecycle (MOAT 12)** — `CustomerControl.status` supports `Tested`;
  `control_effectiveness_events.lifecycle_state` column exists. No test-scheduling / due-date engine.

---

## 7. Moats — Not Started

P1 items, unchanged from the original request: regulatory versioning diff engine, template
library, consultant/multi-client mode, vendor trust reuse marketplace, integration abstraction
layer, automated evidence collectors, full copilot autopilot architecture, private-AI provider
abstraction. See §20 for the categorized roadmap.

---

## 8. Framework Validation Results

`GET /api/v1/regulatory/frameworks` — **17 frameworks, 3,031 requirements** (all
`published_status = DRAFT`; publishing workflow is a separate P1). No framework name appears in
the UI without backing requirements **except** where the UI explicitly says "Not yet imported"
(NIST SP 800-161).

Per-framework mapping + coverage for the demo tenant (Acme Financial), after loading the
expert-curated + crosswalk mappings and running the AI proposer:

| Framework | Requirements | Authoritatively mapped | Covered | Partial | Not covered | AI candidates pending |
|---|---:|---:|---:|---:|---:|---:|
| EU AI Act (2024/1689) | 419 | 25 | 13 | 10 | 2 | 19 |
| GDPR | 238 | 6 | 4 | 2 | 0 | 4 |
| OWASP LLM Top 10 (2026) | 10 | 8 | 6 | 0 | 2 | 2 |
| OWASP Agentic (2026) | 10 | 3 | 3 | 0 | 0 | 7 |
| NIST AI RMF 1.0 | 72 | 7 | 6 | 1 | 0 | 3 |
| NIST AI 600-1 (GenAI Profile) | 212 | 0 | 0 | 0 | 0 | 41 |
| DORA | 146 | 1 | 0 | 0 | 1 | 13 |
| NIS2 | 143 | 0 | 0 | 0 | 0 | 2 |
| EU CRA | 238 | 0 | 0 | 0 | 0 | 11 |

**Interpretation.** The two `NOT_COVERED` OWASP LLM rows are the proof that MOAT 2 works: LLM05
(Data & Model Poisoning) is mapped `EXACT` to `UC-AI-SEC-002`, but that control is `In Progress /
Partially Effective` in this tenant, so the requirement is correctly **not** counted as covered
despite a perfect mapping. Frameworks with `mapped = 0` have only AI candidates — coverage stays
honestly at 0 until a reviewer promotes them.

---

## 9. Unified Control Library Statistics

- **27 unified controls**, 12 domains (Governance, Accountability, Inventory, Risk, Prompt
  Security, Data/Model Integrity, Output Handling, Agent Security, Privacy, Transparency,
  Logging, Incident, Supply Chain, Testing, Accuracy, Vulnerability, Vendor, Resilience).
- **231 mapping rows**: `EXPERT_REVIEWED` 55 · `APPROVED` 3 · `AI_SUGGESTED` 173.
- Mapping type distribution (AI candidates): `EXACT` 2 · `STRONG` ~46 · `PARTIAL` ~125 ·
  `RELATED` 0 (the proposer floors a lone-anchor match at `PARTIAL`).
- **AI proposer produced 173 candidates across 12 frameworks**; no single control exceeds ~40
  candidates (`UC-AI-TST-001` is highest at 40 because every OWASP entry literally ends
  "…evidence them via adversarial testing"). MITRE ATLAS: **0** (excluded by design).
- Crosswalk seed: 5 of 81 legacy ids resolved to real requirement keys (the file predates the
  ingestion subsystem and uses thematic ids like `NIST-600-CBRN`); the unresolved 76 are a
  known debt item (§16), superseded by `authoritative_control_mappings.json`.

---

## 10. Evidence Reuse Statistics

`GET /api/v1/evidence/{id}/reuse` returns, for one evidence object, the count of unified
controls, reviewed requirements, frameworks, and AI systems it currently supports. For the demo
tenant, an evidence item mapped to `UC-AI-RSK-001` now reaches **EU AI Act Art. 9(1)/(2)/(5) +
NIST AI RMF** through a single upload — versus re-uploading per framework before this pass.
The reuse multiplier grows automatically as more mappings are promoted to `EXPERT_REVIEWED`.

---

## 11. Test Results

```
backend/ pytest:            76 passed        (was 64; +12 new in test_unified_control_graph.py)
live_customer_e2e.py:       62 / 62 PASS
frontend tsc --noEmit:      clean
alembic upgrade/downgrade:  round-trips cleanly (d4e5f6a7b8c9 <-> c3d4e5f6a7b8)
```

New tests (`tests/test_unified_control_graph.py`):

| Test | Asserts |
|---|---|
| `test_phrase_in_left_boundary_blocks_substrings` | `"rag"` ∉ `storage`; `"raci"` ∉ `racial`; stem matches work |
| `test_score_requires_an_anchor` | no anchor ⇒ score 0 |
| `test_requirement_status_matrix` | not-mapped / mapped-not-implemented→NOT_COVERED / implemented-no-evidence→PARTIAL / full→COVERED / blocking-finding→PARTIAL |
| `test_mapping_alone_never_covers` | EXPERT_REVIEWED EXACT mapping + no control ⇒ `NOT_COVERED` |
| `test_implemented_effective_evidenced_is_covered` | control implemented+effective + fresh accepted evidence ⇒ `COVERED` |
| `test_ai_suggested_mapping_does_not_count` | `AI_SUGGESTED` mapping ⇒ `mapped_requirements = 0`, surfaced as candidate |
| `test_no_cross_framework_inheritance` | shared control not implemented in tenant B ⇒ B's requirement `NOT_COVERED` even though covered in A |
| `test_proposer_is_idempotent_and_candidate_only` | 2nd run creates 0; MITRE untouched by AI |
| `test_mapping_review_transition_and_rbac` | Viewer→403; Admin→200; coverage reflects promotion |
| `test_coverage_endpoint_tenant_isolation` | tenant B sees `covered = 0` for tenant A's work |
| `test_control_status_history_is_append_only` | 3 status changes ⇒ ≥3 history events |
| `test_provenance_columns_and_new_tables_exist` | migration added 8 columns + 4 tables |

---

## 12. Known Bugs / Data-Quality Issues

1. **`FrameworkVersion.is_current` is `False` on all 18 rows.** Coverage's `_current_version()`
   falls back to newest-by-`created_at`, which is correct for every framework today, but this
   should be set explicitly by the ingestion pipeline. *Severity: low, latent.*
2. **`crosswalk_mappings.json` legacy ids (76/81 unresolved).** The file predates the ingestion
   subsystem. Superseded by `authoritative_control_mappings.json`; the loader logs the
   unresolved keys. *Severity: low (cosmetic — those mappings simply don't load).*
3. **Some ingested requirement text carries mojibake** (`�` where a smart-quote was). Originates
   in the source parsers, not this pass. *Severity: low, display-only.*
4. **`next build` while `next dev` is running corrupts `.next`** (recurring environmental
   footgun, documented in project memory). Not a code bug.
5. **`published_status = DRAFT` on all 3,031 requirements.** There is no publish workflow yet, so
   the "authoritative frameworks" browser shows draft content. *Severity: medium for a real
   customer — see §14.*

---

## 13. Security / Tenant / RBAC Results

- **Tenant isolation:** every new query filters by `tenant_id`; `coverage.py` and
  `unified_controls.py` take `current_user.tenant_id`, never a path/JWT value. Verified by
  `test_coverage_endpoint_tenant_isolation` and live E2E section 12 (5/5 cross-tenant reads
  blocked, no list leakage, copilot injection blocked).
- **RBAC:** `PUT /control-mappings/{id}/review` and `POST /admin/propose-mappings` require
  `require_mapping_review` (Tenant Admin / AI Governance Lead / Compliance Manager / Auditor /
  Super Admin). `POST /unified-controls/{code}/status` requires `GOVERNANCE_WRITE`. Viewer role
  → 403 (tested).
- **Audit:** every write path (`propose-mappings`, `review`, `status`) emits an `AuditEvent`;
  approvals additionally emit a `GovernanceDecision` + hashed `GovernanceSnapshot`.
- **No secrets, no new external calls, no new file-write paths.** The AI proposer is pure
  keyword matching — no LLM call, no network.

---

## 14. Production Blockers

| Blocker | Why it blocks a paying customer | Fix size |
|---|---|---|
| Requirements are all `DRAFT` | Customer-facing "authoritative" content must be through a review/publish gate | Medium (workflow + one status column already exists) |
| `is_current` unset on framework versions | A second ingested version of any framework could silently flip coverage | Small (ingestion pipeline one-liner + backfill migration) |
| Coverage only meaningful for the 5 frameworks with expert-curated mappings | EU AI Act, GDPR, OWASP LLM/Agentic, NIST AI RMF are seeded; DORA/NIS2/CRA/NIST-600 have candidates only | Medium (expert curation effort, not code) |
| SQLite dev DB | Not for production | Known; Postgres DSN is a config change, migrations are Postgres-safe |
| Session token in `sessionStorage` | XSS token theft | Medium (httpOnly cookie + CSRF) — pre-existing, tracked in `PRODUCTION_READINESS_REPORT.md` |

---

## 15. Technical Debt Introduced This Pass

- `control_mapper.CONTROL_SPEC` is a hand-tuned term dictionary. It is deliberately conservative
  (candidates only, human-reviewed) but it will need curation as frameworks are added.
- `coverage.framework_coverage()` recomputes `_control_assurance()` per call (one set of small
  queries). Fine at current scale (hundreds of requirements); add a per-request cache if a
  tenant reaches thousands of controls.
- `authoritative_control_mappings.json` is checked-in seed data loaded through the same admin
  endpoint as the AI proposer. A dedicated migration-time loader would be cleaner.
- The Coverage console (`CoverageExplorer.tsx`) is a self-contained tab; it duplicates a little
  bar/badge styling that could move to a shared component.

---

## 16. Next 10 Features (priority order)

1. **Publish workflow for regulatory requirements** (`DRAFT → IN_REVIEW → PUBLISHED`), gate the
   Frameworks browser and coverage on `PUBLISHED`.
2. **Set `is_current` in the ingestion pipeline** + backfill migration.
3. **Fold coverage readiness into the Executive Dashboard** — a "Governance readiness" tile that
   drills into the Coverage console, plus a "N mappings await your review" action card.
4. **Expert-curate mappings for DORA, NIS2, EU CRA, NIST AI 600-1** (code is ready; this is
   content).
5. **Per-system compliance inheritance resolution + "inherited" badge** in the requirement list.
6. **Single `GET /trace/requirement/{key}`** returning the full chain (source → mapping →
   control → evidence → findings → snapshots).
7. **Control testing lifecycle** — due dates, "test now", auto-`STALE` on overdue, feeding
   `control_effectiveness_events`.
8. **Governance-as-code export** (`GET /governance/export.yaml`) + snapshot diff.
9. **Change-impact engine** — when a new framework version is ingested, diff requirements and
   flag affected mappings/controls.
10. **Mapping review inbox** with bulk actions and a "confidence + rationale + source excerpt
    side-by-side" review view.

---

## 17. Remaining Roadmap (categorized)

**Knowledge graph & mappings:** items 1, 4, 6, 9, 10 above; template library; regulatory
versioning diff.
**Assurance & evidence:** control testing lifecycle; automated evidence collectors; evidence
freshness dashboards; vendor trust reuse.
**Workflow & UX:** dashboard action cards; consultant/multi-client mode; onboarding deepening;
copilot autopilot.
**Platform:** Postgres cutover; httpOnly session cookies; integration abstraction layer;
private-AI provider abstraction; governance-as-code + CI gate.

---

## 18. Full End-to-End Workflow Validation

Exercised against the live backend (`:8010`) as `compliance@acmefinancial.com`:

1. Login → `GET /unified-controls` → 27 controls with `reach` + tenant status ✅
2. `POST /unified-controls/admin/propose-mappings` → `{expert_curated: 54, crosswalk_seed: 3, ai_proposer: 173}` ✅
3. `GET /coverage/summary` → `overall_readiness_pct: 8.6`, per-framework breakdown + explanation ✅
4. `GET /coverage/framework/owasp_llm` → 8 mapped, 6 `COVERED`, 2 `NOT_COVERED` (poisoning control In Progress) with per-requirement explanation strings ✅
5. `GET /control-mappings?state=AI_SUGGESTED` → 173 candidates with `state_counts` ✅
6. `PUT /control-mappings/{id}/review {decision: EXPERT_REVIEWED}` → state transitions, `reviewed_by` set, coverage recomputes ✅
7. `POST /unified-controls/UC-AI-RSK-001/status` ×3 → 3 append-only `control_effectiveness_events`, `GET /history` returns all 3 ✅
8. Assessment approval → `governance_snapshots` row with `content_hash`, `governance_decisions` row ✅
9. `GET /evidence/{id}/reuse` → controls/requirements/frameworks/systems reached ✅
10. Cross-tenant: second tenant sees `covered: 0` for the same framework ✅

Live customer E2E script: **62/62 PASS** (inventory, intake, classification, controls, evidence
lifecycle, assessments, findings→remediation, reports, dashboard, audit, tenant isolation,
copilot grounding).

---

## 19. Existing Data Validation

- **17 frameworks / 3,031 requirements** confirmed via API (previous session counted 3,211
  including both MITRE ATLAS versions and both OWASP LLM versions; the coverage engine scopes to
  one current version per framework).
- Every requirement carries `requirement_key`, `source_reference`, `normalized_requirement`;
  most carry `source_text` where the licence permits redistribution.
- MITRE ATLAS correctly typed as `THREAT_KNOWLEDGE_BASE` and excluded from the obligation
  proposer; its control links come only from the hand-authored crosswalk.
- Demo tenant has 27 `CustomerControl` rows (25 Implemented/Effective, 2 In Progress) so the
  coverage engine has real assurance state to compute against.

---

## 20. Git Diff Summary

**Modified (7 files, +254 / −18):**

| File | Change |
|---|---|
| `backend/aegis_app/models/regulatory.py` | `MAPPING_STATES` / `AUTHORITATIVE_MAPPING_STATES`; 8 provenance columns on `RequirementControlMapping` |
| `backend/aegis_app/models/models.py` | 4 new models: `ControlEffectivenessEvent`, `ComplianceInheritance`, `GovernanceDecision`, `GovernanceSnapshot` |
| `backend/aegis_app/api/assessments.py` | write `GovernanceSnapshot` (content-hashed) + `GovernanceDecision` on approve |
| `backend/aegis_app/api/evidence.py` | `GET /{id}/reuse` |
| `backend/aegis_app/main.py` | register `unified_controls` router |
| `frontend/src/app/page.tsx` | "Framework Coverage" nav item + tab render + `Scale` icon |
| `frontend/src/lib/api.ts` | 11 new API client functions for the graph/coverage endpoints |

**New (7 files, ~1,730 lines):**

| File | Lines | Purpose |
|---|---:|---|
| `backend/aegis_app/services/control_mapper.py` | 306 | AI mapping proposer + expert/crosswalk seed loaders |
| `backend/aegis_app/services/coverage.py` | 293 | compliance-inheritance coverage engine |
| `backend/aegis_app/api/unified_controls.py` | 372 | 11 endpoints: controls, mappings, review, coverage, inheritance |
| `backend/aegis_app/data/authoritative_control_mappings.json` | 54 mappings | expert-curated, real requirement keys |
| `backend/alembic/versions/d4e5f6a7b8c9_unified_control_graph.py` | 134 | 8 columns + 4 tables, reversible |
| `backend/tests/test_unified_control_graph.py` | 350 | 12 tests |
| `frontend/src/components/CoverageExplorer.tsx` | 273 | Framework Coverage console + review queue |

Alembic head: `d4e5f6a7b8c9`. No pre-existing migration modified.

---

## 21. Production Readiness Verdict

### `SME PILOT READY` — for the Unified Governance Knowledge Graph capability

**On the ingested + expert-curated frameworks (EU AI Act, GDPR, OWASP LLM, OWASP Agentic, NIST
AI RMF):** a 10–250-person company can implement a Unified Control once and see explainable,
tenant-scoped coverage across every mapped requirement, with an AI-assisted (never
auto-authoritative) mapping pipeline and immutable governance history. This is pilot-grade:
tests pass, tenant isolation holds, the workflow is real.

### Platform-wide: `LIMITED PILOT READY`

Unchanged from before this pass, gated by §14: `DRAFT` requirement content, SQLite, session
storage token, and expert curation still needed for DORA / NIS2 / CRA / NIST-600. None of these
are introduced by this pass; they are the pre-existing gap to `SME PILOT READY` platform-wide.

---

## 22. How to Run

```bash
# backend  (port 8010)
cd backend
ENVIRONMENT=development SEED_DEMO_DATA=true \
  BACKEND_CORS_ORIGINS='["http://localhost:3001","http://127.0.0.1:3001"]' \
  python -m uvicorn aegis_app.main:app --host 127.0.0.1 --port 8010

# one-time: build the mapping graph for the demo tenant
curl -X POST http://127.0.0.1:8010/api/v1/unified-controls/admin/propose-mappings \
  -H "Authorization: Bearer <token>"

# frontend  (port 3001)
cd frontend && NEXT_PUBLIC_API_BASE=http://127.0.0.1:8010/api/v1 npm run dev -- -p 3001
```

Login: `compliance@acmefinancial.com` / `Password123!` → **Framework Coverage** tab.
