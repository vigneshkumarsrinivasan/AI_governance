# MISSING OR UNIMPORTED SOURCES

_Final enterprise validation — 2026-09-08. Goal: zero unexplained source files._

## A. Source files present but NOT imported

| source file | framework | reason not imported | root cause | fix performed this run | remaining blocker |
|---|---|---|---|---|---|
| `NIST.SP.800-218A.pdf` | nist_sp_800_218a | No manifest entry with a parser; `manifest_parser: null`, `manifest_ingestion_status: null`. No `regulatory_sources` row, no `regulatory_ingestion_runs` row, no `regulatory_framework_versions` row. | The framework was added to `regulatory-source-manifest.yaml` `by_framework` but never wired into `framework_manifest.yaml` with a parser + expected counts. There is no `nist_ssdf_ai` / 218A parser. | **None** — writing a faithful 800-218A parser + expected-count validation set is net-new parser work that cannot be verified against source in this pass without risking fabricated structure. | Needs: manifest entry, parser (can likely extend `nist_ssdf`), expected counts from the PDF, ingestion run, validation. |
| `NIST.SP.800-161r1-upd1.pdf` | nist_sp_800_161 | `regulatory_ingestion_runs`: 3 rows, all `BLOCKED`. `manifest_ingestion_status: SOURCE_RETRIEVAL_BLOCKED`. Parser configured as `nist_oscal` (expects OSCAL JSON, not the PDF). | Manifest points the 800-161 ingestion at a machine-readable OSCAL URL that is unreachable in this environment; the local PDF is not accepted by the `nist_oscal` parser. | **None** — same reason: a PDF parser for the 800-161r1 catalogue (control families, controls, enhancements, C-SCRM relationships) is net-new and unverifiable here. | Needs: either a reachable OSCAL feed, or a PDF catalogue parser; then C-SCRM relationship mapping to vendors/models/datasets/dependencies (Part 24). |
| `DPDP Act 2023` (text) | india_dpdp | Not supplied as a file. Only `DPDP_Rules_2025_English_only.pdf` is in the folder. DB ingested 41 requirements from the Rules only. | Operator did not provide the DPDP Act 2023 consolidated text, corrigenda, or commencement/enforcement notifications. | **None** — cannot import a document that was not supplied. | Operator must supply DPDP Act 2023 + any corrigenda / S.O. commencement notifications. Part 15 cannot pass on Rules alone. |

## B. Source files imported but content INCOMPLETE / SHALLOW

| source file | framework | problem | fix performed | remaining blocker |
|---|---|---|---|---|
| `OWASP-GenAI-LLM-Top-10-2026-v1.0.pdf` | owasp_llm | Flat import: 10 risk nodes only. No child nodes for per-risk mitigations, example attack scenarios, reference CWEs. Part 25 wants it to drive tests/controls/findings — it drives none. | None | Deepen `owasp_pdf` parser to capture per-entry mitigations + scenarios as child nodes; then map to controls + evaluation suite. |
| `OWASP-Top-10-for-Agentic-Applications-2026-12.6-1.pdf` | owasp_agentic_ai | Same flat structure (10 nodes). Not integrated with Agent Registry / permissions / runtime governance (Part 26). | None | Same as above + wire to `ai_agents`. |
| MITRE ATLAS (repo) | mitre_atlas | Two versions ingested (5.6.0 and 2026.08), duplicate, neither `is_current`. Not distinguished in the UI from legislation (Part 5 forbids classifying ATLAS as legislation — legacy `/frameworks` lists it flat alongside GDPR/EU AI Act). | None | Pick one current ATLAS version; tag `framework_type` as threat-KB; wire into threat-modelling / red-team / control mapping. |

## C. Frameworks/pipelines present but NOT exposed to users

Every one of the 16 ingested frameworks is in this category. The regulatory subsystem has **no frontend route** — `grep -r "/regulatory/" frontend/src` returns only an unrelated graph endpoint. Consequences:

- `regulatory` API is reachable with a token but no screen renders it.
- Reports, Copilot, Crosswalk, Unified Controls all read `crosswalk_service` → `data/frameworks/*.json` (demo).
- Assessments: backend `create_assessment` (uncommitted change) now pre-populates from real `regulatory_requirements` when a version exists, but **there is no Assessments page in the UI** to start or complete one.

**Fix performed this run:** verified and retained the uncommitted `assessments.py` wiring + its regression test `test_assessment_uses_ingested_regulatory_requirements` (passing). Retained the uncommitted `main.py` security-headers middleware.

**Not fixed:** building the regulatory Frameworks UI, an Assessments UI, control-mapping authoring, applicability-rule authoring, Copilot/report re-pointing. These are feature builds + regulatory-analyst work, not defects fixable by an automated pass without producing unverified content.

## D. Non-source files — all explained

See `SOURCE_INVENTORY.md` §"Non-regulatory files". `web-ui/` is an abandoned second frontend and should be deleted or clearly archived. `backend/tests/test_evidence_storage/` (60 files) should be git-ignored.

## Unexplained source files: **0**
