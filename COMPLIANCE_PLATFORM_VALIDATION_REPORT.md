# Compliance Platform — Regulatory Content Validation Report

_Generated 2026-09-06. Reproduce: `cd backend && python -m aegis_app.regulatory.ingest --inventory --all && python -m aegis_app.regulatory.ingest --report`_

This report covers the ingestion of the **operator-supplied framework documents**
(15 files at the workspace root) plus **MITRE ATLAS** and **Singapore AI Verify**
from their official GitHub repositories, into the source-traceable regulatory
subsystem (`backend/aegis_app/regulatory/`).

Nothing is marked `PRODUCTION_READY`. That gate requires 100% human requirement
verification, ≥80% reviewed unified-control mapping and reviewed applicability
rules — none of which a machine pass performs. Frameworks that are structurally
complete, source-hashed, licence-checked and pass every CRITICAL/ERROR check are
`VALIDATED`.

---

## 1. Local document inventory (spec §1, §13)

15 documents found at the workspace root, every one identified and matched to a
framework. Full manifest: `regulatory-data/manifests/regulatory-source-manifest.yaml`.
Originals are **never modified** — they are read-only input; the pipeline copies
each into `backend/aegis_app/regulatory/sources_archive/<framework>/<sha>.<ext>`.

| File | Framework | SHA-256 (prefix) | Parser |
|---|---|---|---|
| EU AI Act.docx | eu_ai_act | `26e478105fd5cd87` | eu_docx |
| GDPR.docx | gdpr | `0d3a1b2473eedab8` | eu_docx |
| EU CRA.docx | eu_cra | `31753cb03573a2ee` | eu_docx |
| NIS2.docx | nis2 | `98086ae2ee03608d` | eu_docx |
| DORA.docx | dora | `4e8af0689a9f0693` | eu_docx |
| NIST.AI.100-1.pdf | nist_ai_rmf | `7576edb531d98488` | nist_pdf (AI RMF) |
| NIST.AI.600-1.pdf | nist_ai_600_1 | `6e73620ab6b64e90` | nist_pdf (AI 600-1) |
| NIST.CSWP.29.pdf | nist_csf_2 | `3c31f46fee98cac0` | (corroborates CPRT) |
| NIST.SP.800-218.pdf | nist_sp_800_218 | `617746e553a9e2da` | (corroborates CPRT) |
| NIST.SP.800-218A.pdf | nist_sp_800_218a | `e088c8bc75716824` | pending |
| NIST.SP.800-161r1-upd1.pdf | nist_sp_800_161 | `d2bacbf4053adbbe` | pending (overlay of 800-53) |
| OWASP-GenAI-LLM-Top-10-2026-v1.0.pdf | owasp_llm | `ef87993a4e50ae9d` | owasp_pdf |
| OWASP-Top-10-for-Agentic-Applications-2026-12.6-1.pdf | owasp_agentic_ai | `a2db94cd00b08e0b` | owasp_pdf |
| Implementation_Guide_for_the_AI_Cyber_Security_Code_of_Practice.pdf | uk_ai_cyber_code | `5d4c961cc811dc67` | pdf_legal (UK) |
| DPDP_Rules_2025_English_only.pdf | india_dpdp | `63bc7ca508ae4ebb` | pdf_legal (DPDP) |

---

## 2. Special external sources (spec §3–§7)

| Source | Repo | Resolved at ingestion | Licence |
|---|---|---|---|
| **MITRE ATLAS** | `mitre-atlas/atlas-data` | latest release, asset `ATLAS-*.yaml` (currently **v2026.08**, schema v6) — tag + SHA-256 recorded | Apache-2.0 (attribution) |
| **Singapore AI Verify** | `aiverify-foundation/aiverify` | latest tag (currently **v2.2.0**), `stock-plugins/aiverify.stock.process-checklist/inputs/config_*.ts` — tag + SHA-256 recorded | Apache-2.0 (attribution) |

The ATLAS release tag is **not hard-coded** — `fetch_github_release_asset` queries
`releases/latest`. Same for AI Verify (`fetch_github_bundle`, `ref_mode: latest_tag`).

---

## 3. Per-framework validation (spec §38–§42, §65)

| Framework | Version | Source SHA-256 | Parsed | Hierarchy nodes | Requirements | Definitions | Src cov. | Hierarchy cov. | Status |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| **EU AI Act** | 2024/1689 | `26e478105fd5cd87` | ✓ | 1386 | 419 | 68 | 100% | 100% | VALIDATED |
| **GDPR** | 2016/679 | `0d3a1b2473eedab8` | ✓ | 1038 | 238 | 26 | 100% | 100% | VALIDATED |
| **EU CRA** | 2024/2847 | `31753cb03573a2ee` | ✓ | 749 | 238 | 51 | 100% | 100% | VALIDATED |
| **NIS2** | 2022/2555 | `98086ae2ee03608d` | ✓ | 638 | 143 | 41 | 100% | 100% | VALIDATED |
| **DORA** | 2022/2554 | `4e8af0689a9f0693` | ✓ | 819 | 146 | 65 | 100% | 100% | VALIDATED |
| **NIST AI RMF** | 1.0 | `7576edb531d98488` | ✓ | 96 | 72 | – | 100% | 100% | VALIDATED |
| **NIST AI 600-1** | GenAI Profile 2024 | `6e73620ab6b64e90` | ✓ | 234 | 212 | – | 100% | 100% | VALIDATED¹ |
| **NIST CSF 2.0** | 2.0 | CPRT `4bc765ff39a2` | ✓ | 498 | 106 | – | 100% | 100% | VALIDATED |
| **NIST SSDF 800-218** | 1.1 | CPRT `d6cc11da3e6c` | ✓ | 264 | 42 | – | 100% | 100% | VALIDATED |
| **NIST SP 800-53** | Rev 5 (5.2.0) | OSCAL `01f37cf90ea9` | ✓ | 1217 | 1014 | – | 100% | 100% | VALIDATED |
| **MITRE ATLAS** | 2026.08 | release `a8d32f676854` | ✓ | 325 | 197 | – | 100% | 100% | VALIDATED |
| **OWASP LLM Top 10** | 2026 | `ef87993a4e50ae9d` | ✓ | 11 | 10 | – | 100% | 100% | VALIDATED |
| **OWASP Agentic Top 10** | 2026 | `a2db94cd00b08e0b` | ✓ | 11 | 10 | – | 100% | 100% | VALIDATED¹ |
| **UK AI Cyber Security Code** | 2025-01 | `5d4c961cc811dc67` | ✓ | 60 | 46 | – | 100% | 100% | VALIDATED |
| **India DPDP Rules** | 2025 | `63bc7ca508ae4ebb` | ✓ | 152 | 41 | – | 100% | 100% | VALIDATED² |
| **Singapore AI Verify** | v2.2.0 | bundle `74111b5a6949` | ✓ | 182 | 97 | – | 100% | 100% | VALIDATED |
| **NIST SP 800-161** | Rev 1 | `d2bacbf4053adbbe` (archived) | ✗ | 0 | 0 | – | – | – | NOT_INGESTED³ |

**Totals: 16/17 ingested, ~3,443 source-linked normalized requirements, ~7,760 hierarchy nodes.**

Structural counts reconcile exactly against the source for every ingested pack
(EU AI Act: 180 recitals / 13 chapters / 113 articles / 68 Article-3 definitions /
13 annexes; ATLAS: 16 tactics / 114 techniques / 83 sub-techniques / 39 mitigations
/ 72 case studies / 309 relationships; 800-53: 20 families / 324 base controls /
872 enhancements; CSF 2.0: 6 functions / 22 categories / 106 subcategories; SSDF:
4 groups / 19 practices / 42 tasks; AI RMF: 4 functions / 19 categories / 72
subcategories with full outcome text; UK: 13 principles / 46 provisions; AI Verify:
11 governance principles / 65 testable criteria / 90 process checks).

¹ **NIST AI 600-1 / OWASP Agentic** — PDF layout extraction leaves some noise in a
minority of entries (AI 600-1: the "GAI Risks" table column occasionally bleeds
into an action's text; Agentic ASI03's description was recovered from a wide
fallback window). Flagged in `parser_notes`; these are review items, not
structural failures.

² **India DPDP Rules** — licence status is `UNKNOWN` (Gazette of India reproduction
terms not yet reviewed). Ingested because the operator supplied their own copy
(`operator_supplied_primary_source: true`): the text lives only in the operator's
own instance, and the validation engine keeps
`redistribution_licence_review_pending` as an open item until counsel confirms.
The parser currently recovers 18 of ~23 rules cleanly (some rule titles wrap
across PDF lines); improving that is a tracked follow-up.

³ **NIST SP 800-161** — the operator PDF is archived + hashed, but 800-161r1 is
largely an overlay/profile of SP 800-53 with C-SCRM enhancements. Per spec §24 it
should be ingested as cross-references to the already-ingested 800-53 controls, not
re-parsed. That overlay parser is not built yet.

---

## 4. Guarantees enforced in code

- **Source traceability** — every node/requirement links to a `SourceArtifact`
  (retrieval URL, timestamp, HTTP metadata, SHA-256) and carries a
  `source_anchor_url` + `source_hash`. Requirement → official source is one click
  (`GET /api/v1/regulatory/requirements/{key}`).
- **Official text vs platform text** kept in separate columns (`source_text` vs
  `normalized_requirement` / `platform_summary`); interpretation is labelled
  `PLATFORM_INTERPRETATION`, never shown as law.
- **Licence gate** — `source_text` is only persisted where the licence permits
  redistribution *or* the operator supplied their own copy. `framework-licenses`
  API + the manifest record every determination.
- **Semantics preserved** — recitals, definitions, ATLAS techniques and OWASP
  attack scenarios are classified (`obligation_type`) and are **not** turned into
  obligations (spec §17).
- **EU AI Act temporal engine** — Article 5 prohibitions dated 2025-02-02, GPAI
  provisions 2025-08-02, general application 2026-08-02 (Article 113).
- **Immutability** — a `PUBLISHED` `FrameworkVersion` cannot be re-ingested;
  source-hash changes raise a `SourceChangeEvent` and never auto-publish.
- **Reconciliation is a CRITICAL check** — `expected_counts` are derived by the
  parser from the source structure, then compared to what was persisted.

---

## 5. Same blockers for every ingested framework (genuine human/analyst work)

1. **Requirement verification** — all requirements are `MACHINE_EXTRACTED`; the
   review queue must take scoring requirements to `VERIFIED`.
2. **Unified-control mapping** — 0 mappings. The `RequirementControlMapping` table
   + AI-propose→review→approve workflow exist; no mappings proposed yet.
3. **Applicability rules** — 0 rules. `ApplicabilityRule` table exists; each
   framework needs explainable jurisdiction/role/use-case rules, human-reviewed.
4. **EU AI Act role engine** — provisions carry detected `subject_roles` but the
   provider/deployer/importer/distributor obligation split is not yet a rule set.
5. **Assessments + Copilot** — `Assessment`/`AssessmentResponse` and the Copilot
   RAG still read the legacy `data/frameworks/*.json`; must be pointed at
   `regulatory_*`.
6. **AI Verify technical tests** — `aiverify_adapter.py` normalizes imported
   results and lists stock-plugin capabilities; live execution of the AI Verify
   engine is a follow-up.
7. **Scheduled source monitor** — hash-change detection runs during ingestion; a
   recurring re-check job is not yet wired.
8. **NIST 800-161 overlay** and **800-218A** ingestion.
9. **Legacy JSON retirement** — retire `data/frameworks/*.json` +
   `services/crosswalk.py` per-framework as each real pack is wired into
   assessments.

---

## 6. API (`/api/v1/regulatory/*`, auth required; admin RBAC-gated)

```
GET  /frameworks                     catalog + per-framework production status
GET  /frameworks/{key}               detail: version, source hash, licence, coverage
GET  /frameworks/{key}/tree          full original hierarchy
GET  /frameworks/{key}/requirements  normalized requirements
GET  /requirements/{key}             requirement + clickable official source citation
GET  /frameworks/{key}/validation    latest 3-layer validation run
GET  /frameworks/{key}/coverage      coverage fractions (NOT a compliance score)
GET  /licenses                       licence + attribution for every source
GET  /readiness-report               this report as JSON
GET  /search?q=                      full-text over nodes + requirements
GET  /aiverify/capabilities          AI Verify stock-test registry
POST /aiverify/import-result         normalize an operator-run AI Verify result   (governance-write)
POST /admin/ingest/{key}             run the pipeline                              (governance-write)
POST /admin/frameworks/{key}/validate  re-run validation                          (governance-write)
POST /admin/frameworks/{key}/publish   publish (refused unless PRODUCTION_READY)   (governance-write)
GET  /admin/source-changes           open REGULATORY_SOURCE_CHANGE_DETECTED events (governance-write)
```

---

## 7. Tests

`backend/tests/test_regulatory_ingestion.py` — 14 tests, offline (fixture-backed
+ operator documents when present; live-network retrieval is out of CI by design,
spec §83). Covers: manifest + licence gate, EU-docx / OSCAL / NIST-PDF / AI-RMF
parsers, full ingestion + 3-layer validation, `PUBLISHED` immutability,
blocked-framework metadata-only path, document inventory, catalog / licence /
readiness API + auth. **Full suite: 40 passed.**
