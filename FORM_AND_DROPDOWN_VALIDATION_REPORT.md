# Form & Dropdown Validation Report

_2026-09-08. Full record for the Company form (rebuilt this pass) + an audit of the remaining forms/dropdowns._

## Company create / edit form — `components/company/CompanyWizard.tsx`

| Field | Visible label | Required | Type | Data source | Searchable | Custom values | Validation | Persisted | Reloads | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| Company name | ✅ | ✅ | text | — | — | — | required, ≤200, non-ASCII ok | `organizations.name` | ✅ | **PASS** |
| Legal name | ✅ + help | — (Optional) | text | — | — | — | ≤255 | `organizations.legal_name` | ✅ | **PASS** |
| Website | ✅ | — | url | — | — | — | `https?://…` (client + server 422) | `organizations.website` | ✅ | **PASS** |
| Company type | ✅ | — | SearchableSelect | `COMPANY_TYPES` (11) | ✅ | — | — | `organizations.company_type` | ✅ | **PASS** |
| Employee range | ✅ | ✅ | SearchableSelect | `EMPLOYEE_RANGES` (7) | ✅ | — | required | `organizations.employee_range` + derived `employee_count` | ✅ | **PASS** |
| Primary industry | ✅ + help | ✅ | SearchableSelect | `INDUSTRIES` (35) | ✅ | ✅ ("Use \"x\"…" + Specify field) | required | `organizations.industry` | ✅ | **PASS** |
| Headquarters country | ✅ + help | ✅ | SearchableSelect | `COUNTRIES` (ISO 3166-1, ~195) | ✅ | — | required, **no default** | `organizations.headquarters_country` (ISO alpha-2) | ✅ | **PASS** |
| Countries of operation | ✅ + help | — | MultiCountrySelect (chips) | `COUNTRIES` | ✅ | — | — | `organizations.countries_operating` (JSON codes) | ✅ | **PASS** |
| AI deployment countries | ✅ + help | — | MultiCountrySelect | `COUNTRIES` | ✅ | — | — | `organizations.ai_deployment_countries` | ✅ | **PASS** |
| Customer/user countries | ✅ + help | — | MultiCountrySelect | `COUNTRIES` | ✅ | — | — | `organizations.customer_countries` | ✅ | **PASS** |
| Uses AI / GenAI / agents / personal data / financial institution / critical infra / software vendor / EU market | ✅ + help | — | Toggle (role=switch) | — | — | — | — | `organizations.*` flags + `OrganizationProfile` | ✅ | **PASS** |
| Governance contacts ×5 | ✅ | — | text | — | — | — | — | `organizations.governance_contacts` (JSON) | ✅ | **PASS** |
| Review step | shows every value + EU-exposure derivation | — | — | — | — | — | — | — | — | **PASS** |
| Save/Cancel | sticky footer: Back / Continue / Create company / Save changes; close X | — | — | — | — | — | — | — | — | **PASS** |

**Layout:** portal to `document.body` (no clip); sticky header+footer, scrolling body; `max-w-xl` column; 2-col grid collapses to 1 on `sm`. Verified at **1366×768**: all fields reachable, footer visible, no horizontal scroll.

## Reference data (central) — `frontend/src/lib/referenceData.ts`

`COUNTRIES` (ISO 3166-1 alpha-2 + name, ~195), `EU_EEA_CODES`, `INDUSTRIES` (35 + Other), `COMPANY_TYPES` (11), `EMPLOYEE_RANGES` (7 with midpoints). Helpers: `countryName`, `industryLabel`, `employeeRangeLabel`.

## Reusable form primitives — `frontend/src/components/forms/FormControls.tsx`

`Field` (label + required/optional + help + inline error + `htmlFor`), `TextInput`, `SearchableSelect` (type-ahead, arrow-key nav, opens upward when <280px below, custom-value row, empty state), `MultiCountrySelect` (chips + backspace-remove + search), `Toggle` (`role="switch"`, `aria-checked`, focus ring).

## Other forms — audit (not rebuilt this pass)

| Form | Location | Dropdowns | Notable gaps | Status |
|---|---|---|---|---|
| SME onboarding wizard | `components/sme/SmeExperience.tsx` | country chips (12), industry (9), providers, data types, decision domains | uses **its own** short country/industry lists — should adopt `referenceData.ts` | ⚠️ works; lists incomplete |
| AI System intake wizard | `page.tsx` "intake" tab | deployment countries, decision domains, model provider (free text), agent tools | country list local; model/vendor are free-text not linked to registry | ⚠️ works; P1 to standardise |
| Add Model / Agent / Vendor (registry quick-add) | `page.tsx` registry modals | provider, service type, risk rating, data-processing role | small fixed option sets; labels present; `<select>` not searchable | ⚠️ works |
| Control status modal | `page.tsx` `selectedControl` | status (5), effectiveness (3) | fine for the option count; labels present | ✅ |
| Assessment: start + approval | `page.tsx` "assessments" tab | system select, framework select, per-requirement status | framework select lists 17 legacy ids; per-requirement UI caps at 40 rows | ⚠️ works |
| Evidence upload | `page.tsx` evidence modal | evidence type, control multi-select | "what evidence is expected" hint not yet shown per control | ⚠️ works |
| Risk create / Finding create / Remediation | `page.tsx` Risk Register tab | severity, source, control, system | inline forms; labels present via placeholder in a few spots | ⚠️ mostly |
| Login / Signup | `page.tsx` `LoginScreen` | — | labels present, focus rings | ✅ |

## §104 field-level status

| | Result |
|---|---|
| COMPANY FORM | **PASS** |
| LEGAL NAME | **PASS** (label + help visible; ≤255 validated; persists to `legal_name`) |
| COUNTRY SELECTOR | **PASS** (full ISO list, searchable, keyboard, opens upward) |
| MULTI-COUNTRY | **PASS** (chips + search on 3 fields) |
| INDUSTRY SELECTOR | **PASS** (35-entry taxonomy, searchable) |
| CUSTOM INDUSTRY | **PASS** ("Use \"x\"…" + Specify field) |
| EMPLOYEE FIELD | **PASS** (ranges, not a raw number) |
| COMPANY CREATE | **PASS** (7 backend tests + browser) |
| COMPANY EDIT | **PASS** (`PATCH /organizations/current`, prefilled wizard) |
| COMPANY SWITCH | **PASS** (prior pass; token swap + full reload; search when many) |
| FORM PERSISTENCE (draft on refresh) | **FAIL** — not implemented; wizard state is lost on browser refresh mid-flow |
| RESPONSIVE | **PASS at 1366×768 for the company wizard** (verified). Other pages not re-audited this pass. |
| ACCESSIBILITY | **PARTIAL** — labels/`htmlFor`, `role="switch"`, focus rings, arrow-key select nav done; no axe run, no full keyboard-trap audit, modal focus-trap not implemented |
| AI REGISTRY | **PASS** (Add AI System CTA + guided empty state + Governance Progress/Next Action columns from prior pass) |
| AI SYSTEM INTAKE | **PARTIAL** — functional, differentiated results, but not rebuilt to the new standard (local country list, free-text model/vendor) |
| APPLICABILITY UX | **PARTIAL** — company applicability groups by exposure with reasoning + source + confidence + legal-review flags (prior pass); per-system applicability screen not yet card-grouped |
| ASSESSMENT UX | **PARTIAL** — start/list/detail + Submit/Approve/Reject + search on requirement browser; per-requirement work caps at 40 rows in the modal |
| EVIDENCE UX | **PARTIAL** — upload/review/auto-finding works; "expected evidence" guidance per control not surfaced |
| FINDING UX | **PASS** — title, why-it-matters, severity, source, owner-linkable, due date, remediation, resolve; auto-created from failed controls / rejected evidence |
| REPORT UX | **PARTIAL** — "Generate report →" appears after approval; report is JSON; not a large post-approval CTA on the dashboard |
| FULL CUSTOMER JOURNEY | **PASS** — create company → add system → applicability → assessment → fail control → finding → remediate → submit → approve → report, all via UI/API, verified in `test_company_journey_e2e::test_full_governance_journey_new_company` |
