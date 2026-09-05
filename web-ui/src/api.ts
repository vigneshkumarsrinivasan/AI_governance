/**
 * API Client for AegisAI Web UI.
 * Connects Web UI to FastAPI backend with real session-based authentication
 * (no auto-login, no hardcoded credentials - see frontend/src/lib/api.ts for
 * the Next.js app's identical fix; this file mirrors it since both apps talk
 * to the same backend).
 */

const API_BASE = (import.meta as any).env?.VITE_API_BASE || "http://127.0.0.1:8000/api/v1";

const TOKEN_STORAGE_KEY = "aegis_access_token";
const USER_STORAGE_KEY = "aegis_current_user";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  tenant_id: string;
  organization_id: string | null;
  organization_name?: string | null;
  is_demo_tenant?: boolean;
}

function getToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function setToken(token: string | null) {
  try {
    if (token) sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    else sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* sessionStorage unavailable - session won't persist across refresh */
  }
}

function getStoredUser(): CurrentUser | null {
  try {
    const raw = sessionStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function setStoredUser(user: CurrentUser | null) {
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
  email: string; password: string; full_name: string; organization_name: string;
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

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  if (!token) throw new UnauthorizedError("Not authenticated");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
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
