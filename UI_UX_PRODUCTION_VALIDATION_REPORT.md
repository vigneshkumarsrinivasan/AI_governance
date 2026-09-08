# UI/UX Production Validation Report

_2026-09-08. Focus of this pass: the company creation/edit form (the reported blocker) + the highest-impact adjacent UX. Executed against the live app at **1366×768** and via `pytest`._

## Part 1 — Reproduced problems & root causes

| Reported problem | Root cause (found, not assumed) |
|---|---|
| Legal Name label not visible / clipped | The old `CreateCompanyModal` was a `max-w-md` box with **no `max-height` and no internal scroll**; on a short screen the lower fields (incl. Legal Name help) were pushed below the viewport. Also lived **inside the header's `backdrop-blur` element**, which creates a CSS containing block — so `position: fixed` was resolving against the 64px header, not the viewport. |
| Form cramped / content exceeds viewport | Same: fixed-in-blurred-ancestor + no viewport-aware sizing + a 2-column grid squeezing complex fields. |
| Country dropdown unclear / incomplete | Hard-coded 12-entry `COUNTRIES` array in the component; a plain `<select>`; no search. |
| Industry dropdown unclear / incomplete / can't add custom | Hard-coded 9-entry list of internal keys (`b2b_saas`…); no "Other"; no custom value. |
| Employee field is a raw number (`25`) | `<input type="number">` bound to `employee_count`, default 25. |
| Missing Company Type, Website not persisted | `Organization` model had no `legal_name`, `website`, `company_type`, `employee_range` columns; `create_company` dropped `legal_name`/`website` into a JSON blob only. |
| Defaults to United States | `Organization.headquarters_country` model default `"United States"`; schema default `"US"`. |
| "Silently inherits Acme" feel | New orgs got `industry="b2b_saas"`, `employee_count=25`, `headquarters="US"` regardless of input. |

## Part 2 — Fixes

| Area | Fix | Test |
|---|---|---|
| **Full-screen company wizard** | New `components/company/CompanyWizard.tsx` — a `fixed inset-0` overlay (**rendered via `createPortal` to `document.body`** so no ancestor can clip it), sticky header (progress) + sticky footer (Back / Continue), scrolling middle. 5 short steps: Company details → Operating footprint → AI & regulatory profile → Governance contacts → Review. | browser @1366×768: footer buttons in viewport, no horizontal scroll |
| **Every field has a visible label** | New `components/forms/FormControls.tsx` — `Field` wrapper (label + `*`/`Optional` + help + inline error + `<label htmlFor>`), `TextInput`, `SearchableSelect`, `MultiCountrySelect`, `Toggle`. Legal Name shows *"Registered legal entity name, if different from the company display name."* | browser asserts label + help visible |
| **Country selector** | New `lib/referenceData.ts` — **complete ISO 3166-1 list** (~195). `SearchableSelect` with type-ahead, keyboard nav, opens upward when low on space, "India (IN)" display. Multi-country fields use chips + search. | browser: search "Ind" → India, Indonesia |
| **Industry selector** | 35-entry taxonomy (Software/SaaS, Banking, FinTech, Healthcare, Automotive, Manufacturing, Critical Infrastructure, Defense/Aerospace, …, Other). Searchable. **Custom values allowed** ("Use \"x\" as a custom industry") + an explicit "Specify industry" field when "Other" is chosen. | browser: "fintech" → FinTech |
| **Employee range** | `EMPLOYEE_RANGES` (1–10 … 10,000+); backend stores both `employee_range` and a derived `employee_count` midpoint. | `test_company_profile_fields_persist_and_edit` (51-250 → 150) |
| **Company type** | `COMPANY_TYPES` (private, public, startup, SME, enterprise, government, nonprofit, consultancy, financial institution, …). Distinct from industry. | persistence test |
| **No incorrect defaults** | Wizard starts with **empty** HQ country; schema `headquarters_country: Optional` with **no default**; `create_company` no longer forces `US`/`b2b_saas`/`25`. | `test_new_company_has_no_default_country_or_acme_data` (`headquarters_country in ("", None)`) |
| **Validation + inline errors** | Client: required checks, name ≤200, legal name ≤255, website URL. Server: `field_validator` on website, `Field(max_length=…)`, blank name → **422 with a field message** (not 500). | `test_company_field_validation` (blank/bad-url/over-long → 422; `Müller & Société Générale` → 201) |
| **Backend fields + persistence** | Migration `c3d4e5f6a7b8` adds `legal_name, website, company_type, ai_deployment_countries, customer_countries, employee_range, is_software_vendor, processes_personal_data, governance_contacts`. `create_company` + `PATCH /organizations/current` write all of them; `GET /organizations/current` returns all. EU exposure auto-derived from any EU/EEA country in operating/deployment/customer lists. | `test_company_profile_fields_persist_and_edit` (create → reload → edit → reload) |
| **Edit company** | Same wizard in `mode="edit"`, prefilled from `GET /organizations/current`; "Save changes". Accessible from the company selector ("Edit {name}", hidden for the demo tenant). | persistence test edits legal_name + employee_range |
| **Company selector** | Search box appears when >6 companies; "Add company" + "Edit" in the dropdown; DEMO badge on Acme; keyboard-focusable trigger. | prior `test_company_journey_e2e` + browser |
| **"Add AI System" CTA** | Renamed "Start New Intake" → **"+ Add AI System"** (primary button, top-right of AI Registry); empty state is now a paragraph + a real button, not a tiny inline link (spec §35, §37). | browser |
| **Special characters / non-ASCII** | No ASCII restriction; `Müller & Société Générale — PT Teknologi Indonesia` creates and displays correctly. | `test_company_field_validation` |

## Part 3 — Not done this pass (documented, prioritised)

**P1 (should do next):** run the AI System intake wizard through the same standard (its country/AI-type lists are still local); centralise the SME onboarding wizard's lists onto `referenceData.ts`; unsaved-changes guard + wizard draft persistence on refresh; a toast/notification system (currently `alert()` in a few places); breadcrumbs; a dedicated Company Management page (table of companies with Edit/Manage Users/Archive) — currently only the selector dropdown; date/number formatting sweep.

**P2:** full 100-route + every-form audit with a11y tooling (axe), visual-regression screenshots, browser-zoom matrix, tablet/mobile pass on every page, column-chooser on wide tables, per-requirement assessment UI beyond the first 40 rows.

**Terminology:** the app still mixes "Company" and "Organization" (nav, API paths). The user-facing term is now consistently "Company" in the new wizard/selector; the API path `/organizations` and some older labels remain.

## Regression

- **Backend: 64/64 pass** (61 prior + 3 new company-field tests in `test_company_journey_e2e.py`).
- **Live E2E script: 62/62 pass.**
- **Frontend: `tsc --noEmit` clean.**
- No existing route/table/framework/control/API/permission removed. All prior features intact.
