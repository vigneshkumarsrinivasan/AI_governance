# Production Readiness Report

_Run date: 2026-09-06. Supersedes the older `PRODUCTION_READINESS.md` for the
regulatory subsystem; see `VALIDATION_REPORT.md` for the full method._

Readiness is expressed as **explicit release gates**, not a score.

---

## Release gates

| Gate | Status | Evidence / blocker |
|---|---|---|
| **SECURITY (implemented surface)** | ✅ PASS | 41 pytest + 62 live checks; headers added; no secrets; SSRF-guarded ingestion |
| **SECURITY (independent pen-test)** | ❌ NOT DONE | requires external firm |
| **TENANT ISOLATION** | ✅ PASS | 26 cross-tenant attempts, 0 leaks |
| **AUTH / RBAC** | ✅ PASS (core) / ⚠️ | server-enforced; but no user-invitation flow, no MFA/SSO, no lockout/reset |
| **REGULATORY CONTENT** | ⚠️ PARTIAL | 16/17 frameworks ingested, hashed, licence-checked, structurally VALIDATED; **0 human-verified requirements, 0 control mappings, 0 applicability rules on the ingested set**; 1 framework (800-161) blocked; India DPDP licence review pending |
| **CORE WORKFLOWS** | ✅ PASS | signup→inventory→applicability→assessment→evidence→risk→report over HTTP, no manual DB edits |
| **EVIDENCE** | ✅ PASS | hash, tenant-bound signed download, MIME allowlist, review workflow, separation of duties |
| **ASSESSMENTS** | ⚠️ PARTIAL | now generated from the real requirement set (419 for EU AI Act, etc.); no create-UI; scoring is answer-weighting, not the full control+evidence+effectiveness determination |
| **REPORTING** | ⚠️ PARTIAL | executive report as JSON; no PDF/CSV/XLSX; no evidence pack; no auditor delivery |
| **BACKUP / RESTORE** | ❌ FAIL | no automation, no tested restore |
| **OBSERVABILITY** | ⚠️ PARTIAL | `/health` (+ DB check), structured-ish logs, request errors carry a code; no `/ready`, no worker/queue health, no error-tracking integration, no metrics |
| **CI/CD** | ⚠️ PARTIAL | CI runs lint + 41 tests + migration check + non-blocking `pip-audit` + web-ui lint/build. Missing: secret scan, container scan, `npm audit` gate, SAST, integration/E2E in CI, security-test gate |
| **DATA STORE** | ⚠️ | code supports PostgreSQL (`asyncpg`); prod boot refuses SQLite; but the deployment has only been run on SQLite + a `docker-compose` (no TLS, no secrets manager, no HA) |
| **PERFORMANCE / SCALE** | ❌ NOT DONE | no load test at the target scale (10k+ systems, 1M+ mappings); N+1 review not performed on the heavy graph endpoints |
| **DR** | ❌ NOT DONE | no runbook, no exercise |

---

## Verdict

**Status: PRE-PRODUCTION / DESIGN-PARTNER CANDIDATE.**

The security and tenant-isolation gates — the ones that would make a multi-tenant
SaaS unsafe to run at all — **pass**. The core compliance workflow runs end to end
against genuine, source-traceable regulatory content.

It is **not a production candidate** for unsupervised external customers because:

1. **Compliance content is machine-extracted and unmapped.** Requirements have not
   been human-verified, mapped to controls (0), or given applicability rules on the
   ingested keys (0). A customer assessment today lists the right requirements but
   cannot compute a defensible readiness position from controls + evidence.
2. **No backup/restore, no DR, no load test, no independent pen-test.**
3. **Whole feature areas are absent** (connectors, telemetry, runtime governance,
   red-team, vendor/auditor portals, user management, background workers) — several
   are load-bearing for the "continuous monitoring" and "auditor workflow" claims.

---

## Path to production candidate

**Phase 1 — make the compliance output defensible (largest effort, no external dep)**
- Map the ~3,443 ingested requirements → Unified Control Library (AI-propose → human-approve).
- Human-verify the requirements used in scoring.
- Author applicability rules against the ingested requirement keys.
- Replace naive scoring with the spec §53 determination (applicable + control implemented + evidence accepted + effectiveness + no blocking finding).
- Point the Copilot RAG at `regulatory_*`; add citations.
- Retire `data/frameworks/*.json`.

**Phase 2 — platform hardening**
- User management + invitation + MFA/SSO + password reset + lockout.
- PostgreSQL deployment with managed backups + a tested restore.
- Background worker + scheduled regulatory source-monitor + change→reassess orchestration.
- CI security gates (secret/container/dependency/SAST) as blocking.
- Load test at target scale; fix N+1 on graph endpoints.
- Report export (PDF/CSV) + evidence pack.
- Observability: `/ready`, metrics, error tracking, structured JSON logs.

**Phase 3 — external validation**
- Independent penetration test.
- Legal review of the platform's regulatory interpretations.
- India DPDP / Gazette reproduction-licence review.
- DR exercise.

**Phase 4 — feature completion** (as roadmap, not blockers for a pilot)
- Connectors, agent telemetry, policy-to-code + runtime governance, red-team engine,
  vendor portal, auditor portal, Shadow AI discovery.
