# Security Validation Report

_Run date: 2026-09-06. Re-run: `cd backend && python -m pytest tests/test_api_security.py -q`
plus `scratchpad/validate.py` against a running instance._

This is a **self-assessment through code and live testing**. It is not a
substitute for an independent penetration test (see §7).

---

## 1. Authentication

| Check | Result |
|---|---|
| Signup issues a JWT; password hashed with bcrypt (`core/security.py`) | PASS |
| Login with wrong password | `401` PASS |
| Unauthenticated API call | `401` PASS |
| Malformed / garbage bearer token | `401` PASS |
| Signup attempting `role: "Super Admin"` | privilege **not** granted (founder becomes Tenant Admin) PASS (`test_signup_login_and_me`) |
| Token expiry | `ACCESS_TOKEN_EXPIRE_MINUTES` enforced in `decode_access_token` — PASS (unit) |
| Password reset / email verification / account lockout / MFA / SSO | **NOT_IMPL** |

## 2. RBAC (server-side)

| Check | Result |
|---|---|
| Read-only role (`Viewer`) → `POST /ai-systems` | `403` PASS (`test_rbac_viewer_cannot_write_but_admin_can`) |
| Role tiers centralised in `core/permissions.py`; enforced by `require_roles` dependency, not UI | PASS |
| Evidence review restricted to reviewer tier (separation of duties from uploader) | PASS (`EVIDENCE_REVIEW` excludes most `EVIDENCE_WRITE` roles) |
| Risk acceptance restricted to `RISK_ACCEPTANCE_APPROVAL` | PASS |
| Agent kill-switch restricted to `OPERATIONAL_CONTROL` | PASS |
| "Super Admin" bypass is explicit and audited | PASS by design |
| Coverage gap | non-founder users can only be created via direct DB insert — the **full** role matrix is not exercisable through the product |

## 3. Multi-tenant isolation — **P0 gate**

Two tenants created via signup. Tenant B attempted, with a valid B token:

| Attack surface | Attempts | Result |
|---|---|---|
| `GET`/`PUT`/`DELETE` by A's object id — ai-systems, models, agents, vendors, assessments, risks, evidence | 17 | **all 403/404** |
| Dependency/impact graphs for A's model/agent/vendor | 3 | all 403/404 |
| Evidence review of A's record (valid status body) | 1 | `404` (query is `id AND tenant_id`) |
| Evidence download-token + download of A's file (B's own token) | 2 | `403` (token bound to evidence's real tenant) |
| List endpoints (`/ai-systems`, `/models`, `/agents`, `/vendors`, `/risks`, `/assessments`, `/evidence`) contain A's objects | 7 | **none** — 0 leak |
| Copilot query "list all AI systems and owners" from tenant B | 1 | A's system name **not** present |

**26 cross-tenant attempts, 0 leaks. P0 gate: PASS.**

## 4. IDOR / injection

| Check | Result |
|---|---|
| `GET /ai-systems/<nil-uuid>` | `404` PASS |
| `GET /models/not-a-real-id` | `404` PASS |
| Path traversal `GET /assessments/../ai-systems` | `404` PASS |
| SQLAlchemy ORM parameterised everywhere (no string-built SQL found) | PASS (grep) |
| Evidence upload MIME/type allowlist | PASS (`test_evidence_upload_rejects_disallowed_file_type`) |
| Regulatory source fetcher SSRF | **mitigated** — strict host allowlist in `regulatory/fetch.py`, redirects off-allowlist refused, 60 MB cap, no entity resolution / archive extraction |
| XSS/CSRF | API is JSON-only + `Content-Type` enforced; CSRF N/A for bearer-token auth (no cookies). Frontend not separately fuzzed |

## 5. Response headers (added this validation)

`curl -D- http://…/api/v1/frameworks`:
```
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: no-referrer
content-security-policy: default-src 'none'; frame-ancestors 'none'
cross-origin-opener-policy: same-origin
permissions-policy: geolocation=(), camera=(), microphone=()
strict-transport-security: (production only)
```

## 6. Secrets / dependencies / config

| Check | Result |
|---|---|
| Secret scan of tracked tree (`AKIA…`, `ghp_…`, private keys, `sk-…`, `xox…`) | **0 hits** |
| `.env` tracked in git | none |
| `SECRET_KEY` dev default | present, but `validate_production_settings()` **refuses to boot** in prod with it (also blocks `SEED_DEMO_DATA=true` and SQLite in prod) |
| `web-ui` npm audit (prod deps) | **0 vulnerabilities** |
| `pip check` | 2 conflicts, both in unrelated global packages (`google-cloud-bigquery`, `grpcio-status`) — not in `requirements.txt` |
| CI security gates | `pip-audit` (non-blocking) only. **Missing:** secret scan, container scan, `npm audit`, SAST, SBOM |
| DEBUG / stack-trace leakage | FastAPI default (no `debug=True`); errors return JSON `{error:{code,message,request_id}}` |

## 7. Not covered here — requires external work

- Independent **penetration test** (network, auth, business logic).
- Frontend DOM XSS / dependency-confusion fuzzing.
- Cloud IAM / infra review once connectors exist.
- DoS / rate-limiting under load (no rate limiter implemented).
- Malware scanning of uploaded evidence (no AV hook).
- Formal threat model of the agent-telemetry / runtime-governance features
  (not implemented, so nothing to test).

## Verdict

**Security gate: PASS for the implemented surface** (auth, RBAC, tenant
isolation, IDOR, injection basics, headers, secrets). Tenant isolation — the
critical P0 — held across 26 attempts. Production sign-off still requires an
external penetration test and the CI security gates above.
