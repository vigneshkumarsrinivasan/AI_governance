# Source Inventory — `project\AI governance`

_Generated 2026-09-08 by final enterprise validation. Recursive scan, original files not modified._

## Part 1 — Regulatory / framework source documents

All 15 primary source documents live in the repo root. SHA-256 truncated to 16 chars for readability; full hashes in `regulatory-data/manifests/regulatory-source-manifest.yaml` and the DB `regulatory_source_artifacts` table.

| # | source_file | type | size (B) | SHA-256 (16) | detected_framework | authority | jurisdiction | version | source_type | parser | ingestion_status (DB) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | EU AI Act.docx | docx | 251,086 | 26e478105fd5cd87 | eu_ai_act | EU Parliament & Council | EU | 2024/1689 | Regulation | eu_docx | INGESTED · DRAFT |
| 2 | GDPR.docx | docx | 153,782 | 0d3a1b2473eedab8 | gdpr | EU | EU | 2016/679 | Regulation | eu_docx | INGESTED · DRAFT |
| 3 | EU CRA.docx | docx | 145,674 | 31753cb03573a2ee | eu_cra | EU | EU | 2024/2847 | Regulation | eu_docx | INGESTED · DRAFT |
| 4 | NIS2.docx | docx | 138,045 | 98086ae2ee03608d | nis2 | EU | EU | 2022/2555 | Directive | eu_docx | INGESTED · DRAFT |
| 5 | DORA.docx | docx | 143,706 | 4e8af0689a9f0693 | dora | EU | EU | 2022/2554 | Regulation | eu_docx | INGESTED · DRAFT |
| 6 | NIST.AI.100-1.pdf | pdf | 1,946,127 | 7576edb531d98488 | nist_ai_rmf | NIST | US (voluntary) | 1.0 | Framework | nist_ai_rmf_pdf | INGESTED · DRAFT |
| 7 | NIST.AI.600-1.pdf | pdf | 1,174,643 | 6e73620ab6b64e90 | nist_ai_600_1 | NIST | US (voluntary) | 600-1 (2024) | Profile | nist_ai_600_1_pdf | INGESTED · DRAFT |
| 8 | NIST.CSWP.29.pdf | pdf | 1,518,858 | 3c31f46fee98cac0 | nist_csf_2 | NIST | US (voluntary) | 2.0 | Framework | nist_csf | INGESTED · DRAFT |
| 9 | NIST.SP.800-218.pdf | pdf | 739,891 | 617746e553a9e2da | nist_sp_800_218 | NIST | US (voluntary) | 1.1 | SP | nist_ssdf | INGESTED · DRAFT |
| 10 | NIST.SP.800-218A.pdf | pdf | 650,661 | e088c8bc75716824 | nist_sp_800_218a | NIST | US (voluntary) | — | SP | **none (null in manifest)** | **NOT IMPORTED** |
| 11 | NIST.SP.800-161r1-upd1.pdf | pdf | 3,511,556 | d2bacbf4053adbbe | nist_sp_800_161 | NIST | US (voluntary) | Rev 1 upd1 | SP | nist_oscal | **NOT IMPORTED (metadata only; SOURCE_RETRIEVAL_BLOCKED)** |
| 12 | OWASP-GenAI-LLM-Top-10-2026-v1.0.pdf | pdf | 2,402,520 | ef87993a4e50ae9d | owasp_llm | OWASP | International | 2026 v1.0 | Community standard | owasp_pdf | INGESTED · DRAFT (also a 2025 version present; both flat, 10 items, no sub-structure) |
| 13 | OWASP-Top-10-for-Agentic-Applications-2026-12.6-1.pdf | pdf | 1,274,186 | a2db94cd00b08e0b | owasp_agentic_ai | OWASP | International | 2026 (12.6) | Community standard | owasp_pdf | INGESTED · DRAFT (10 items only) |
| 14 | Implementation_Guide_for_the_AI_Cyber_Security_Code_of_Practice.pdf | pdf | 1,011,888 | 5d4c961cc811dc67 | uk_ai_cyber_code | UK DSIT | UK (voluntary) | 2025-01 | Code of practice | uk_pdf | INGESTED · DRAFT |
| 15 | DPDP_Rules_2025_English_only.pdf | pdf | 375,007 | 63bc7ca508ae4ebb | india_dpdp | Government of India (MeitY) | India | Rules 2025 | Subordinate legislation | dpdp_pdf | INGESTED · DRAFT (Rules only — **Act 2023 text not supplied**) |

### Frameworks in the DB with NO local source file (ingested from official online repos)

| framework | DB version(s) | source of record | notes |
|---|---|---|---|
| mitre_atlas | 5.6.0 **and** 2026.08 | `github.com/mitre-atlas/atlas-data` (YAML archived under `regulatory/sources_archive/mitre_atlas/`) | two versions ingested; duplicate — neither is_current |
| nist_sp_800_53 | Rev 5 (5.2.0) | NIST OSCAL JSON (archived) | 1,014 controls ingested |
| singapore_ai_verify | v2.2.0 | AI Verify Foundation (JSON archived) | licence `CUSTOMER_LICENCE_REQUIRED` in one source row |

## Part 1 — Non-regulatory files found (classified, not regulatory sources)

| file | classification |
|---|---|
| `backend/aegis_app/data/frameworks/*.json` (17) | **LEGACY DEMO CONTENT** — hand-authored, ~2–10 sample requirements each. This is what the UI/reports/Copilot read. |
| `backend/aegis_app/data/{unified_controls,crosswalk_mappings,applicability_rules}.json` | legacy demo control library / crosswalk / applicability (not derived from ingested sources) |
| `backend/aegis_app/regulatory/framework_manifest.yaml` | ingestion manifest (config) |
| `backend/aegis_app/regulatory/sources_archive/**` | retained copies of retrieved sources (hash-named) — OK |
| `backend/aegis_app/regulatory/fixtures/`, `backend/tests/fixtures/` | test fixtures |
| `regulatory-data/manifests/regulatory-source-manifest.yaml` | generated reconciliation manifest |
| `backend/tests/test_evidence_storage/**` (60 files) | pytest evidence-storage artifacts (should be git-ignored) |
| `web-ui/**` | **abandoned second frontend** (Vite). Not built, not served. `frontend/` (Next.js) is the live UI. |
| `*_REPORT.md`, `PRODUCTION_READINESS*.md`, `REGULATORY_CONTENT_STATUS.md` | prior status reports (per instruction: not trusted; superseded by this run) |
| `docker-compose.yml`, `.github/workflows/ci.yml`, `Dockerfile`s | infra/CI |

**UNIDENTIFIED_SOURCE: none.** Every file is accounted for.
