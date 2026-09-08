# End-to-End Test Report

_Run date: 2026-09-06. Driver: `scratchpad/validate.py` (62 HTTP assertions) +
`backend/tests/` (41 pytest) + Playwright frontend nav._

---

## 1. Fresh-install path

| Step | Command | Outcome |
|---|---|---|
| Clean DB + migrate | `DATABASE_URL=…/fresh.db alembic upgrade head` | 2 migrations, clean |
| Start backend | `uvicorn aegis_app.main:app --port 8020` (`SEED_DEMO_DATA=false`) | `/health` = healthy |
| Start frontend | `VITE_API_BASE=…:8020 npx vite` | serves, hot-reloads |
| Sign up (founder) | `POST /auth/signup` | 200, token, role=Tenant Admin |
| Register AI system | `POST /ai-systems` | 200 |
| Applicability | `POST /ai-systems/intake-evaluate` | 200, `High Risk` for EU+credit, `rules_fired` populated |
| Model / Agent / Vendor | `POST /models` `/agents` `/vendors` | 200 each |
| Risk | `POST /risks` | 200 |
| Assessment | `POST /assessments {framework_id: eu_ai_act}` | 200, **419 requirements** from `regulatory:2024/1689` |
| Assessment detail | `GET /assessments/{id}` | 200, 419 response items, each with `source_text` |
| Evidence (metadata) | `POST /evidence` | 200, SHA-256 stored |
| Dashboard | `GET /dashboard/metrics` | numbers match DB |
| Executive report | `GET /reports/executive` | 200 |

**No database or source-code edits were needed to complete this path** — except
that regulatory content must first be ingested (`python -m aegis_app.regulatory.ingest --all`,
~4 min, one-time admin step). A fresh DB with no ingestion serves the 17-framework
catalog but 0 requirements.

## 2. Assessment engine — real requirement sets (spec §27 / §35 / §50)

`POST /assessments` against a running instance with regulatory content ingested:

| framework_id | requirement_count | source |
|---|---:|---|
| eu_ai_act | **419** | `regulatory:2024/1689` |
| gdpr | 238 | `regulatory:2016/679` |
| nist_ai_rmf | 72 | `regulatory:1.0` |
| mitre_atlas | 197 | `regulatory:2026.08` |
| owasp_llm | 10 | `regulatory:2026` |
| nist_sp_800_53 | **1,014** | `regulatory:Rev 5 (5.2.0)` |

Each `GET /assessments/{id}` response item carries `requirement_id` (stable key),
`normalized_requirement`, verbatim `source_text`, `obligation_type`, and
`official_url`. Regression: `test_assessment_uses_ingested_regulatory_requirements`.

## 3. Workflow state machines (pytest `test_workflows.py`, 3 tests)

- Evidence: Draft → Submitted → Under Review → Accepted, reviewer ≠ uploader enforced.
- Risk: create → accept (authorised role) → status change + audit event.
- Applicability decision: create → `LEGAL_REVIEW_REQUIRED` → reviewer accept/modify;
  the rule engine's own output cannot self-approve.

## 4. Traceability (spec §79 / §80)

**Regulation → requirement → source** verified live:
`GET /regulatory/requirements/EU-AIA-ARTICLE-9-1` →
`source_reference: "Article 9(1)"`, `source_text` (verbatim), `normalized_requirement`
(separate field), `official_source.sha256` = `26e478105fd5cd87…` (= SHA-256 of the
operator's `EU AI Act.docx`), `official_url` → EUR-Lex CELEX.

**Requirement → assessment item** verified: assessment response `EU-AIA-ARTICLE-9-1`
resolves to the same source text in `GET /assessments/{id}`.

**Not yet traceable end-to-end:** requirement → Unified Control → Customer Control →
Evidence → Finding. The `regulatory_requirement_control_maps` table exists but has
**0 rows** — control mapping of the ingested requirements has not been done.

## 5. Frontend

Playwright, logged in, clicked all 12 sidebar items:
`Executive Dashboard, AI Systems Inventory, Unified Controls, 17-Framework
Crosswalk, Authoritative Frameworks, Assessments & Readiness, Evidence Vault,
Risk Register & Heatmap, Executive Reports, Tamper-Evident Audit, AI Security &
Agents, Settings & RBAC`.

- **0 crashes, 0 uncaught console errors.**
- Frameworks tab renders the 16 ingested frameworks with real requirement counts;
  clicking a card opens the framework detail (structural breakdown + source hash),
  clicking a requirement shows official source text vs platform interpretation +
  evidence expectations + citation.
- **Dead areas (not dead buttons — placeholder text):** Assessments tab has no
  "create assessment" control; Evidence upload UI works but Shadow AI / Runtime
  Governance / Policies / Evaluations / Integrations / Vendor Portal / Auditor
  Portal tabs **do not exist** in the nav.

## 6. Business scenario (spec §77) — partial

`GLOBALBANK` multi-system scenario partially executed: 5 systems registered,
applicability run for each (results differ — see `VALIDATION_REPORT.md` §4),
assessments created against real requirements. **Not executed:** evidence per
system, control testing, findings→remediation→approval→report chain per system,
auditor review (no auditor portal), continuous monitoring (no monitor job).

## Verdict

**Core customer path (signup → inventory → applicability → assessment against the
real requirement set → evidence → risk → report) works over HTTP with no manual
DB edits.** The chain breaks at control mapping (0 mappings) and at the
downstream personas/automation that are not implemented.
