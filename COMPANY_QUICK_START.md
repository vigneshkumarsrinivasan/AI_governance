# Company Quick Start

Get from zero to a defensible AI governance baseline in about an hour. No developer needed.

## Before you start
- Open the app URL your admin gave you (local dev: **http://localhost:3001**, API on **:8010**).
- Have ready: the countries you operate in / sell to, your AI providers (OpenAI, Anthropic, AWS Bedrock, …), and the data types you handle.

## 1. Create your organization (2 min)
On the login screen choose **"New organization? Create one"**. Enter your name, email, password, and company name. You become the Tenant Admin and land in the **Simple** experience.

## 2. Complete the 5-minute onboarding (5 min)
The wizard asks about your company, AI use, providers, data, and product. You are **not** picking frameworks — the platform determines them. Finish with **"See my compliance profile"**.

## 3. Read your compliance profile (5 min)
- **Home** — your AI Trust Score (6 dimensions) and the top things to do this week.
- **What applies to us** — every framework with an exposure (*Directly applicable* / *Supply-chain* / *Customer required* / *Recommended*), a plain-English reason, the source article, and any items needing legal review. Nothing is asserted as legal certainty where it depends on interpretation.
- **What to do next** — a prioritized, time-estimated action list built from your real gaps.

## 4. Register your AI systems (10 min)
Switch to **Advanced view** (bottom of the sidebar) → **AI Systems Inventory** → **Register AI System**. Add each system with its purpose, data, jurisdictions, model, and provider. Run **Intake & Classification** for each to get its risk classification and applicable obligations.

## 5. Add models, vendors, agents (10 min)
- **Vendors** — add each AI provider; record data-processing role, regions, retention, training-on-data setting, DPA.
- **Models** — add each model; link it to its vendor and the systems that use it.
- **Agents** — for any autonomous system, capture tools, permissions, autonomy, human-approval requirement, and confirm the kill-switch. The platform computes an agent risk score.

## 6. Start an assessment (15 min)
**Advanced → (create an assessment via the API or the assessment view)** for a framework that applies to you (e.g. EU AI Act). It is pre-populated with the **real requirement set** for that regulation. Work through the requirements, setting a status and rationale, and attaching evidence.

## 7. Assign controls and collect evidence (ongoing)
**Unified Controls** — set each control's status, effectiveness, and owner. One piece of evidence can satisfy many frameworks. **Evidence Vault** — upload your policy / DPIA / model card / config / test report and map it to controls. A reviewer (different person than the uploader) accepts or rejects it.

## 8. Review findings and remediate
**Risk Register & SLA** — the **Findings** section lists issues. Findings appear automatically when a control fails its effectiveness test or evidence is rejected, and you can raise one manually with **+ New Finding**. For each finding, add a **+ Remediation** task and assign an owner. Completing all tasks resolves the finding (it stays in the audit trail).

## 9. Manage risk
Create risks (from an assessment gap, a finding, an agent, a vendor). Score inherent vs residual. High risks can only be **accepted** by an authorized approver, with a written business justification and an expiry date — and it's audited.

## 10. Generate a report
**Executive Reports** — a board-ready summary generated from your live data (systems, risk mix, readiness, open findings), plus a full machine-readable JSON export.

## 11. Check the audit trail
**Audit Trail** — every governance action (system creation, control change, evidence review, finding, risk acceptance) is logged with actor, timestamp, and before/after.

---
**Not yet available:** email notifications, vendor self-service portal, Trust Pack / Trust Center, connector-collected evidence, PDF/Excel export, SSO. See `docs/SME_MARKET_PRODUCT_GAP_ANALYSIS.md` for the roadmap.
