# SME Repositioning — Phase 1 Implementation

_Delivered 2026-09-08. Additive only. No existing feature, framework, mapping, model, API, or UI capability was removed or disabled._

## What was built (working end-to-end, tested)

### 1. Two experiences on one backend (spec §4, §28)
- `users.ui_mode` — `"simple"` (SME guided) or `"advanced"` (full enterprise console, unchanged).
- **Existing users are untouched**: column default `"advanced"`, migration adds it with that server-default.
- **New self-service signups** default to `"simple"`.
- `PATCH /api/v1/auth/me/ui-mode` switches either way. Frontend: SME users get `SmeExperience`; a "Switch to advanced view" button flips the flag and the original console renders. The advanced sidebar has a reciprocal "Switch to simple view".
- `/auth/me`, `/auth/login`, `/auth/signup` now return `ui_mode` + `onboarding_completed`.

### 2. 5-minute company onboarding (spec §5)
- New table `organization_profiles` (1:1 with `organizations`), raw `answers` JSON + normalised fact columns.
- `GET/PUT /api/v1/onboarding/profile` — partial saves allowed, `completed` flag sets `completed_at`.
- Keeps the coarse `Organization` fields (industry, countries, employee_count, eu_market_exposure…) in sync so existing enterprise dashboards/reports reflect onboarding.
- Frontend: 5-step wizard (Company / AI use / Providers / Data / Product & reviews).

### 3. Company-level applicability engine (spec §6, §23, §24)
- New `services/company_applicability.py` + versioned `data/company_applicability_rules.json` (ruleset `2026.1.0-company`, 27 rules across 19 framework families).
- Reuses the existing per-system condition evaluator (`rule_engine._eval_condition`), extended with numeric operators (`gte/lte/gt/lt`).
- Output per framework: exposure (`DIRECTLY_APPLICABLE` / `POTENTIALLY_APPLICABLE` / `SUPPLY_CHAIN_INDIRECT` / `CONTRACTUALLY_REQUIRED` / `RECOMMENDED_BEST_PRACTICE` / …), **confidence** (`HIGH/MEDIUM/LOW/LEGAL_REVIEW_REQUIRED`), reasoning, jurisdiction, **regulation_type** (legal / certification / voluntary / best-practice / contractual — spec §23), the triggering business facts, a citation to the framework's own scope provision (e.g. "EU AI Act Art. 2(1)(a)"), and the open questions still needed.
- Never asserts legal certainty where scope is interpretive → `LEGAL_REVIEW_REQUIRED` + response-level `legal_review_recommended`.
- `GET /api/v1/onboarding/applicability` persists an `ApplicabilityDecision` (`scope="organization"`, new column) each run and supersedes the previous one — history is never overwritten (existing review workflow applies).
- Verified differentiated: pure-US-SaaS ≠ EU-connected-hardware ≠ India-HRTech results.

### 4. AI Trust Score + Compliance Profile (spec §7, §22)
- New `services/trust_score.py` — rolls up the **same** `CustomerControl` / evidence / `Finding` state the enterprise dashboard uses into 6 plain-language dimensions (AI Governance, AI Security, Privacy, Vendor Risk, Agent Security, Secure Development) via the existing `scoring.calculate_compliance_scores`.
- `GET /api/v1/sme/trust-score` — no fabricated numbers: `has_data:false` and score `0` with a per-dimension `basis` string when a tenant has no controls yet.
- Frontend: score ring + dimension tiles + inventory counts + top-5 actions.

### 5. "What to do next" (spec §16)
- `GET /api/v1/sme/next-actions` — derived entirely from real gaps: AI providers declared in onboarding but missing from the Vendor Registry, missing AI Acceptable Use policy, production agents with DB/code/payment access and no approval gate, open Critical/High findings, models with no vendor, unstarted controls, implemented controls with no evidence.
- Each action: risk, `TODAY/THIS_WEEK/NEXT` bucket, estimated minutes, affected areas, concrete steps, action chips (Fix / Assign / Generate Policy / Upload Evidence / Register).

### 6. Enterprise Sales Readiness (spec §27)
- `GET /api/v1/sme/sales-readiness` — procurement-blocker checklist (AI use policy, AI inventory, vendor review, DPA, incident process, logging, SOC 2/ISO evidence) computed from real state.

### 7. SOC 2 / ISO 27001 / ISO 42001 (spec §3) — copyright-safe
- `data/commercial_frameworks.json` — **metadata only**: our own descriptions, publicly-known structure names, and mappings **from our Unified Control Library to** the standard's clause/criteria IDs. **No reproduced standard text.** `content_availability: "METADATA_ONLY"`, `licence_status: "COPYRIGHTED_CUSTOMER_LICENCE_REQUIRED"`.
- `GET /api/v1/onboarding/frameworks-catalog` exposes them; company applicability rules reference `soc2`/`iso_27001`/`iso_42001` keys.
- Architecture-ready: when a customer loads a licensed copy, a real `FrameworkVersion` supersedes the metadata.

### 8. Sector starter packs (spec §19)
- `data/starter_packs.json` — B2B AI SaaS, FinTech, HealthTech, HRTech, India IT Services, CRA/Connected Product. `GET /api/v1/onboarding/starter-packs`. HIPAA deliberately excluded (not implemented — not invented).

## Database migrations added

`alembic/versions/a1b2c3d4e5f6_sme_onboarding_and_ui_mode.py` (revises `36606e944171`):
- `users.ui_mode` (server_default `"advanced"`)
- `applicability_decisions.scope` (server_default `"system"`), `.framework_exposure` (JSON, nullable), `.open_questions` (JSON, nullable)
- `organization_profiles` (new table, FKs to tenants + organizations, unique on organization_id)

All column adds are guarded with `inspect()` checks → safe to re-run. `downgrade()` provided. No table dropped, no column retyped, no data deleted, no framework IDs changed, no API removed.

## Tests

`backend/tests/test_sme_onboarding.py` — **10 new tests, all passing** (51/51 total suite):
- new signup → simple mode; UI-mode toggle + validation
- onboarding profile roundtrip + completion flag
- company applicability is **differentiated** (SaaS vs hardware) and **explainable** (reasoning + source + jurisdiction + regulation_type on every item)
- NIST AI RMF always flagged `VOLUNTARY_FRAMEWORK` / never legal
- high-risk employment AI → `LEGAL_REVIEW_REQUIRED` + `legal_review_recommended`
- applicability decision persisted + supersedes prior
- Trust Score `has_data:false` / score 0 for a fresh tenant, every dimension explains its number
- next-actions reflect real gaps (declared-but-unregistered providers, missing policy)
- **tenant isolation** on every new endpoint + 401 when unauthenticated
- **per-system intake still works unchanged** (regression guard)
- starter packs + copyright guard on commercial frameworks

Frontend: `tsc --noEmit` clean. Manual E2E in headless Chrome: signup → wizard → dashboard → compliance tab → switch to advanced → full console renders.

## Files added / changed

Added: `services/company_applicability.py`, `services/trust_score.py`, `api/onboarding.py`, `api/sme.py`, `data/company_applicability_rules.json`, `data/commercial_frameworks.json`, `data/starter_packs.json`, `alembic/versions/a1b2c3d4e5f6_*.py`, `tests/test_sme_onboarding.py`, `frontend/src/components/sme/SmeExperience.tsx`, this doc + `SME_MARKET_PRODUCT_GAP_ANALYSIS.md`.
Changed (additively): `models/models.py` (+`OrganizationProfile`, `User.ui_mode`, 3 `ApplicabilityDecision` cols), `services/rule_engine.py` (+numeric ops), `api/auth.py` (ui_mode in payloads + PATCH endpoint), `schemas/schemas.py` (+SME schemas), `main.py` (+2 routers), `frontend/src/lib/api.ts` (+SME client fns), `frontend/src/app/page.tsx` (SME branch + reciprocal toggle + org-name in hero).

## Not in this pass (roadmap — see gap analysis §3 for the full list)

Phase 2: Trust Pack, Trust Center, policy generation, questionnaire automation, quick-add flows, enhanced vendor intelligence UI.
Phase 3+: automated evidence connectors, Shadow AI discovery, agent telemetry, runtime governance, automated evaluations, billing/entitlements, SSO/SCIM, report export.
Still open from prior validation: wiring the 3,211 ingested regulatory requirements into assessments/reports/Copilot; control-mapping + applicability-rule authoring against ingested keys; 800-218A / 800-161 import.
