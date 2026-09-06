> **Superseded by [`COMPLIANCE_PLATFORM_VALIDATION_REPORT.md`](COMPLIANCE_PLATFORM_VALIDATION_REPORT.md)**
> (2026-09-06) — 16/17 frameworks now ingested from the operator-supplied documents
> + MITRE ATLAS/AI Verify repos. This file is the earlier (6-framework) status.

# Regulatory Content — Production Readiness Report

_Generated 2026-09-05. Re-runnable: `cd backend && python -m aegis_app.regulatory.ingest --all && python -m aegis_app.regulatory.ingest --report`._

This report replaces the previous hand-authored framework JSON files
(`backend/aegis_app/data/frameworks/*.json`, ~63 "representative" requirements
across 17 frameworks, no source retrieval, no hashes, no licence tracking) with
a **source-traceable ingestion pipeline** and its output.

Nothing below is marked `PRODUCTION_READY`. Per the build spec that gate requires
100% human requirement verification, ≥80% reviewed unified-control mapping, and
reviewed applicability rules — none of which a machine pass can satisfy on its
own. Frameworks that are structurally complete, source-hashed, licence-verified
and pass every CRITICAL/ERROR validation check are marked `VALIDATED`.

---

## 0. What was built (P0 foundation)

| Component | Location |
|---|---|
| Regulatory data model (10 tables, versioned, immutable-on-publish) | `backend/aegis_app/models/regulatory.py` |
| Alembic migration | `backend/alembic/versions/36606e944171_regulatory_content_ingestion_tables.py` |
| Canonical source + licence manifest (all 17) | `backend/aegis_app/regulatory/framework_manifest.yaml` |
| Retrieval (host allowlist, 60 MB cap, no redirects off-allowlist, no execution) | `backend/aegis_app/regulatory/fetch.py` |
| Parsers (ATLAS, OSCAL, OWASP-MD, NIST-CPRT, AI-RMF) | `backend/aegis_app/regulatory/parsers/` |
| Pipeline: fetch → archive → hash → parse → persist → validate → change-detect | `backend/aegis_app/regulatory/pipeline.py` |
| 3-layer validation engine (SOURCE / SEMANTIC / COMPLIANCE) | `backend/aegis_app/regulatory/validate.py` |
| Readiness reporting | `backend/aegis_app/regulatory/report.py` |
| Read + admin API (`/api/v1/regulatory/*`) | `backend/aegis_app/api/regulatory.py` |
| Tests (offline, fixture-backed) | `backend/tests/test_regulatory_ingestion.py` (10 tests) |
| Archived original sources (SHA-256 named) | `backend/aegis_app/regulatory/sources_archive/` |

**Guarantees enforced in code**

- Official source text is stored in a separate column from platform interpretation and is **only** persisted when the manifest licence status permits redistribution (`VERIFIED_*`). `UNKNOWN` / `CUSTOMER_LICENCE_REQUIRED` → metadata only, no provision text (spec §3, §10, §85).
- Every node/requirement carries a `source_anchor_url`, `source_hash`, and links to a `SourceArtifact` with retrieval URL, timestamp, HTTP metadata and SHA-256 (spec §5, §34, §35).
- `expected_counts` are **derived from the authoritative source structure** by the parser, then reconciled against ingested counts as a CRITICAL check (spec §5, §39).
- Published framework versions are immutable; re-ingestion of a `PUBLISHED` version is refused; source-hash changes raise a `SourceChangeEvent` and never auto-publish (spec §35, §36, §59).

---

## 1. Summary

| | Count |
|---|---:|
| Frameworks in manifest | 17 |
| Ingested from authoritative machine-readable source this pass | **6** |
| `VALIDATED` (structurally complete, hashed, licence-verified, all CRITICAL/ERROR checks pass) | 5 |
| `PARTIAL` (ingested, gap identified & flagged) | 1 |
| `PRODUCTION_READY` | 0 |
| Blocked / not yet ingested (metadata + source pointer stored) | 11 |
| Licence status `UNKNOWN` (provision text withheld by design) | 1 (India DPDP) |
| Total normalized, source-linked requirements ingested | **1,361** |

---

## 2. Per-framework status

### Ingested this pass

| Framework | Version | Source (SHA-256 prefix) | Licence | Reqs | Nodes | Src cov. | Hierarchy cov. | Status |
|---|---|---|---|---:|---:|---:|---:|---|
| **MITRE ATLAS** | 5.6.0 | `dist/ATLAS.yaml` `c9c23971…` | Apache-2.0 (attribution) | 170 | 279 | 100% | 100% | VALIDATED |
| **NIST SP 800-53** | Rev 5 (5.2.0) | OSCAL catalog `01f37cf9…` | US Gov / public domain | 1014 | 1217 | 100% | 100% | VALIDATED |
| **NIST CSF 2.0** | 2.0 | CPRT graph `4bc765ff…` | US Gov / public domain | 106 | 498 | 100% | 100% | VALIDATED |
| **NIST SP 800-218 (SSDF)** | 1.1 | CPRT graph `d6cc11da…` | US Gov / public domain | 42 | 264 | 100% | 100% | VALIDATED |
| **OWASP Top 10 for LLM** | 2025 | GenAI-Security-Project repo `28fd7435…` | CC BY-SA 4.0 | 10 | 11 | 100% | 100% | VALIDATED |
| **NIST AI RMF** | 1.0 | committed fixture `7b68feaa…` | US Gov / public domain | 19 | 96 | n/a¹ | 100% | PARTIAL |

Source-derived vs ingested structural counts reconcile exactly for all six:
- ATLAS — 16 tactics / 101 techniques / 69 sub-techniques / 35 mitigations / 57 case studies
- 800-53 — 20 families / 324 base controls / 872 enhancements (1,196 total)
- CSF 2.0 — 6 functions / 22 categories / 106 subcategories
- SSDF — 4 practice groups / 19 practices / 42 tasks
- OWASP LLM — 10 risk entries (LLM01–LLM10)

¹ **AI RMF is `PARTIAL` on purpose.** There is no official machine-readable
release of AI RMF 1.0. The committed fixture holds the 4 functions, 19 category
outcome statements (verbatim from NIST AI 100-1 Appendix A) and all 72
subcategory identifiers, but **subcategory normative text is not reproduced**.
The validation check `official_source_text_complete` correctly FAILs, capping
the pack below `VALIDATED`.

### Not yet ingested — blocked, with the exact source required

| Framework | Licence status | Blocker | Required authoritative source |
|---|---|---|---|
| EU AI Act (2024/1689) | VERIFIED_WITH_ATTRIBUTION | EUR-Lex Formex/Akoma-Ntoso XML parser + Art. 3 definitions + role engine + phased temporal engine not yet built | `eur-lex.europa.eu/legal-content/EN/TXT/XML/?uri=CELEX:32024R1689` |
| GDPR (2016/679) | VERIFIED_WITH_ATTRIBUTION | shared `eu_lex` parser | `…CELEX:32016R0679` |
| EU CRA (2024/2847) | VERIFIED_WITH_ATTRIBUTION | shared `eu_lex` parser + Annex I essential-requirements extraction | `…CELEX:32024R2847` |
| NIS2 (2022/2555) | VERIFIED_WITH_ATTRIBUTION | shared `eu_lex` parser; EU baseline only (per-Member-State transposition packs later) | `…CELEX:32022L2555` |
| DORA (2022/2554) | VERIFIED_WITH_ATTRIBUTION | shared `eu_lex` parser; L1 only, RTS/ITS ingested separately later | `…CELEX:32022R2554` |
| NIST AI 600-1 (GenAI Profile) | VERIFIED_REUSABLE | PDF-only; structured extraction of ~12 risk categories + ~200 suggested actions + AI RMF cross-refs | `nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf` |
| OWASP Agentic AI | VERIFIED_SHARE_ALIKE | PDF-only; no stable machine-readable artefact | `genai.owasp.org/resource/agentic-ai-threats-and-mitigations/` |
| NIST SP 800-161r1 | VERIFIED_REUSABLE | express as an overlay/profile of 800-53 (cross-reference, don't duplicate controls) | `csrc.nist.gov` OSCAL / `csrc.nist.gov/pubs/sp/800/161/r1/final` |
| UK AI Cyber Security Code of Practice | VERIFIED_WITH_ATTRIBUTION (OGL v3.0) | GOV.UK HTML parser for 13 principles × 5 lifecycle phases | `gov.uk/government/publications/ai-cyber-security-code-of-practice` |
| India DPDP Act + Rules | **UNKNOWN** | **licence review required before any provision text may be reproduced**; metadata only until then | `meity.gov.in` / Gazette of India |
| Singapore AI Verify | CUSTOMER_LICENCE_REQUIRED | separate the Apache-2.0 toolkit from the testing-framework / Model AI Governance Framework text; confirm reuse terms for non-software content | `aiverifyfoundation.sg` / `github.com/aiverify-foundation/aiverify` |

For every blocked framework a `RegulatorySource` row with authority, official
URL, canonical identifier and licence determination **is** stored, so the
`/regulatory/licenses` page and catalog are complete for all 17.

---

## 3. What every ingested framework still needs to reach PRODUCTION_READY

These are the same blockers for all six (they are genuine human/analyst work, not
code gaps):

1. **Human requirement verification** — requirements are `MACHINE_EXTRACTED`; the release gate requires each scoring requirement to reach `VERIFIED` via the review queue.
2. **Unified-control mapping** — 0 mappings today; the `RequirementControlMapping` table + AI-proposed→review→approve workflow exist, but no mappings have been proposed/approved. Gate: ≥80% of requirements with an `APPROVED` mapping.
3. **Applicability rules** — 0 rules; `ApplicabilityRule` table exists. Each framework needs explainable scope rules (jurisdiction / role / use-case → applies?) reviewed by a person.
4. **Evidence expectations** — auto-generated from source (mitigations / implementation examples / assessment objectives); present on 100% of requirements but not analyst-reviewed.
5. **Assessment + report generation** against the new tables — the existing `Assessment`/`AssessmentResponse` flow still points at the legacy framework JSON; it must be switched to `regulatory_requirements`.
6. **Copilot RAG** — retrieval must be pointed at `regulatory_*` tables with citations (spec §66–68).
7. **Legacy JSON retirement** — `backend/aegis_app/data/frameworks/*.json` and `services/crosswalk.py` still serve the old `/frameworks` endpoints; retire per-framework as each real pack is wired into assessments.
8. **Live source monitoring job** — `SourceChangeEvent` is raised on hash change during ingestion; a scheduled re-check job (spec §69) is not yet wired.
9. **AI RMF specifically** — obtain a verified full-text source (or reviewed transcription) for the 72 subcategories.

---

## 4. API surface (all under `/api/v1/regulatory`, auth required; admin RBAC-gated)

```
GET  /frameworks                      catalog + per-framework production status
GET  /frameworks/{key}                detail: version, source hash, licence, coverage, top nodes
GET  /frameworks/{key}/tree           full original hierarchy
GET  /frameworks/{key}/requirements   normalized requirements
GET  /requirements/{requirement_key}  requirement + clickable official source citation
GET  /frameworks/{key}/validation     latest 3-layer validation run
GET  /frameworks/{key}/coverage       coverage fractions (NOT a compliance score)
GET  /licenses                        licence + attribution for every source (all 17)
GET  /readiness-report                this report as JSON
GET  /search?q=                       full-text over nodes + requirements
POST /admin/ingest/{key}              run the pipeline           (governance-write)
POST /admin/frameworks/{key}/validate re-run validation          (governance-write)
POST /admin/frameworks/{key}/publish  publish (refused unless PRODUCTION_READY or ?force) (governance-write)
GET  /admin/source-changes            open REGULATORY_SOURCE_CHANGE_DETECTED events (governance-write)
```

---

## 5. Test coverage

`backend/tests/test_regulatory_ingestion.py` (10 tests, fully offline):
manifest validation; licence gate blocks `UNKNOWN`/`CUSTOMER_LICENCE_REQUIRED`
reproduction; ATLAS + OSCAL + AI-RMF parsers against committed trimmed real
sources; full pipeline ingest + 3-layer validation of AI RMF; `PUBLISHED`
immutability; blocked-framework metadata-only path; catalog / licence /
readiness API + auth enforcement. Full suite: **38 passed**.

Live-source retrieval is intentionally **not** in CI — it belongs in a separate
network-gated job so CI stays deterministic while a monitor still checks live
sources (spec §83).
