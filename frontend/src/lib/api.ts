/**
 * API Client for AegisAI Frontend.
 * Connects Next.js UI to FastAPI backend with real session-based
 * authentication (no auto-login, no hardcoded credentials).
 */

// Configurable via NEXT_PUBLIC_API_BASE at build time so the same build can
// target dev/staging/production backends without a code change.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api/v1";

const TOKEN_STORAGE_KEY = "aegis_access_token";
const USER_STORAGE_KEY = "aegis_current_user";

// sessionStorage (not localStorage) so the session ends when the tab closes -
// a reasonable middle ground for an MVP-grade SPA. A production hardening
// follow-up would move to an httpOnly, SameSite=Strict session cookie plus
// CSRF protection so the token is never reachable from JS at all; that is a
// larger backend+frontend change than this pass covers and is called out in
// PRODUCTION_READINESS.md.
function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (token) sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    else sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* sessionStorage unavailable (private browsing, etc.) - session simply won't persist across refresh */
  }
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  tenant_id: string;
  organization_id: string | null;
  organization_name?: string | null;
  is_demo_tenant?: boolean;
  // SME repositioning: "simple" = guided SME experience, "advanced" = full
  // enterprise experience. Both use the same backend; this only changes which
  // screens the frontend renders. Undefined on tokens minted before this field
  // existed - treated as "advanced" so nothing changes for existing users.
  ui_mode?: "simple" | "advanced";
  onboarding_completed?: boolean;
}

function getStoredUser(): CurrentUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function setStoredUser(user: CurrentUser | null) {
  if (typeof window === "undefined") return;
  try {
    if (user) sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    else sessionStorage.removeItem(USER_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export class UnauthorizedError extends Error {}
export class ForbiddenError extends Error {}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export function getCurrentUser(): CurrentUser | null {
  return getStoredUser();
}

export async function login(email: string, password: string): Promise<CurrentUser> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Incorrect email or password");
  }
  const data = await res.json();
  setToken(data.access_token);
  setStoredUser(data.user);
  return data.user;
}

export async function signup(payload: {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
  ui_mode?: "simple" | "advanced";
}): Promise<CurrentUser> {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Sign up failed");
  }
  const data = await res.json();
  setToken(data.access_token);
  setStoredUser(data.user);
  return data.user;
}

export function logout() {
  setToken(null);
  setStoredUser(null);
}

// --- SME experience (spec sections 4-7, 16) --------------------------------
export async function refreshCurrentUser(): Promise<CurrentUser> {
  const me = await request<CurrentUser>("/auth/me");
  setStoredUser(me);
  return me;
}

export async function setUiMode(ui_mode: "simple" | "advanced"): Promise<CurrentUser> {
  const me = await request<CurrentUser>("/auth/me/ui-mode", {
    method: "PATCH",
    body: JSON.stringify({ ui_mode }),
  });
  setStoredUser(me);
  return me;
}

export async function getOnboardingProfile() {
  return request<{ exists: boolean; profile: any }>("/onboarding/profile");
}

export async function saveOnboardingProfile(profile: any) {
  return request<{ exists: boolean; profile: any }>("/onboarding/profile", {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}

export async function getCompanyApplicability() {
  return request<any>("/onboarding/applicability");
}

export async function getStarterPacks() {
  return request<any>("/onboarding/starter-packs");
}

export async function getFrameworksCatalog() {
  return request<any>("/onboarding/frameworks-catalog");
}

export async function getTrustScore() {
  return request<any>("/sme/trust-score");
}

export async function getNextActions() {
  return request<any>("/sme/next-actions");
}

export async function getSalesReadiness() {
  return request<any>("/sme/sales-readiness");
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  if (!token) {
    throw new UnauthorizedError("Not authenticated");
  }

  const headers: Record<string, string> = {
    ...(options.body && !(options.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
    Authorization: `Bearer ${token}`,
    ...((options.headers as Record<string, string>) || {}),
  };

  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });

  if (res.status === 401) {
    logout();
    throw new UnauthorizedError("Session expired. Please sign in again.");
  }
  if (res.status === 403) {
    const body = await res.json().catch(() => ({}));
    throw new ForbiddenError(body.detail || "You do not have permission to perform this action.");
  }
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`API ${endpoint} failed (${res.status}): ${errText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// 1. Dashboard
export async function getDashboardMetrics() {
  return request<any>("/dashboard/metrics");
}

// 2. AI Systems & Intake
export async function getAISystems() {
  return request<any[]>("/ai-systems");
}

export async function createAISystem(payload: any) {
  return request<any>("/ai-systems", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function evaluateIntake(payload: any) {
  return request<any>("/ai-systems/intake-evaluate", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getApplicabilityDecisions() {
  return request<any[]>("/ai-systems/applicability/decisions");
}

export async function reviewApplicabilityDecision(decisionId: string, decision: string, rationale: string) {
  return request<any>(`/ai-systems/applicability/decisions/${decisionId}/review`, {
    method: "PUT",
    body: JSON.stringify({ decision, rationale }),
  });
}

// 3. Frameworks
export async function getFrameworks() {
  return request<any[]>("/frameworks");
}

export async function getFrameworkDetail(frameworkId: string) {
  return request<any>(`/frameworks/${frameworkId}`);
}

// 4. Controls & Crosswalk
export async function getControls() {
  return request<any[]>("/controls");
}

export async function updateControl(controlId: string, payload: any) {
  return request<any>(`/controls/${controlId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export async function getCrosswalkMatrix() {
  return request<any[]>("/crosswalk/matrix");
}

export async function resolveEvidenceCoverage(controlIds: string[]) {
  return request<any>("/crosswalk/resolve-evidence", {
    method: "POST",
    body: JSON.stringify({ control_ids: controlIds })
  });
}

// 5. Assessments
export async function getAssessments() {
  return request<any[]>("/assessments");
}

export async function getAssessmentDetail(id: string) {
  return request<any>(`/assessments/${id}`);
}

export async function submitAssessmentResponse(assessmentId: string, payload: any) {
  return request<any>(`/assessments/${assessmentId}/response`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

// 6. Evidence
export async function getEvidence() {
  return request<any[]>("/evidence");
}

export async function uploadEvidence(payload: any) {
  return request<any>("/evidence", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function uploadEvidenceFile(file: File, title: string, evidenceType: string, controlIds: string[]) {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title);
  form.append("evidence_type", evidenceType);
  form.append("control_ids", JSON.stringify(controlIds));
  return request<any>("/evidence/upload", { method: "POST", body: form });
}

export async function reviewEvidence(evidenceId: string, status: string, notes?: string) {
  return request<any>(`/evidence/${evidenceId}/review`, {
    method: "PUT",
    body: JSON.stringify({ status, notes }),
  });
}

export async function downloadEvidence(evidenceId: string): Promise<Blob> {
  const { download_token } = await request<{ download_token: string }>(`/evidence/${evidenceId}/download-token`);
  const res = await fetch(`${API_BASE}/evidence/${evidenceId}/download?token=${encodeURIComponent(download_token)}`);
  if (!res.ok) throw new Error("Download failed");
  return res.blob();
}

// 7. Risks & Remediations
export async function getRisks() {
  return request<any[]>("/risks");
}

export async function getFindings() {
  return request<any[]>("/findings");
}

export async function getRemediations() {
  return request<any[]>("/remediations");
}

export async function updateRemediation(taskId: string, status: string) {
  return request<any>(`/remediations/${taskId}`, {
    method: "PUT",
    body: JSON.stringify({ status })
  });
}

export async function acceptRisk(riskId: string, businessJustification: string, expiryDate?: string) {
  return request<any>(`/risks/${riskId}/accept`, {
    method: "PUT",
    body: JSON.stringify({ business_justification: businessJustification, expiry_date: expiryDate }),
  });
}

// 8. AI Security & Agents
export async function getSecurityOverview() {
  return request<any>("/security/overview");
}

export async function getAgents() {
  return request<any[]>("/security/agents");
}

export async function triggerKillSwitch(agentId: string) {
  return request<any>(`/security/agents/${agentId}/kill-switch`, {
    method: "POST"
  });
}

export async function getVendors() {
  return request<any[]>("/security/vendors");
}

// 8b. Model / Agent / Vendor Registries (Phase 1)
export async function getModels() {
  return request<any[]>("/models");
}
export async function createModel(payload: any) {
  return request<any>("/models", { method: "POST", body: JSON.stringify(payload) });
}
export async function updateModel(modelId: string, payload: any) {
  return request<any>(`/models/${modelId}`, { method: "PUT", body: JSON.stringify(payload) });
}
export async function linkModelToSystem(modelId: string, systemId: string, role: string = "Secondary") {
  return request<any>(`/models/${modelId}/link-system`, {
    method: "POST",
    body: JSON.stringify({ system_id: systemId, role }),
  });
}
export async function getModelDependents(modelId: string) {
  return request<any>(`/models/${modelId}/dependents`);
}

export async function getAgentRegistry() {
  return request<any[]>("/agents");
}
export async function createAgent(payload: any) {
  return request<any>("/agents", { method: "POST", body: JSON.stringify(payload) });
}
export async function updateAgentRegistry(agentId: string, payload: any) {
  return request<any>(`/agents/${agentId}`, { method: "PUT", body: JSON.stringify(payload) });
}
export async function getAgentPermissionGraph() {
  return request<any>("/agents/permission-graph");
}

export async function getVendorRegistry() {
  return request<any[]>("/vendors");
}
export async function createVendor(payload: any) {
  return request<any>("/vendors", { method: "POST", body: JSON.stringify(payload) });
}
export async function updateVendorRegistry(vendorId: string, payload: any) {
  return request<any>(`/vendors/${vendorId}`, { method: "PUT", body: JSON.stringify(payload) });
}
export async function getVendorImpact(vendorId: string) {
  return request<any>(`/vendors/${vendorId}/impact`);
}

// 8c. Knowledge Graph (Phase 2)
export async function graphRequirementAffectedSystems(requirementId: string) {
  return request<any>(`/graph/requirement/${requirementId}/affected-systems`);
}
export async function graphControlsMultiFramework(frameworks: string[]) {
  return request<any[]>(`/graph/controls/multi-framework?frameworks=${encodeURIComponent(frameworks.join(","))}`);
}
export async function graphEvidenceHighestCoverage() {
  return request<any[]>("/graph/evidence/highest-coverage");
}
export async function graphVendorExposure() {
  return request<any[]>("/graph/vendors/regulatory-exposure");
}
export async function graphSharedHighRiskModels() {
  return request<any[]>("/graph/models/shared-high-risk");
}
export async function graphAgentToolDependents(tool: string) {
  return request<any>(`/graph/agents/tool-dependents?tool=${encodeURIComponent(tool)}`);
}

// 9. Copilot & Reports
export async function queryCopilot(query: string) {
  return request<any>("/copilot/query", {
    method: "POST",
    body: JSON.stringify({ query })
  });
}

export async function getExecutiveReport() {
  return request<any>("/reports/executive");
}

export async function getAuditEvents() {
  return request<any[]>("/audit");
}
