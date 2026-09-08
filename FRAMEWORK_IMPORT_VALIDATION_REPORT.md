# FRAMEWORK IMPORT VALIDATION REPORT

_Final enterprise validation — 2026-09-08. Evidence: live SQLite DB (`backend/aegis_ai.db`), live API on `:8010`, live Next.js UI on `:3001`, `pytest` (41 tests), source-file hashes. Prior status reports were **not** trusted._

## Executive finding

The platform contains **two disconnected content systems**:

1. **Regulatory ingestion subsystem** (`aegis_app/regulatory`, `regulatory_*` tables) — 16 frameworks / 18 versions, **3,211 source-traceable requirements**, deep hierarchy (7,970 nodes), 251 definitions, full source text, licence-checked, structurally validated. **This is real and good work.** But every version is `published_status = DRAFT`, `is_current = 0`, **0 % human-verified, 0 control mappings, 0 applicability rules**, and it is **not consumed by the UI, reports, Copilot, or crosswalk**.
2. **Legacy demo JSON** (`aegis_app/data/frameworks/*.json`) — 17 files, ~2–10 hand-authored sample requirements each. **This is what the UI `/frameworks`, `/reports/executive`, `/copilot`, `/crosswalk`, and `/controls` actually serve.** e.g. the UI shows "EU AI Act" with **10** requirements; the real ingested EU AI Act has **419**.

A framework name appearing in the UI therefore does **not** mean the real regulation is usable. It means a ~10-row placeholder file exists.

## Per-framework matrix

Legend: ✅ done · ⚠️ partial · ❌ absent · `n/a`. "Reqs (real)" = `regulatory_requirements` rows. "Reqs (UI)" = requirements served by legacy `/frameworks`.

| Framework | Source file(s) | Ver (DB) | Expected structure | Imported structure | Reqs (real) | Reqs (UI) | Src-text | Human-verified | Controls mapped | Applicability | Assessment | UI page | Reports | Copilot | Validation status | STATUS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EU AI Act | EU AI Act.docx | 2024/1689 | 113 art, 13 ch, 13 annex, 180 rec | 113 art, 13 ch, 13 annex, 180 rec, 68 def, 500 para, 352 pt | 419 | 10 | ✅ 419/419 | ❌ 0 % | ❌ 0 | ❌ 0 | ⚠️ backend only (uncommitted) | ❌ no assessment UI | ⚠️ legacy only | ⚠️ legacy only | VALIDATED (struct) / FAIL (compliance layer) | **PARTIAL** |
| GDPR | GDPR.docx | 2016/679 | 99 art, 11 ch, 173 rec | 1,038 nodes, depth 4 | 238 | 3 | ✅ | ❌ 0 % | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| EU CRA | EU CRA.docx | 2024/2847 | 71 art, annexes | 749 nodes, depth 4 | 238 | 3 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| NIS2 | NIS2.docx | 2022/2555 | 46 art | 638 nodes, depth 4 | 143 | 2 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| DORA | DORA.docx | 2022/2554 | 64 art | 819 nodes, depth 4 | 146 | 2 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| NIST AI RMF 1.0 | NIST.AI.100-1.pdf | 1.0 | GOVERN/MAP/MEASURE/MANAGE + subcats | 96 nodes, 72 reqs, depth 3 | 72 | 8 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| NIST AI 600-1 (GenAI) | NIST.AI.600-1.pdf | 600-1 (2024) | 12 GenAI risks + actions | 234 nodes, 212 reqs | 212 | 4 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| NIST CSF 2.0 | NIST.CSWP.29.pdf | 2.0 | 6 functions, 22 cat, 106 subcat | 498 nodes, 106 reqs, depth 4 | 106 | 4 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| NIST SSDF 800-218 | NIST.SP.800-218.pdf | 1.1 | PO/PS/PW/RV, 19 practices, 42 tasks | 264 nodes, 42 reqs, depth 4 | 42 | 2 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| NIST SSDF 800-218A | NIST.SP.800-218A.pdf | — | AI-model SSDF augmentations | **nothing** | 0 | 0 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **no run** | **NOT_IMPORTED** |
| NIST SP 800-161r1 | NIST.SP.800-161r1-upd1.pdf | Rev 1 | C-SCRM controls + enhancements | **metadata row only** | 0 | 1 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ legacy stub | ⚠️ legacy stub | **BLOCKED** (parser=nist_oscal, `SOURCE_RETRIEVAL_BLOCKED`) | **NOT_IMPORTED / PARSER_FAILED** |
| NIST SP 800-53 Rev 5 | (OSCAL, no local file) | 5.2.0 | 20 families, 1000+ controls + enh | 1,217 nodes, 1,014 reqs | 1,014 | 2 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| OWASP LLM Top 10 | OWASP-GenAI-LLM-Top-10-2026-v1.0.pdf | 2026 (+2025) | 10 risks + mitigations + scenarios | 11 nodes (flat), 10 reqs, **no sub-structure** | 10 (×2 ver) | 6 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| OWASP Agentic Top 10 | OWASP-Top-10-for-Agentic-Applications-2026-12.6-1.pdf | 2026 | 10 threats + mitigations | 11 nodes (flat), 10 reqs | 10 | 4 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| UK AI Cyber Security Code | Implementation_Guide...pdf | 2025-01 | 13 principles across lifecycle | 60 nodes, 46 reqs, depth 2 | 46 | 2 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL** |
| India DPDP | DPDP_Rules_2025_English_only.pdf | Rules 2025 | Act 2023 + Rules 2025 + schedules | 152 nodes, 41 reqs (Rules only) | 41 | 2 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL — Act text missing** |
| MITRE ATLAS | official repo (no local file) | 5.6.0 **and** 2026.08 | tactics/techniques/mitigations/case studies | 279 + 325 nodes, 170 + 197 reqs | 367 | 3 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL | **PARTIAL — duplicate versions, not classified as non-legislation in UI** |
| Singapore AI Verify | official repo (no local file) | v2.2.0 | testing framework + process checks | 182 nodes, 97 reqs, depth 3 | 97 | 2 | ✅ | ❌ | ❌ 0 | ❌ 0 | ⚠️ backend only | ❌ | ⚠️ legacy | ⚠️ legacy | VALIDATED / FAIL; licence `CUSTOMER_LICENCE_REQUIRED` on one source row | **PARTIAL** |

## Part 3 — Cross-surface reconciliation

| Surface | Frameworks exposed | Content system used |
|---|---|---|
| DB `regulatory_framework_versions` | 16 (18 versions) | real ingestion |
| API `/api/v1/regulatory/frameworks` | 16 | real ingestion (DRAFT) |
| API `/api/v1/frameworks` (legacy) | 17 | **demo JSON** |
| UI "Authoritative Frameworks" page | 17 | **demo JSON** (calls `/frameworks`) |
| Assessment engine (`crosswalk_service`) | 17 | **demo JSON** — except uncommitted `assessments.py` change now prefers real reqs at create-time |
| Reports (`/reports/executive`) | 17 summary | **demo JSON** |
| Governance Copilot | 17 | **demo JSON** + live tenant data (deterministic rules) |
| Crosswalk matrix | 17 | **demo JSON** `crosswalk_mappings.json` |
| Applicability engine | `regulatory_applicability_rules` = **0 rows**; `applicability_decisions` = **0 rows**; legacy `applicability_rules.json` only |

## Part 71 summary table

| | Count |
|---|---|
| Source documents discovered | 15 local + 3 online-only families = **18 framework families** |
| Fully production-validated (source→import→verified→mapped→applicability→assessment→UI→report→Copilot→tested) | **0** |
| Ingested + structurally validated, but DRAFT and not wired downstream | **16** |
| Not imported | **2** (800-218A, 800-161) |
| Frameworks with 0 control mappings | **16 / 16** |
| Frameworks with 0 applicability rules | **16 / 16** |
| Frameworks with 0 human-verified requirements | **16 / 16** |
| Frameworks with an assessment UI | **0** |
| Duplicate imports | MITRE ATLAS (5.6.0 + 2026.08), OWASP LLM (2025 + 2026) — none marked current |
