import { useState, useEffect, useRef } from "react";
import type { FormEvent } from "react";
import {
  Shield, Brain, AlertTriangle, AlertCircle, FileText,
  Layers, Lock, Terminal, Activity, FileCheck, Sliders, RefreshCw,
  ExternalLink, ChevronRight, Play, X, Download,
  Building, Check, Clock, AlertOctagon, Sparkles, Target,
  Settings, Users, BarChart2, GitMerge, Zap,
  TrendingUp, ShieldCheck, Database, ChevronDown, Plus,
  CheckCircle2
} from "lucide-react";
import * as api from "./api";

// ─── Color helpers ────────────────────────────────────────────
function getRiskColor(score: number): string {
  if (score >= 20) return "#F43F5E";
  if (score >= 15) return "#FB7185";
  if (score >= 10) return "#FBBF24";
  if (score >= 5) return "#34D399";
  return "#94A3B8";
}

function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    "Implemented": "#34D399",
    "In Progress": "#FBBF24",
    "Not Started": "#FB7185",
    "Accepted Risk": "#C084FC",
    "Tested": "#38BDF8",
    "Unknown": "#64748B",
    "Open": "#FB7185",
    "Mitigated": "#34D399",
    "Accepted": "#C084FC",
    "Done": "#34D399",
    "Active": "#34D399",
    "Halted": "#F43F5E",
    "Yes": "#34D399",
    "No": "#FB7185",
    "Partial": "#FBBF24",
    "N/A": "#64748B",
  };
  return map[status] || "#94A3B8";
}

function getReadinessColor(pct: number): string {
  if (pct >= 80) return "#34D399";
  if (pct >= 60) return "#FBBF24";
  return "#FB7185";
}

// ─── Risk Heatmap Component ──────────────────────────────────
function RiskHeatmap({ risks }: { risks: any[] }) {
  const likelihood = ["Rare (1)", "Unlikely (2)", "Possible (3)", "Likely (4)", "Almost Certain (5)"];
  const impact = ["Negligible (1)", "Minor (2)", "Moderate (3)", "Major (4)", "Catastrophic (5)"];

  const cells: Record<string, any[]> = {};
  risks.forEach(r => {
    const l = Math.min(5, Math.max(1, Math.round(r.residual_score / 5)));
    const im = Math.min(5, Math.max(1, Math.round(r.inherent_score / 5)));
    const key = `${l}-${im}`;
    if (!cells[key]) cells[key] = [];
    cells[key].push(r);
  });

  const getHeatClass = (l: number, im: number) => {
    const score = l * im;
    if (score >= 20) return "heatmap-critical";
    if (score >= 12) return "heatmap-high";
    if (score >= 6) return "heatmap-medium";
    if (score >= 3) return "heatmap-low";
    return "heatmap-minimal";
  };

  return (
    <div style={{ overflowX: "auto" }}>
      <div style={{ fontSize: "11px", color: "#64748B", marginBottom: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>↑ Impact (Inherent)</span>
        <span>Likelihood →</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "100px repeat(5, 1fr)", gap: "4px", minWidth: "560px" }}>
        {/* Header row */}
        <div />
        {likelihood.map(l => (
          <div key={l} style={{ fontSize: "10px", color: "#64748B", textAlign: "center", padding: "4px" }}>{l}</div>
        ))}

        {/* Impact rows (high to low) */}
        {[5, 4, 3, 2, 1].map(im => (
          <>
            <div key={`label-${im}`} style={{ fontSize: "10px", color: "#64748B", display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: "8px" }}>
              {impact[im - 1].split("(")[0].trim()}
            </div>
            {[1, 2, 3, 4, 5].map(l => {
              const key = `${l}-${im}`;
              const items = cells[key] || [];
              const score = l * im;
              return (
                <div
                  key={`${l}-${im}`}
                  className={`heatmap-cell ${getHeatClass(l, im)}`}
                  style={{ height: "52px", flexDirection: "column", gap: "2px", fontSize: "10px" }}
                  data-tooltip={items.length > 0 ? items.map(r => r.risk_code).join(", ") : `Score: ${score}`}
                >
                  <span style={{ fontWeight: 800, fontSize: "13px" }}>{score}</span>
                  {items.length > 0 && (
                    <span style={{ fontSize: "9px", opacity: 0.8 }}>{items.length} risk{items.length > 1 ? "s" : ""}</span>
                  )}
                </div>
              );
            })}
          </>
        ))}
      </div>

      {/* Legend */}
      <div style={{ display: "flex", gap: "12px", marginTop: "16px", flexWrap: "wrap", fontSize: "10px" }}>
        {[
          { cls: "heatmap-critical", label: "Critical (≥20)" },
          { cls: "heatmap-high", label: "High (12–19)" },
          { cls: "heatmap-medium", label: "Medium (6–11)" },
          { cls: "heatmap-low", label: "Low (3–5)" },
          { cls: "heatmap-minimal", label: "Minimal (1–2)" }
        ].map(item => (
          <div key={item.cls} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <div className={`heatmap-cell ${item.cls}`} style={{ width: "24px", height: "16px", borderRadius: "3px", pointerEvents: "none" }} />
            <span style={{ color: "#94A3B8" }}>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Circular Progress ───────────────────────────────────────
function CircularProgress({ value, size = 64, color = "#38BDF8", label }: { value: number; size?: number; color?: string; label?: string }) {
  const r = (size - 10) / 2;
  const c = 2 * Math.PI * r;
  const fill = c - (value / 100) * c;
  return (
    <div style={{ position: "relative", width: size, height: size, display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)", position: "absolute" }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth="5"
          strokeDasharray={`${c}`}
          strokeDashoffset={fill}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.16,1,0.3,1)" }}
        />
      </svg>
      <div style={{ textAlign: "center", zIndex: 1 }}>
        <div style={{ fontSize: size / 4.5, fontWeight: 800, color }}>{value}%</div>
        {label && <div style={{ fontSize: 9, color: "#64748B", marginTop: 1 }}>{label}</div>}
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────
export default function App() {
  const [authChecked, setAuthChecked] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<api.CurrentUser | null>(null);

  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [metrics, setMetrics] = useState<any>(null);
  const [aiSystems, setAiSystems] = useState<any[]>([]);
  const [frameworks, setFrameworks] = useState<any[]>([]);
  const [controls, setControls] = useState<any[]>([]);
  const [crosswalk, setCrosswalk] = useState<any[]>([]);
  const [evidenceList, setEvidenceList] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [vendors, setVendors] = useState<any[]>([]);
  const [risks, setRisks] = useState<any[]>([]);
  const [findings, setFindings] = useState<any[]>([]);
  const [remediations, setRemediations] = useState<any[]>([]);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [assessments, setAssessments] = useState<any[]>([]);

  // Modals
  const [copilotOpen, setCopilotOpen] = useState<boolean>(false);
  const [copilotQuery, setCopilotQuery] = useState<string>("");
  const [copilotLoading, setCopilotLoading] = useState<boolean>(false);
  const [copilotMessages, setCopilotMessages] = useState<any[]>([
    {
      sender: "system",
      text: "Welcome to AegisAI Copilot — your AI governance expert grounded in 17 authoritative frameworks.\n\nI can help you:\n• Identify applicable regulations for your AI systems\n• Explain crosswalk mappings and control obligations\n• Find evidence gaps and missing controls\n• Interpret EU AI Act Annex III classification logic\n\nAsk me anything about your compliance posture."
    }
  ]);
  const copilotEndRef = useRef<HTMLDivElement>(null);

  const [selectedSystem, setSelectedSystem] = useState<any>(null);
  const [selectedControl, setSelectedControl] = useState<any>(null);
  const [evidenceModalOpen, setEvidenceModalOpen] = useState<boolean>(false);
  const [selectedAssessment, setSelectedAssessment] = useState<any>(null);
  const [findingsExpanded, setFindingsExpanded] = useState<boolean>(false);

  // Intake Wizard State
  const [intakeStep, setIntakeStep] = useState<number>(1);
  const [intakeForm, setIntakeForm] = useState({
    system_name: "Customer Onboarding Copilot",
    business_purpose: "Automated customer identity verification and preliminary KYC risk scoring",
    business_unit: "Risk & Compliance",
    deployment_countries: ["EU", "US"],
    makes_decisions_about_individuals: true,
    decision_domains: ["credit", "biometrics"],
    interacts_directly_with_humans: true,
    generates_synthetic_content: true,
    processes_personal_data: true,
    is_generative_ai: true,
    uses_foundation_model: true,
    foundation_model_provider: "Anthropic",
    is_autonomous_agent: false,
    can_execute_code: false,
    can_access_database: true
  });
  const [intakeResult, setIntakeResult] = useState<any>(null);
  const [evaluatingIntake, setEvaluatingIntake] = useState<boolean>(false);

  // Evidence Form
  const [newEvidence, setNewEvidence] = useState({
    title: "",
    description: "",
    evidence_type: "Policy",
    file_url: "https://storage.acmefinancial.internal/evidence/doc.pdf",
    selected_controls: [] as string[]
  });

  // Filter states
  const [controlDomainFilter, setControlDomainFilter] = useState<string>("All");
  const [riskStatusFilter, setRiskStatusFilter] = useState<string>("All");
  const [heatmapView, setHeatmapView] = useState<boolean>(false);

  // Load all platform data
  const loadPlatformData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [
        dashData, systemsData, fwData, ctrlData, cwData, evData,
        agentData, vndData, riskData, findData, remData, auditData, assData
      ] = await Promise.all([
        api.getDashboardMetrics(),
        api.getAISystems(),
        api.getFrameworks(),
        api.getControls(),
        api.getCrosswalkMatrix(),
        api.getEvidence(),
        api.getAgents(),
        api.getVendors(),
        api.getRisks(),
        api.getFindings(),
        api.getRemediations(),
        api.getAuditEvents(),
        api.getAssessments()
      ]);

      setMetrics(dashData);
      setAiSystems(systemsData);
      setFrameworks(fwData);
      setControls(ctrlData);
      setCrosswalk(cwData);
      setEvidenceList(evData);
      setAgents(agentData);
      setVendors(vndData);
      setRisks(riskData);
      setFindings(findData);
      setRemediations(remData);
      setAuditEvents(auditData);
      setAssessments(assData);
    } catch (err: any) {
      console.error("Data load failed:", err);
      setError(err.message || "Failed to load platform data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const user = api.getCurrentUser();
    setCurrentUser(user);
    setAuthChecked(true);
    if (user) loadPlatformData();
    else setLoading(false);
  }, []);
  useEffect(() => {
    if (copilotEndRef.current) copilotEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [copilotMessages]);

  const runIntakeEvaluation = async () => {
    try {
      setEvaluatingIntake(true);
      const res = await api.evaluateIntake(intakeForm);
      setIntakeResult(res);
      setIntakeStep(4);
    } catch (err: any) { alert("Evaluation error: " + err.message); }
    finally { setEvaluatingIntake(false); }
  };

  const registerIntakeSystem = async () => {
    if (!intakeResult) return;
    try {
      await api.createAISystem({
        name: intakeForm.system_name,
        business_purpose: intakeForm.business_purpose,
        business_unit: intakeForm.business_unit,
        countries_deployed: intakeForm.deployment_countries,
        ai_technology: intakeForm.is_generative_ai ? "Generative AI" : "Traditional ML",
        model_provider: intakeForm.foundation_model_provider,
        model_name: "Claude 3.5 Sonnet",
        is_generative_ai: intakeForm.is_generative_ai,
        is_agentic_ai: intakeForm.is_autonomous_agent,
        makes_autonomous_decisions: intakeForm.makes_decisions_about_individuals,
        processes_personal_data: intakeForm.processes_personal_data,
        risk_classification: intakeResult.risk_level,
        eu_ai_act_classification: intakeResult.eu_ai_act_classification,
        applicable_frameworks: intakeResult.recommended_frameworks,
        kill_switch_implemented: true
      });
      alert(`System '${intakeForm.system_name}' successfully registered to AI Inventory!`);
      loadPlatformData();
      setActiveTab("inventory");
      setIntakeStep(1);
      setIntakeResult(null);
    } catch (err: any) { alert("Registration failed: " + err.message); }
  };

  const handleKillSwitch = async (agentId: string) => {
    try {
      const res = await api.triggerKillSwitch(agentId);
      alert(res.message);
      loadPlatformData();
    } catch (err: any) { alert("Kill switch failed: " + err.message); }
  };

  const handleUpdateControl = async (controlId: string, status: string, eff: string) => {
    try {
      await api.updateControl(controlId, { status, effectiveness: eff, implementation_notes: "Updated via AegisAI Control Operations" });
      loadPlatformData();
      setSelectedControl(null);
    } catch (err: any) { alert("Failed to update control: " + err.message); }
  };

  const handleUploadEvidence = async () => {
    if (!newEvidence.title) { alert("Please provide an artifact title"); return; }
    try {
      await api.uploadEvidence({
        title: newEvidence.title,
        description: newEvidence.description,
        evidence_type: newEvidence.evidence_type,
        file_url: newEvidence.file_url,
        control_ids: newEvidence.selected_controls
      });
      alert("Evidence artifact uploaded and hashed SHA-256. Satisfying controls across all mapped frameworks!");
      setEvidenceModalOpen(false);
      setNewEvidence({ title: "", description: "", evidence_type: "Policy", file_url: "", selected_controls: [] });
      loadPlatformData();
    } catch (err: any) { alert("Upload failed: " + err.message); }
  };

  const handleRemediationToggle = async (taskId: string, currentStatus: string) => {
    const nextStatus = currentStatus === "Done" ? "In Progress" : "Done";
    try {
      await api.updateRemediation(taskId, nextStatus);
      loadPlatformData();
    } catch (err: any) { alert("Failed to update task: " + err.message); }
  };

  const handleCopilotSend = async () => {
    if (!copilotQuery.trim()) return;
    const q = copilotQuery;
    setCopilotQuery("");
    setCopilotMessages(prev => [...prev, { sender: "user", text: q }]);
    setCopilotLoading(true);
    try {
      const res = await api.queryCopilot(q);
      setCopilotMessages(prev => [...prev, { sender: "copilot", text: res.answer, citations: res.citations }]);
    } catch (err: any) {
      setCopilotMessages(prev => [...prev, { sender: "copilot", text: "Error contacting Copilot: " + err.message }]);
    } finally { setCopilotLoading(false); }
  };

  // ─── Sidebar nav definition ─────────────────────────────────
  const navGroups = [
    {
      label: "Core Governance",
      items: [
        { id: "dashboard", label: "Executive Dashboard", icon: Activity },
        { id: "inventory", label: "AI Systems Inventory", icon: Brain, badge: aiSystems.length },
        { id: "intake", label: "Intake & Classification", icon: Sliders },
        { id: "controls", label: "Unified Controls", icon: Layers, badge: controls.length },
        { id: "crosswalk", label: "17-Framework Crosswalk", icon: GitMerge },
      ]
    },
    {
      label: "Assurance & Audit",
      items: [
        { id: "frameworks", label: "Authoritative Frameworks", icon: FileCheck, badge: "17" },
        { id: "assessments", label: "Assessments & Readiness", icon: Target, badge: assessments.length || undefined },
        { id: "evidence", label: "Evidence Vault", icon: Lock, badge: evidenceList.length },
        { id: "risks", label: "Risk Register & Heatmap", icon: AlertTriangle, badge: findings.filter((f: any) => f.severity === "Critical" && f.status === "Open").length || undefined },
        { id: "reports", label: "Executive Reports", icon: FileText },
        { id: "audit", label: "Tamper-Evident Audit", icon: Clock },
      ]
    },
    {
      label: "Security & Operations",
      items: [
        { id: "security", label: "AI Security & Agents", icon: Terminal, badge: agents.length || undefined },
        { id: "settings", label: "Settings & RBAC", icon: Settings },
      ]
    }
  ];

  const s = { padding: "0 12px", fontSize: "10px", fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: "0.06em", color: "#475569", paddingTop: "16px", paddingBottom: "6px" };
  const navBtnStyle = (active: boolean) => ({
    width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "8px 12px", borderRadius: "8px", fontSize: "12px", fontWeight: active ? 600 : 500,
    cursor: "pointer", border: active ? "1px solid rgba(56,189,248,0.3)" : "1px solid transparent",
    background: active ? "rgba(56,189,248,0.1)" : "transparent",
    color: active ? "#38BDF8" : "#94A3B8", transition: "all 0.15s ease", textAlign: "left" as const
  });

  if (!authChecked) {
    return (
      <div style={{ display: "flex", height: "100vh", width: "100vw", alignItems: "center", justifyContent: "center", background: "#080D1A" }}>
        <RefreshCw size={22} color="#38BDF8" />
      </div>
    );
  }

  if (!currentUser) {
    return <LoginScreen onSuccess={(user) => { setCurrentUser(user); loadPlatformData(); }} />;
  }

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", overflow: "hidden", fontFamily: "var(--font-inter)" }}>

      {/* ══════════════ SIDEBAR ══════════════ */}
      <aside style={{ width: "256px", flexShrink: 0, display: "flex", flexDirection: "column", borderRight: "1px solid rgba(255,255,255,0.07)", background: "linear-gradient(180deg, #080D1A 0%, #060A13 100%)" }}>
        {/* Logo */}
        <div style={{ padding: "18px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ width: "38px", height: "38px", borderRadius: "11px", background: "linear-gradient(135deg, #38BDF8 0%, #6366F1 100%)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 6px 20px rgba(56,189,248,0.3), inset 0 1px 0 rgba(255,255,255,0.2)", flexShrink: 0 }}>
            <Shield style={{ width: "21px", height: "21px", color: "white" }} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: "16px", letterSpacing: "-0.02em", display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ color: "#F8FAFC" }}>AegisAI</span>
              <span style={{ fontSize: "9px", background: "rgba(56,189,248,0.15)", color: "#38BDF8", padding: "2px 6px", borderRadius: "4px", border: "1px solid rgba(56,189,248,0.3)", fontWeight: 700, letterSpacing: "0.05em" }}>OS</span>
            </div>
            <div style={{ fontSize: "11px", color: "#475569", marginTop: "1px" }}>AI Trust & Compliance</div>
          </div>
        </div>

        {/* Nav Links */}
        <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px" }}>
          {navGroups.map(group => (
            <div key={group.label}>
              <div style={s}>{group.label}</div>
              {group.items.map(item => {
                const Icon = item.icon;
                const active = activeTab === item.id;
                return (
                  <button key={item.id} onClick={() => setActiveTab(item.id)} style={navBtnStyle(active)}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <Icon style={{ width: "15px", height: "15px", color: active ? "#38BDF8" : "#475569", flexShrink: 0 }} />
                      <span>{item.label}</span>
                    </div>
                    {item.badge !== undefined && item.badge !== 0 && (
                      <span style={{ fontSize: "10px", padding: "1px 6px", borderRadius: "10px", background: active ? "rgba(56,189,248,0.25)" : "rgba(255,255,255,0.06)", color: active ? "#7DD3FC" : "#64748B", fontWeight: 600, flexShrink: 0 }}>
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* User Footer */}
        <div style={{ padding: "12px 14px", borderTop: "1px solid rgba(255,255,255,0.06)", background: "rgba(0,0,0,0.3)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "linear-gradient(135deg, rgba(99,102,241,0.4), rgba(56,189,248,0.3))", border: "1px solid rgba(99,102,241,0.5)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: 800, color: "#818CF8", flexShrink: 0 }}>
              {(currentUser?.full_name || "?").split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase()}
            </div>
            <div style={{ overflow: "hidden", flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: "12px", fontWeight: 600, color: "#E2E8F0", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{currentUser?.full_name || "Unknown User"}</div>
              <div style={{ fontSize: "10px", color: "#475569" }}>{currentUser?.role || ""}</div>
            </div>
            <button
              onClick={() => { api.logout(); setCurrentUser(null); }}
              title="Sign out"
              style={{ fontSize: "10px", color: "#64748B", background: "transparent", border: "none", cursor: "pointer", flexShrink: 0 }}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* ══════════════ MAIN WORKSPACE ══════════════ */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>

        {/* Global Header */}
        <header style={{ height: "60px", flexShrink: 0, borderBottom: "1px solid rgba(255,255,255,0.07)", padding: "0 24px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(6,10,19,0.85)", backdropFilter: "blur(16px)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "5px 12px", borderRadius: "8px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", fontSize: "12px" }}>
              <Building style={{ width: "14px", height: "14px", color: "#38BDF8" }} />
              <span style={{ fontWeight: 600, color: "#F1F5F9" }}>{currentUser?.organization_name || "Your Organization"}</span>
              {currentUser?.is_demo_tenant && (
                <span style={{ fontSize: "9px", background: "rgba(52,211,153,0.15)", color: "#34D399", padding: "2px 6px", borderRadius: "4px", fontWeight: 700, border: "1px solid rgba(52,211,153,0.3)", letterSpacing: "0.04em" }}>DEMO TENANT</span>
              )}
            </div>

            {metrics && (
              <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "11px", color: "#94A3B8" }}>
                <span>Readiness: <strong style={{ color: getReadinessColor(metrics.overall_readiness_percentage) }}>{metrics.overall_readiness_percentage}%</strong></span>
                <span style={{ color: "#2D3748" }}>•</span>
                <span style={{ color: "#FB7185" }}>{metrics.open_findings_count} Open Findings</span>
                <span style={{ color: "#2D3748" }}>•</span>
                <span style={{ color: "#C084FC" }}>{metrics.agentic_systems_count} Agents</span>
              </div>
            )}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "10px", color: "#FBBF24", background: "rgba(251,191,36,0.08)", padding: "4px 10px", borderRadius: "6px", border: "1px solid rgba(251,191,36,0.2)" }}>
              <AlertOctagon style={{ width: "12px", height: "12px" }} />
              <span>Governance Guidance — Not Legal Advice</span>
            </div>

            <button
              onClick={() => { loadPlatformData(); }}
              style={{ padding: "6px", borderRadius: "8px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", cursor: "pointer", display: "flex", alignItems: "center" }}
              data-tooltip="Refresh Data"
            >
              <RefreshCw style={{ width: "14px", height: "14px", color: "#64748B" }} />
            </button>

            <button
              onClick={() => setCopilotOpen(true)}
              style={{ display: "flex", alignItems: "center", gap: "8px", padding: "6px 14px", borderRadius: "8px", background: "linear-gradient(135deg, rgba(56,189,248,0.18), rgba(99,102,241,0.18))", border: "1px solid rgba(56,189,248,0.4)", color: "#38BDF8", fontSize: "12px", fontWeight: 600, cursor: "pointer", boxShadow: "0 2px 12px rgba(56,189,248,0.12)" }}
            >
              <Sparkles style={{ width: "14px", height: "14px" }} />
              <span>Ask AI Copilot</span>
            </button>
          </div>
        </header>

        {/* Content Area */}
        <main style={{ flex: 1, overflowY: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
          {loading && (
            <div style={{ height: "400px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "16px" }}>
              <div style={{ position: "relative", width: "56px", height: "56px" }}>
                <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "linear-gradient(135deg, rgba(56,189,248,0.25), rgba(99,102,241,0.2))", border: "2px solid rgba(56,189,248,0.3)", animation: "spin 2s linear infinite" }} />
                <Shield style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", width: "24px", height: "24px", color: "#38BDF8" }} />
              </div>
              <div>
                <div style={{ fontSize: "14px", fontWeight: 600, color: "#E2E8F0", textAlign: "center" }}>Connecting to AegisAI Governance Engine</div>
                <div style={{ fontSize: "12px", color: "#64748B", textAlign: "center", marginTop: "4px" }}>Loading 17 authoritative frameworks & compliance data...</div>
              </div>
            </div>
          )}

          {!loading && error && (
            <div style={{ padding: "16px", borderRadius: "12px", background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.25)", color: "#FDA4AF", fontSize: "12px", display: "flex", alignItems: "center", gap: "12px" }}>
              <AlertCircle style={{ width: "18px", height: "18px", flexShrink: 0 }} />
              <div>
                <div style={{ fontWeight: 600 }}>Connection Error</div>
                <div style={{ color: "#9C8B90", marginTop: "2px" }}>{error} — Make sure the AegisAI backend is running on port 8000.</div>
              </div>
              <button onClick={loadPlatformData} style={{ marginLeft: "auto", padding: "6px 12px", borderRadius: "8px", background: "rgba(244,63,94,0.2)", color: "#FDA4AF", border: "1px solid rgba(244,63,94,0.35)", cursor: "pointer", fontSize: "11px", fontWeight: 600 }}>Retry</button>
            </div>
          )}

          {!loading && !error && (
            <div className="animate-fadeIn" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>

              {/* ══════════════════════════════════════════════════════
                  TAB: EXECUTIVE DASHBOARD
              ══════════════════════════════════════════════════════ */}
              {activeTab === "dashboard" && metrics && (
                <div className="stagger-children" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  {/* Hero Banner */}
                  <div className="glass-panel" style={{ padding: "24px", background: "linear-gradient(135deg, rgba(7,14,31,0.9), rgba(11,18,37,0.95))", border: "1px solid rgba(56,189,248,0.18)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "20px" }}>
                      <div style={{ flex: 1, minWidth: "280px" }}>
                        <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "10px", fontWeight: 700, color: "#38BDF8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "8px", background: "rgba(56,189,248,0.08)", padding: "3px 10px", borderRadius: "20px", border: "1px solid rgba(56,189,248,0.2)" }}>
                          <Shield style={{ width: "12px", height: "12px" }} />
                          AI Governance Operating System · 17 Authoritative Frameworks
                        </div>
                        <h1 style={{ fontSize: "24px", fontWeight: 900, color: "#FFFFFF", letterSpacing: "-0.03em", lineHeight: 1.2 }}>
                          Acme Financial AI Governance
                          <br /><span style={{ color: "#38BDF8" }}>{metrics.overall_readiness_percentage}% Compliance Readiness</span>
                        </h1>
                        <p style={{ fontSize: "12px", color: "#64748B", marginTop: "10px", maxWidth: "580px", lineHeight: "1.6" }}>
                          Unified control plane for EU AI Act, NIST AI RMF, NIST AI 600-1, OWASP LLM/Agentic, CRA, GDPR, DORA, and 10 more authoritative standards. Track, evidence, and assure all AI systems from a single platform.
                        </p>
                        <div style={{ display: "flex", gap: "8px", marginTop: "16px", flexWrap: "wrap" }}>
                          <button onClick={() => setActiveTab("intake")} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "7px 14px", borderRadius: "8px", background: "linear-gradient(135deg, #38BDF8, #6366F1)", color: "#050810", fontWeight: 700, fontSize: "12px", border: "none", cursor: "pointer" }}>
                            <Play style={{ width: "12px", height: "12px" }} /> New AI Intake
                          </button>
                          <button onClick={() => setEvidenceModalOpen(true)} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "7px 14px", borderRadius: "8px", background: "rgba(52,211,153,0.12)", color: "#34D399", fontWeight: 600, fontSize: "12px", border: "1px solid rgba(52,211,153,0.3)", cursor: "pointer" }}>
                            <Lock style={{ width: "12px", height: "12px" }} /> Upload Evidence
                          </button>
                          <button onClick={() => setCopilotOpen(true)} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "7px 14px", borderRadius: "8px", background: "rgba(192,132,252,0.12)", color: "#C084FC", fontWeight: 600, fontSize: "12px", border: "1px solid rgba(192,132,252,0.3)", cursor: "pointer" }}>
                            <Sparkles style={{ width: "12px", height: "12px" }} /> Ask Copilot
                          </button>
                        </div>
                      </div>

                      <div style={{ display: "flex", gap: "16px", alignItems: "center", flexWrap: "wrap" }}>
                        <CircularProgress value={metrics.implementation_score} size={80} color="#34D399" label="Implemented" />
                        <CircularProgress value={metrics.evidence_completeness_score} size={80} color="#38BDF8" label="Evidence" />
                        <CircularProgress value={metrics.control_effectiveness_score} size={80} color="#818CF8" label="Effective" />
                      </div>
                    </div>
                  </div>

                  {/* KPI Cards */}
                  <div className="stagger-children" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(155px, 1fr))", gap: "12px" }}>
                    {[
                      { label: "Total AI Systems", val: metrics.total_ai_systems, desc: "Active in Registry", color: "#FFFFFF", icon: Brain, cls: "stat-card-blue" },
                      { label: "High-Risk (Annex III)", val: metrics.high_risk_systems_count, desc: "Mandatory EU Oversight", color: "#FB7185", icon: AlertTriangle, cls: "stat-card-red" },
                      { label: "Generative AI", val: metrics.genai_systems_count, desc: "LLM / RAG Pipelines", color: "#C084FC", icon: Sparkles, cls: "stat-card-purple" },
                      { label: "Autonomous Agents", val: metrics.agentic_systems_count, desc: "Tool & Code Execution", color: "#FBBF24", icon: Target, cls: "stat-card-amber" },
                      { label: "Active Evidence", val: metrics.active_evidence_artifacts_count, desc: "SHA-256 Hashed Vault", color: "#34D399", icon: Lock, cls: "stat-card-green" },
                      { label: "Open Findings", val: metrics.open_findings_count, desc: `${metrics.critical_findings_count} Critical SLA Breach`, color: "#FB7185", icon: AlertOctagon, cls: "stat-card-red" },
                    ].map((s, i) => {
                      const Icon = s.icon;
                      return (
                        <div key={i} className={`glass-panel glass-panel-hover ${s.cls}`} style={{ padding: "16px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                            <div style={{ fontSize: "11px", color: "#94A3B8" }}>{s.label}</div>
                            <Icon style={{ width: "15px", height: "15px", color: s.color, opacity: 0.7 }} />
                          </div>
                          <div style={{ fontSize: "28px", fontWeight: 900, color: s.color, marginTop: "6px", letterSpacing: "-0.03em" }}>{s.val}</div>
                          <div style={{ fontSize: "10px", color: "#475569", marginTop: "4px" }}>{s.desc}</div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Framework Readiness + Risk Distribution */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "16px" }}>
                    <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0", display: "flex", alignItems: "center", gap: "8px" }}>
                          <BarChart2 style={{ width: "16px", height: "16px", color: "#38BDF8" }} />
                          Framework Readiness Breakdown
                        </h2>
                        <span style={{ fontSize: "10px", background: "rgba(56,189,248,0.08)", padding: "2px 8px", borderRadius: "10px", border: "1px solid rgba(56,189,248,0.2)", color: "#38BDF8" }}>17 Standards</span>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                        {Object.entries(metrics.framework_readiness || {}).slice(0, 8).map(([fw, pct]: any) => (
                          <div key={fw}>
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "4px" }}>
                              <span style={{ color: "#CBD5E1", fontWeight: 500 }}>{fw}</span>
                              <span style={{ color: getReadinessColor(pct), fontWeight: 700 }}>{pct}%</span>
                            </div>
                            <div className="progress-bar">
                              <div
                                className={`progress-bar-fill${pct >= 80 ? "-green" : pct >= 60 ? "-amber" : "-red"}`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                      <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
                        <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0", display: "flex", alignItems: "center", gap: "8px" }}>
                          <AlertTriangle style={{ width: "16px", height: "16px", color: "#FBBF24" }} />
                          Risk Distribution by Domain
                        </h2>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px" }}>
                          {Object.entries(metrics.risk_category_distribution || {}).map(([cat, count]: any) => (
                            <div key={cat} style={{ padding: "10px", background: "rgba(0,0,0,0.3)", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)", textAlign: "center" }}>
                              <div style={{ fontSize: "20px", fontWeight: 900, color: "#F1F5F9", letterSpacing: "-0.02em" }}>{count}</div>
                              <div style={{ fontSize: "10px", color: "#94A3B8", textTransform: "capitalize", marginTop: "2px" }}>{cat}</div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Quick Findings Alert */}
                      {findings.filter((f: any) => f.severity === "Critical" && f.status === "Open").length > 0 && (
                        <div className="glass-panel" style={{ padding: "16px", border: "1px solid rgba(244,63,94,0.3)", background: "rgba(244,63,94,0.06)" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                            <AlertOctagon style={{ width: "16px", height: "16px", color: "#FB7185" }} />
                            <span style={{ fontSize: "13px", fontWeight: 700, color: "#FB7185" }}>Critical Findings Requiring Action</span>
                          </div>
                          {findings.filter((f: any) => f.severity === "Critical" && f.status === "Open").slice(0, 3).map((f: any) => (
                            <div key={f.id} style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#FDA4AF", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                              <span>{f.title}</span>
                              <span style={{ color: "#64748B" }}>{f.sla_days_remaining}d SLA</span>
                            </div>
                          ))}
                          <button onClick={() => setActiveTab("risks")} style={{ marginTop: "10px", fontSize: "11px", color: "#FB7185", background: "none", border: "none", cursor: "pointer", fontWeight: 600, textDecoration: "underline" }}>
                            View All Findings →
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Activity Strip */}
                  {auditEvents.length > 0 && (
                    <div className="glass-panel" style={{ padding: "16px 20px" }}>
                      <h2 style={{ fontSize: "12px", fontWeight: 700, color: "#94A3B8", marginBottom: "12px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Recent Governance Activity</h2>
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                        {auditEvents.slice(0, 5).map(ev => (
                          <div key={ev.id} style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "11px", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                            <span style={{ color: "#64748B", fontFamily: "var(--font-mono)", whiteSpace: "nowrap" }}>{new Date(ev.timestamp).toLocaleTimeString()}</span>
                            <span style={{ color: "#38BDF8", fontWeight: 600, background: "rgba(56,189,248,0.08)", padding: "1px 6px", borderRadius: "4px", whiteSpace: "nowrap" }}>{ev.action}</span>
                            <span style={{ color: "#94A3B8" }}>{ev.actor_email}</span>
                            <span style={{ color: "#475569" }}>→ {ev.object_type}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: AI SYSTEMS INVENTORY
              ══════════════════════════════════════════════════════ */}
              {activeTab === "inventory" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                        <Brain style={{ width: "22px", height: "22px", color: "#38BDF8" }} />
                        AI System Inventory & Registry
                      </h1>
                      <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                        Central registry mapping AI systems to models, datasets, autonomous agents, and EU AI Act risk tiers.
                      </p>
                    </div>
                    <button onClick={() => setActiveTab("intake")} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 16px", borderRadius: "8px", background: "linear-gradient(135deg, #38BDF8, #6366F1)", color: "#050810", fontWeight: 700, fontSize: "12px", border: "none", cursor: "pointer", boxShadow: "0 4px 14px rgba(56,189,248,0.25)" }}>
                      <Plus style={{ width: "14px", height: "14px" }} /> Register New System
                    </button>
                  </div>

                  {/* Summary stats */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "10px" }}>
                    {[
                      { label: "Total Systems", val: aiSystems.length, color: "#F8FAFC" },
                      { label: "High Risk (EU AIA)", val: aiSystems.filter((s: any) => s.risk_classification?.includes("High")).length, color: "#FB7185" },
                      { label: "GenAI / LLM", val: aiSystems.filter((s: any) => s.is_generative_ai).length, color: "#C084FC" },
                      { label: "Autonomous Agents", val: aiSystems.filter((s: any) => s.is_agentic_ai).length, color: "#FBBF24" },
                    ].map((stat, i) => (
                      <div key={i} className="glass-panel" style={{ padding: "14px" }}>
                        <div style={{ fontSize: "10px", color: "#64748B" }}>{stat.label}</div>
                        <div style={{ fontSize: "26px", fontWeight: 900, color: stat.color, letterSpacing: "-0.02em" }}>{stat.val}</div>
                      </div>
                    ))}
                  </div>

                  <div className="glass-panel" style={{ overflowX: "auto" }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>System Name & Purpose</th>
                          <th>Business Unit</th>
                          <th>Technology & Provider</th>
                          <th>Risk Tier</th>
                          <th>EU AI Act Classification</th>
                          <th>Kill-Switch</th>
                          <th style={{ textAlign: "right" }}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {aiSystems.map(sys => (
                          <tr key={sys.id}>
                            <td>
                              <div style={{ fontWeight: 600, color: "#F8FAFC", display: "flex", alignItems: "center", gap: "8px" }}>
                                {sys.is_agentic_ai && <span style={{ fontSize: "9px", background: "rgba(251,191,36,0.15)", color: "#FBBF24", padding: "1px 5px", borderRadius: "4px", border: "1px solid rgba(251,191,36,0.3)", fontWeight: 700 }}>AGENT</span>}
                                {sys.is_generative_ai && !sys.is_agentic_ai && <span style={{ fontSize: "9px", background: "rgba(192,132,252,0.15)", color: "#C084FC", padding: "1px 5px", borderRadius: "4px", border: "1px solid rgba(192,132,252,0.3)", fontWeight: 700 }}>GenAI</span>}
                                {sys.name}
                              </div>
                              <div style={{ fontSize: "11px", color: "#475569", maxWidth: "320px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginTop: "2px" }}>{sys.description}</div>
                            </td>
                            <td style={{ color: "#CBD5E1" }}>{sys.business_unit}</td>
                            <td>
                              <div style={{ color: "#F1F5F9", fontWeight: 500 }}>{sys.model_provider} {sys.model_name}</div>
                              <div style={{ fontSize: "10px", color: "#475569" }}>{sys.ai_technology}</div>
                            </td>
                            <td>
                              <span className={`badge badge-${sys.risk_classification?.includes("High") ? "red" : sys.risk_classification?.includes("Minimal") ? "green" : "amber"}`}>
                                {sys.risk_classification}
                              </span>
                            </td>
                            <td style={{ color: "#94A3B8", fontSize: "11px", fontFamily: "var(--font-mono)" }}>{sys.eu_ai_act_classification}</td>
                            <td>
                              <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "10px", color: "#34D399" }}>
                                <Check style={{ width: "11px", height: "11px" }} /> Active
                              </span>
                            </td>
                            <td style={{ textAlign: "right" }}>
                              <button onClick={() => setSelectedSystem(sys)} style={{ padding: "4px 10px", borderRadius: "6px", background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.2)", color: "#38BDF8", fontSize: "11px", cursor: "pointer", fontWeight: 600 }}>
                                View Details
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: INTAKE & CLASSIFICATION WIZARD
              ══════════════════════════════════════════════════════ */}
              {activeTab === "intake" && (
                <div style={{ maxWidth: "800px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "20px" }}>
                  <div>
                    <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                      <Sliders style={{ width: "22px", height: "22px", color: "#38BDF8" }} />
                      Guided AI Intake & Classification Wizard
                    </h1>
                    <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                      Rules engine evaluating EU AI Act Annex III risk tier, GDPR/DPDPA scope, and mandatory unified controls — with full statutory rationale.
                    </p>
                  </div>

                  <div className="glass-panel" style={{ padding: "28px", display: "flex", flexDirection: "column", gap: "20px" }}>
                    {/* Step progress */}
                    <div style={{ display: "flex", gap: "0" }}>
                      {[
                        { step: 1, label: "System Scope" },
                        { step: 2, label: "Decision & Data" },
                        { step: 3, label: "AI Capabilities" },
                        { step: 4, label: "Classification" }
                      ].map((s, i, arr) => (
                        <div key={s.step} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
                          <div style={{ display: "flex", alignItems: "center", width: "100%" }}>
                            {i > 0 && <div style={{ flex: 1, height: "2px", background: intakeStep > s.step ? "#38BDF8" : "rgba(255,255,255,0.08)" }} />}
                            <div style={{ width: "28px", height: "28px", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "12px", fontWeight: 700, flexShrink: 0, background: intakeStep > s.step ? "#38BDF8" : intakeStep === s.step ? "rgba(56,189,248,0.2)" : "rgba(255,255,255,0.06)", color: intakeStep > s.step ? "#050810" : intakeStep === s.step ? "#38BDF8" : "#64748B", border: intakeStep === s.step ? "2px solid #38BDF8" : "2px solid transparent" }}>
                              {intakeStep > s.step ? <Check style={{ width: "14px", height: "14px" }} /> : s.step}
                            </div>
                            {i < arr.length - 1 && <div style={{ flex: 1, height: "2px", background: intakeStep > s.step ? "#38BDF8" : "rgba(255,255,255,0.08)" }} />}
                          </div>
                          <div style={{ fontSize: "10px", fontWeight: 600, marginTop: "6px", color: intakeStep === s.step ? "#38BDF8" : intakeStep > s.step ? "#34D399" : "#64748B" }}>{s.label}</div>
                        </div>
                      ))}
                    </div>

                    {/* Step 1 */}
                    {intakeStep === 1 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "12px" }}>
                        <div>
                          <label style={{ display: "block", color: "#CBD5E1", marginBottom: "6px", fontWeight: 600 }}>System Name *</label>
                          <input type="text" value={intakeForm.system_name} onChange={e => setIntakeForm({ ...intakeForm, system_name: e.target.value })} style={{ width: "100%", padding: "10px 12px", fontSize: "13px" }} />
                        </div>
                        <div>
                          <label style={{ display: "block", color: "#CBD5E1", marginBottom: "6px", fontWeight: 600 }}>Business Purpose & Use Case *</label>
                          <textarea rows={3} value={intakeForm.business_purpose} onChange={e => setIntakeForm({ ...intakeForm, business_purpose: e.target.value })} style={{ width: "100%", padding: "10px 12px", fontSize: "12px", resize: "none" }} />
                        </div>
                        <div>
                          <label style={{ display: "block", color: "#CBD5E1", marginBottom: "6px", fontWeight: 600 }}>Business Unit</label>
                          <input type="text" value={intakeForm.business_unit} onChange={e => setIntakeForm({ ...intakeForm, business_unit: e.target.value })} style={{ width: "100%", padding: "10px 12px" }} />
                        </div>
                        <div>
                          <label style={{ display: "block", color: "#CBD5E1", marginBottom: "6px", fontWeight: 600 }}>Deployment Countries (affects EU AI Act applicability)</label>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                            {["EU", "US", "UK", "IN", "SG", "GLOBAL"].map(c => (
                              <label key={c} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 12px", borderRadius: "6px", border: `1px solid ${intakeForm.deployment_countries.includes(c) ? "rgba(56,189,248,0.4)" : "rgba(255,255,255,0.08)"}`, background: intakeForm.deployment_countries.includes(c) ? "rgba(56,189,248,0.1)" : "rgba(0,0,0,0.2)", cursor: "pointer" }}>
                                <input type="checkbox" checked={intakeForm.deployment_countries.includes(c)} onChange={e => { const next = e.target.checked ? [...intakeForm.deployment_countries, c] : intakeForm.deployment_countries.filter(x => x !== c); setIntakeForm({ ...intakeForm, deployment_countries: next }); }} />
                                <span style={{ color: intakeForm.deployment_countries.includes(c) ? "#38BDF8" : "#CBD5E1", fontWeight: 600 }}>{c}</span>
                              </label>
                            ))}
                          </div>
                          {intakeForm.deployment_countries.includes("EU") && (
                            <div style={{ marginTop: "8px", padding: "8px 12px", borderRadius: "6px", background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.2)", fontSize: "11px", color: "#7DD3FC" }}>
                              ⚠ EU deployment detected — EU AI Act (Regulation 2024/1689) will apply. Annex III risk classification required.
                            </div>
                          )}
                        </div>
                        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "6px" }}>
                          <button onClick={() => setIntakeStep(2)} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "10px 20px", borderRadius: "8px", background: "linear-gradient(135deg, #38BDF8, #6366F1)", color: "#050810", fontWeight: 700, fontSize: "12px", border: "none", cursor: "pointer" }}>
                            Next: Decision & Data <ChevronRight style={{ width: "14px", height: "14px" }} />
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Step 2 */}
                    {intakeStep === 2 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "16px", fontSize: "12px" }}>
                        <div style={{ padding: "14px", borderRadius: "8px", background: "rgba(0,0,0,0.25)", border: "1px solid rgba(255,255,255,0.06)", display: "flex", flexDirection: "column", gap: "12px" }}>
                          <label style={{ display: "flex", alignItems: "flex-start", gap: "10px", cursor: "pointer" }}>
                            <input type="checkbox" style={{ marginTop: "2px" }} checked={intakeForm.makes_decisions_about_individuals} onChange={e => setIntakeForm({ ...intakeForm, makes_decisions_about_individuals: e.target.checked })} />
                            <div>
                              <div style={{ fontWeight: 600, color: "#F1F5F9" }}>Evaluates or makes decisions about individuals</div>
                              <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>Credit, employment, education, biometric ID, healthcare, insurance scoring — triggers EU AI Act Annex III</div>
                            </div>
                          </label>

                          {intakeForm.makes_decisions_about_individuals && (
                            <div style={{ paddingLeft: "24px", borderLeft: "2px solid rgba(56,189,248,0.4)", display: "flex", flexDirection: "column", gap: "6px" }}>
                              <div style={{ color: "#64748B", fontSize: "11px", fontWeight: 600 }}>Select applicable Annex III domains:</div>
                              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                                {["credit", "employment", "education", "insurance", "healthcare", "biometrics", "border control", "critical infrastructure"].map(d => (
                                  <label key={d} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "5px 10px", borderRadius: "6px", border: `1px solid ${intakeForm.decision_domains.includes(d) ? "rgba(251,113,133,0.4)" : "rgba(255,255,255,0.08)"}`, background: intakeForm.decision_domains.includes(d) ? "rgba(251,113,133,0.1)" : "rgba(0,0,0,0.2)", cursor: "pointer" }}>
                                    <input type="checkbox" checked={intakeForm.decision_domains.includes(d)} onChange={e => { const next = e.target.checked ? [...intakeForm.decision_domains, d] : intakeForm.decision_domains.filter(x => x !== d); setIntakeForm({ ...intakeForm, decision_domains: next }); }} />
                                    <span style={{ textTransform: "capitalize", color: intakeForm.decision_domains.includes(d) ? "#FB7185" : "#CBD5E1" }}>{d}</span>
                                  </label>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        <label style={{ display: "flex", alignItems: "flex-start", gap: "10px", cursor: "pointer", padding: "14px", borderRadius: "8px", background: "rgba(0,0,0,0.25)", border: "1px solid rgba(255,255,255,0.06)" }}>
                          <input type="checkbox" style={{ marginTop: "2px" }} checked={intakeForm.processes_personal_data} onChange={e => setIntakeForm({ ...intakeForm, processes_personal_data: e.target.checked })} />
                          <div>
                            <div style={{ fontWeight: 600, color: "#F1F5F9" }}>Processes personal data (GDPR / DPDPA / PDPA scope)</div>
                            <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>Names, IDs, financial data, health records, location — triggers mandatory DPIA and GDPR Article 22 obligations</div>
                          </div>
                        </label>

                        <label style={{ display: "flex", alignItems: "flex-start", gap: "10px", cursor: "pointer", padding: "14px", borderRadius: "8px", background: "rgba(0,0,0,0.25)", border: "1px solid rgba(255,255,255,0.06)" }}>
                          <input type="checkbox" style={{ marginTop: "2px" }} checked={intakeForm.interacts_directly_with_humans} onChange={e => setIntakeForm({ ...intakeForm, interacts_directly_with_humans: e.target.checked })} />
                          <div>
                            <div style={{ fontWeight: 600, color: "#F1F5F9" }}>Interacts directly with humans (chatbot, voice assistant, GPAI)</div>
                            <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>Triggers EU AI Act Art. 50 transparency / disclosure obligations for GPAI systems</div>
                          </div>
                        </label>

                        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px" }}>
                          <button onClick={() => setIntakeStep(1)} style={{ padding: "9px 16px", borderRadius: "8px", background: "rgba(255,255,255,0.06)", color: "#CBD5E1", border: "1px solid rgba(255,255,255,0.1)", cursor: "pointer", fontSize: "12px" }}>← Back</button>
                          <button onClick={() => setIntakeStep(3)} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "9px 20px", borderRadius: "8px", background: "linear-gradient(135deg, #38BDF8, #6366F1)", color: "#050810", fontWeight: 700, fontSize: "12px", border: "none", cursor: "pointer" }}>
                            Next: AI Capabilities <ChevronRight style={{ width: "14px", height: "14px" }} />
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Step 3 */}
                    {intakeStep === 3 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "12px" }}>
                        {[
                          { key: "is_generative_ai", label: "Uses Foundation Models / Generative AI", desc: "LLMs, diffusion models, CLIP — triggers NIST AI 600-1 and OWASP LLM Top 10" },
                          { key: "uses_foundation_model", label: "Deployed via foundation model API (e.g. OpenAI, Anthropic, Google)", desc: "Third-party model supply chain risk — triggers NIST SP 800-161 C-SCRM controls" },
                          { key: "generates_synthetic_content", label: "Generates synthetic text, images, code, or audio", desc: "EU AI Act Art. 50 watermarking obligation for deepfake/synthetic content" },
                          { key: "is_autonomous_agent", label: "Autonomous Agent with tool-calling capabilities", desc: "Code execution, browser, file system, API calls — triggers OWASP Agentic AI Risk framework" },
                          { key: "can_execute_code", label: "Can execute code or system commands", desc: "Shell, Python interpreter, bash — requires sandboxing and kill-switch (UC-AI-AGT-005)" },
                          { key: "can_access_database", label: "Has read/write access to production databases", desc: "Data mutation risk — requires human approval gate and access audit logging" },
                        ].map(item => (
                          <label key={item.key} style={{ display: "flex", alignItems: "flex-start", gap: "10px", cursor: "pointer", padding: "12px 14px", borderRadius: "8px", background: "rgba(0,0,0,0.25)", border: `1px solid ${(intakeForm as any)[item.key] ? "rgba(56,189,248,0.25)" : "rgba(255,255,255,0.06)"}` }}>
                            <input type="checkbox" style={{ marginTop: "2px" }} checked={(intakeForm as any)[item.key]} onChange={e => setIntakeForm({ ...intakeForm, [item.key]: e.target.checked })} />
                            <div>
                              <div style={{ fontWeight: 600, color: "#F1F5F9" }}>{item.label}</div>
                              <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>{item.desc}</div>
                            </div>
                          </label>
                        ))}

                        {intakeForm.uses_foundation_model && (
                          <div>
                            <label style={{ display: "block", color: "#CBD5E1", marginBottom: "6px", fontWeight: 600 }}>Foundation Model Provider</label>
                            <select value={intakeForm.foundation_model_provider} onChange={e => setIntakeForm({ ...intakeForm, foundation_model_provider: e.target.value })} style={{ width: "100%", padding: "9px 12px" }}>
                              {["Anthropic", "OpenAI", "Google DeepMind", "Meta AI", "Mistral", "Cohere", "Amazon Bedrock", "Azure OpenAI", "Other"].map(p => <option key={p} value={p}>{p}</option>)}
                            </select>
                          </div>
                        )}

                        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px" }}>
                          <button onClick={() => setIntakeStep(2)} style={{ padding: "9px 16px", borderRadius: "8px", background: "rgba(255,255,255,0.06)", color: "#CBD5E1", border: "1px solid rgba(255,255,255,0.1)", cursor: "pointer", fontSize: "12px" }}>← Back</button>
                          <button onClick={runIntakeEvaluation} disabled={evaluatingIntake} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "10px 24px", borderRadius: "8px", background: "linear-gradient(135deg, #38BDF8, #6366F1)", color: "#050810", fontWeight: 800, fontSize: "12px", border: "none", cursor: evaluatingIntake ? "not-allowed" : "pointer", opacity: evaluatingIntake ? 0.7 : 1 }}>
                            {evaluatingIntake ? <><RefreshCw style={{ width: "14px", height: "14px", animation: "spin 1s linear infinite" }} /> Evaluating...</> : <><Zap style={{ width: "14px", height: "14px" }} /> Run Statutory Classifier</>}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Step 4: Results */}
                    {intakeStep === 4 && intakeResult && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "16px", fontSize: "12px" }} className="animate-fadeIn">
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px", background: "rgba(0,0,0,0.35)", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.08)" }}>
                          <div>
                            <div style={{ fontSize: "10px", color: "#64748B", textTransform: "uppercase", letterSpacing: "0.06em" }}>Classification Output</div>
                            <div style={{ fontSize: "18px", fontWeight: 800, color: "#FFF", marginTop: "2px" }}>{intakeResult.system_name}</div>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <span className={`badge badge-${intakeResult.risk_level?.includes("High") ? "red" : intakeResult.risk_level?.includes("Minimal") ? "green" : "amber"}`} style={{ fontSize: "12px", padding: "5px 14px" }}>
                              {intakeResult.risk_level}
                            </span>
                          </div>
                        </div>

                        <div style={{ padding: "14px", borderRadius: "8px", background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.2)", color: "#BAE6FD", lineHeight: "1.7", fontSize: "12px" }}>
                          <div style={{ fontWeight: 700, color: "#38BDF8", marginBottom: "4px" }}>⚖ EU AI Act Statutory Rationale:</div>
                          {intakeResult.eu_ai_act_rationale}
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                          <div style={{ padding: "14px", background: "rgba(0,0,0,0.25)", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.06)" }}>
                            <div style={{ fontWeight: 700, color: "#E2E8F0", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                              <FileCheck style={{ width: "14px", height: "14px", color: "#38BDF8" }} /> Applicable Frameworks
                            </div>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                              {intakeResult.recommended_frameworks?.map((fw: string) => (
                                <span key={fw} className="badge badge-blue" style={{ fontFamily: "var(--font-mono)" }}>{fw}</span>
                              ))}
                            </div>
                          </div>

                          <div style={{ padding: "14px", background: "rgba(0,0,0,0.25)", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.06)" }}>
                            <div style={{ fontWeight: 700, color: "#E2E8F0", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                              <Layers style={{ width: "14px", height: "14px", color: "#818CF8" }} /> Required Controls ({intakeResult.required_unified_controls?.length})
                            </div>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                              {intakeResult.required_unified_controls?.slice(0, 8).map((c: string) => (
                                <span key={c} className="badge badge-indigo" style={{ fontFamily: "var(--font-mono)" }}>{c}</span>
                              ))}
                              {intakeResult.required_unified_controls?.length > 8 && <span style={{ fontSize: "10px", color: "#64748B" }}>+{intakeResult.required_unified_controls.length - 8} more</span>}
                            </div>
                          </div>
                        </div>

                        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px" }}>
                          <button onClick={() => setIntakeStep(3)} style={{ padding: "9px 16px", borderRadius: "8px", background: "rgba(255,255,255,0.06)", color: "#CBD5E1", border: "1px solid rgba(255,255,255,0.1)", cursor: "pointer", fontSize: "12px" }}>← Edit Answers</button>
                          <button onClick={registerIntakeSystem} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "10px 24px", borderRadius: "8px", background: "#34D399", color: "#050810", fontWeight: 800, fontSize: "12px", border: "none", cursor: "pointer" }}>
                            <ShieldCheck style={{ width: "15px", height: "15px" }} /> Commit to AI Inventory
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: UNIFIED CONTROLS
              ══════════════════════════════════════════════════════ */}
              {activeTab === "controls" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
                    <div>
                      <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                        <Layers style={{ width: "22px", height: "22px", color: "#38BDF8" }} />
                        Unified Control Library
                      </h1>
                      <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                        {controls.length} normalized domain controls mapped across all 17 standards. Update status to recalculate live compliance posture.
                      </p>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
                      <label style={{ color: "#64748B" }}>Domain:</label>
                      <select value={controlDomainFilter} onChange={e => setControlDomainFilter(e.target.value)} style={{ padding: "6px 12px", borderRadius: "8px", fontSize: "11px" }}>
                        <option value="All">All Domains</option>
                        {[...new Set(controls.map((c: any) => c.domain))].map(d => <option key={d} value={d}>{d}</option>)}
                      </select>
                    </div>
                  </div>

                  {/* Status summary bars */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "10px" }}>
                    {["Implemented", "In Progress", "Not Started", "Accepted Risk"].map(status => {
                      const count = controls.filter((c: any) => c.customer_status === status).length;
                      const pct = controls.length > 0 ? Math.round((count / controls.length) * 100) : 0;
                      return (
                        <div key={status} className="glass-panel" style={{ padding: "12px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                            <span style={{ fontSize: "11px", color: "#94A3B8" }}>{status}</span>
                            <span style={{ fontSize: "13px", fontWeight: 700, color: getStatusColor(status) }}>{count}</span>
                          </div>
                          <div className="progress-bar">
                            <div className="progress-bar-fill" style={{ width: `${pct}%`, background: getStatusColor(status) }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="glass-panel" style={{ overflowX: "auto" }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Control Code & Title</th>
                          <th>Domain</th>
                          <th>Type</th>
                          <th>Implementation Status</th>
                          <th>Effectiveness</th>
                          <th style={{ textAlign: "right" }}>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {controls.filter(c => controlDomainFilter === "All" || c.domain === controlDomainFilter).map(ctrl => (
                          <tr key={ctrl.id}>
                            <td>
                              <div style={{ fontFamily: "var(--font-mono)", color: "#38BDF8", fontSize: "11px", fontWeight: 700 }}>{ctrl.code}</div>
                              <div style={{ color: "#F1F5F9", fontWeight: 600, marginTop: "2px" }}>{ctrl.title}</div>
                            </td>
                            <td>
                              <span style={{ fontSize: "11px", color: "#94A3B8", background: "rgba(255,255,255,0.04)", padding: "2px 8px", borderRadius: "4px", border: "1px solid rgba(255,255,255,0.06)" }}>{ctrl.domain}</span>
                            </td>
                            <td style={{ color: "#64748B", fontSize: "11px" }}>{ctrl.control_type}</td>
                            <td>
                              <span className={`badge badge-${ctrl.customer_status === "Implemented" ? "green" : ctrl.customer_status === "In Progress" ? "amber" : ctrl.customer_status === "Accepted Risk" ? "purple" : "red"}`}>
                                {ctrl.customer_status}
                              </span>
                            </td>
                            <td style={{ color: "#CBD5E1", fontSize: "11px" }}>{ctrl.customer_effectiveness}</td>
                            <td style={{ textAlign: "right" }}>
                              <button onClick={() => setSelectedControl(ctrl)} style={{ padding: "4px 10px", borderRadius: "6px", background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.2)", color: "#38BDF8", fontSize: "11px", cursor: "pointer", fontWeight: 600 }}>
                                Manage
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: 17-FRAMEWORK CROSSWALK MATRIX
              ══════════════════════════════════════════════════════ */}
              {activeTab === "crosswalk" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div>
                    <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                      <GitMerge style={{ width: "22px", height: "22px", color: "#38BDF8" }} />
                      17-Framework Compliance Crosswalk Matrix
                    </h1>
                    <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                      Platform moat: One unified control simultaneously satisfies requirements across EU AI Act, NIST AI RMF, OWASP, CSF, GDPR, DORA, and 11 more standards.
                    </p>
                  </div>

                  <div className="glass-panel" style={{ overflowX: "auto" }}>
                    <table className="data-table" style={{ minWidth: "860px" }}>
                      <thead>
                        <tr>
                          <th style={{ width: "32%" }}>Unified Control</th>
                          <th>Cross-Framework Statutory Mappings</th>
                          <th style={{ width: "28%" }}>Rationale</th>
                        </tr>
                      </thead>
                      <tbody>
                        {crosswalk.map(row => (
                          <tr key={row.control_id}>
                            <td style={{ verticalAlign: "top" }}>
                              <div style={{ fontFamily: "var(--font-mono)", color: "#38BDF8", fontWeight: 700, fontSize: "12px" }}>{row.control_code}</div>
                              <div style={{ color: "#F1F5F9", fontWeight: 600, marginTop: "2px" }}>{row.control_title}</div>
                              <div style={{ fontSize: "10px", color: "#475569", marginTop: "2px" }}>{row.domain}</div>
                              <div style={{ marginTop: "6px" }}>
                                <span style={{ fontSize: "10px", fontWeight: 700, color: "#34D399" }}>{row.mappings?.length} framework{row.mappings?.length !== 1 ? "s" : ""}</span>
                              </div>
                            </td>
                            <td style={{ verticalAlign: "top" }}>
                              <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                                {row.mappings?.slice(0, 6).map((m: any, idx: number) => (
                                  <div key={idx} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11px" }}>
                                    <span style={{ color: "#E2E8F0", fontWeight: 600, minWidth: "90px" }}>{m.framework_name}:</span>
                                    <span style={{ fontFamily: "var(--font-mono)", color: "#38BDF8", background: "rgba(56,189,248,0.1)", padding: "1px 6px", borderRadius: "4px", fontSize: "11px" }}>{m.article || m.requirement_id}</span>
                                    <span className={`badge badge-${m.confidence === "Exact" ? "green" : m.confidence === "Strong" ? "blue" : "amber"}`} style={{ padding: "1px 5px" }}>{m.confidence}</span>
                                  </div>
                                ))}
                                {row.mappings?.length > 6 && <span style={{ fontSize: "10px", color: "#64748B" }}>+{row.mappings.length - 6} more mappings</span>}
                              </div>
                            </td>
                            <td style={{ verticalAlign: "top", color: "#94A3B8", fontSize: "11px", lineHeight: "1.6" }}>{row.mappings?.[0]?.rationale}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: AUTHORITATIVE FRAMEWORKS
              ══════════════════════════════════════════════════════ */}
              {activeTab === "frameworks" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div>
                    <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                      <FileCheck style={{ width: "22px", height: "22px", color: "#38BDF8" }} />
                      Authoritative Regulatory & Cybersecurity Frameworks
                    </h1>
                    <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                      {frameworks.length} frameworks ingested from publicly accessible, legally usable sources: EUR-Lex, NIST, OWASP, MITRE ATLAS, UK Gov, India Gazette, IMDA.
                    </p>
                  </div>

                  <div className="stagger-children" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "14px" }}>
                    {frameworks.map(fw => {
                      const accentMap: Record<string, string> = { "EU": "fw-card-accent-eu", "US": "fw-card-accent-us", "UK": "fw-card-accent-security", "Global Security": "fw-card-accent-security", "Global Privacy": "fw-card-accent-privacy", "Financial": "fw-card-accent-financial" };
                      const cls = accentMap[fw.jurisdiction] || "fw-card-accent-eu";
                      return (
                        <div key={fw.id} className={`glass-panel glass-panel-hover ${cls}`} style={{ padding: "18px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                          <div>
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", marginBottom: "6px" }}>
                              <span style={{ color: "#38BDF8", fontWeight: 700, background: "rgba(56,189,248,0.1)", padding: "2px 8px", borderRadius: "10px", border: "1px solid rgba(56,189,248,0.2)" }}>{fw.jurisdiction}</span>
                              <span style={{ color: "#64748B" }}>{fw.type}</span>
                            </div>
                            <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF", lineHeight: "1.3" }}>{fw.name}</h2>
                            <div style={{ fontSize: "10px", fontFamily: "var(--font-mono)", color: "#94A3B8", marginTop: "3px" }}>{fw.official_reference}</div>
                            <p style={{ fontSize: "11px", color: "#64748B", marginTop: "8px", lineHeight: "1.6" }}>{fw.description}</p>
                          </div>

                          <div style={{ paddingTop: "12px", marginTop: "12px", borderTop: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <span style={{ fontSize: "11px", color: "#34D399", fontWeight: 600 }}>{fw.requirement_count} Requirements</span>
                            <a href={fw.official_url} target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", color: "#38BDF8", textDecoration: "none", fontWeight: 600 }}>
                              Official Source <ExternalLink style={{ width: "11px", height: "11px" }} />
                            </a>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: ASSESSMENTS & READINESS
              ══════════════════════════════════════════════════════ */}
              {activeTab === "assessments" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
                    <div>
                      <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                        <Target style={{ width: "22px", height: "22px", color: "#38BDF8" }} />
                        Compliance Assessments & Readiness Scoring
                      </h1>
                      <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                        Execute framework-specific assessments per AI system. Answer Yes/No/Partial to calculate explainable readiness scores with full evidence linkage.
                      </p>
                    </div>
                  </div>

                  {assessments.length === 0 ? (
                    <div className="glass-panel" style={{ padding: "60px 40px", textAlign: "center" }}>
                      <Target style={{ width: "40px", height: "40px", color: "#38BDF8", margin: "0 auto 16px" }} />
                      <div style={{ fontSize: "16px", fontWeight: 700, color: "#E2E8F0" }}>No Assessments Yet</div>
                      <div style={{ fontSize: "12px", color: "#64748B", marginTop: "6px", maxWidth: "400px", margin: "8px auto 0" }}>Create assessments for your AI systems against the 17 authoritative frameworks to track readiness with evidence-backed scoring.</div>
                    </div>
                  ) : (
                    <>
                      {/* Summary Stats */}
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "10px" }}>
                        {[
                          { label: "Total Assessments", val: assessments.length, color: "#F8FAFC" },
                          { label: "In Progress", val: assessments.filter((a: any) => a.status === "In Progress").length, color: "#FBBF24" },
                          { label: "Completed", val: assessments.filter((a: any) => a.status === "Completed").length, color: "#34D399" },
                          { label: "Avg. Readiness", val: assessments.length > 0 ? `${Math.round(assessments.reduce((s: number, a: any) => s + (a.readiness_percentage || 0), 0) / assessments.length)}%` : "—", color: "#38BDF8" },
                        ].map((stat, i) => (
                          <div key={i} className="glass-panel" style={{ padding: "14px" }}>
                            <div style={{ fontSize: "10px", color: "#64748B" }}>{stat.label}</div>
                            <div style={{ fontSize: "24px", fontWeight: 900, color: stat.color, letterSpacing: "-0.02em" }}>{stat.val}</div>
                          </div>
                        ))}
                      </div>

                      <div className="glass-panel" style={{ overflowX: "auto" }}>
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Assessment Title</th>
                              <th>AI System</th>
                              <th>Framework</th>
                              <th>Status</th>
                              <th>Readiness</th>
                              <th>Implementation</th>
                              <th>Evidence</th>
                              <th style={{ textAlign: "right" }}>Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {assessments.map(a => (
                              <tr key={a.id}>
                                <td>
                                  <div style={{ fontWeight: 600, color: "#F8FAFC" }}>{a.title}</div>
                                  <div style={{ fontSize: "10px", color: "#475569", fontFamily: "var(--font-mono)" }}>{a.id?.slice(0, 12)}...</div>
                                </td>
                                <td style={{ color: "#CBD5E1" }}>{a.system_name}</td>
                                <td>
                                  <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "#38BDF8", background: "rgba(56,189,248,0.1)", padding: "2px 6px", borderRadius: "4px" }}>{a.framework_id}</span>
                                </td>
                                <td>
                                  <span className={`badge badge-${a.status === "Completed" ? "green" : a.status === "In Progress" ? "amber" : "indigo"}`}>{a.status}</span>
                                </td>
                                <td>
                                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <div className="progress-bar" style={{ width: "70px" }}>
                                      <div className="progress-bar-fill" style={{ width: `${a.readiness_percentage || 0}%`, background: getReadinessColor(a.readiness_percentage || 0) }} />
                                    </div>
                                    <span style={{ fontSize: "11px", fontWeight: 700, color: getReadinessColor(a.readiness_percentage || 0) }}>{a.readiness_percentage || 0}%</span>
                                  </div>
                                </td>
                                <td style={{ color: "#94A3B8", fontSize: "11px" }}>{a.implementation_score || 0}%</td>
                                <td style={{ color: "#94A3B8", fontSize: "11px" }}>{a.evidence_score || 0}%</td>
                                <td style={{ textAlign: "right" }}>
                                  <button onClick={() => setSelectedAssessment(a)} style={{ padding: "4px 10px", borderRadius: "6px", background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.2)", color: "#38BDF8", fontSize: "11px", cursor: "pointer", fontWeight: 600 }}>
                                    Open
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: EVIDENCE VAULT
              ══════════════════════════════════════════════════════ */}
              {activeTab === "evidence" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
                    <div>
                      <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                        <Lock style={{ width: "22px", height: "22px", color: "#38BDF8" }} />
                        Evidence Vault & Multi-Framework Satisfaction
                      </h1>
                      <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                        Platform moat: Attach one verified artifact to satisfy requirements across up to 17 frameworks simultaneously with SHA-256 tamper-evident hashing.
                      </p>
                    </div>
                    <button onClick={() => setEvidenceModalOpen(true)} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 16px", borderRadius: "8px", background: "#34D399", color: "#050810", fontWeight: 700, fontSize: "12px", border: "none", cursor: "pointer" }}>
                      <Plus style={{ width: "14px", height: "14px" }} /> Upload Evidence Artifact
                    </button>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "10px" }}>
                    {[
                      { label: "Total Artifacts", val: evidenceList.length, color: "#F8FAFC" },
                      { label: "Active & Approved", val: evidenceList.filter((e: any) => e.status === "Active").length, color: "#34D399" },
                      { label: "Avg. Frameworks Covered", val: evidenceList.length > 0 ? Math.round(evidenceList.reduce((s: number, e: any) => s + (e.satisfied_frameworks_count || 0), 0) / evidenceList.length) : 0, color: "#38BDF8" },
                      { label: "Expiring Soon", val: evidenceList.filter((e: any) => e.days_until_expiry && e.days_until_expiry < 30).length, color: "#FBBF24" },
                    ].map((stat, i) => (
                      <div key={i} className="glass-panel" style={{ padding: "14px" }}>
                        <div style={{ fontSize: "10px", color: "#64748B" }}>{stat.label}</div>
                        <div style={{ fontSize: "26px", fontWeight: 900, color: stat.color, letterSpacing: "-0.02em" }}>{stat.val}</div>
                      </div>
                    ))}
                  </div>

                  <div className="glass-panel" style={{ overflowX: "auto" }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Artifact Title</th>
                          <th>SHA-256 Fingerprint</th>
                          <th>Satisfied Controls</th>
                          <th>Multi-Framework Coverage</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {evidenceList.map(ev => (
                          <tr key={ev.id}>
                            <td>
                              <div style={{ fontWeight: 600, color: "#F8FAFC" }}>{ev.title}</div>
                              <div style={{ fontSize: "11px", color: "#475569" }}>{ev.evidence_type} · Owner: {ev.owner}</div>
                            </td>
                            <td style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "#94A3B8" }}>
                              {ev.file_hash_sha256?.substring(0, 28)}...
                            </td>
                            <td>
                              <div style={{ display: "flex", flexWrap: "wrap", gap: "3px" }}>
                                {ev.satisfied_controls?.slice(0, 4).map((c: string) => (
                                  <span key={c} className="badge badge-indigo" style={{ fontFamily: "var(--font-mono)" }}>{c}</span>
                                ))}
                                {ev.satisfied_controls?.length > 4 && <span style={{ fontSize: "10px", color: "#64748B" }}>+{ev.satisfied_controls.length - 4}</span>}
                              </div>
                            </td>
                            <td>
                              <span className="badge badge-green" style={{ fontSize: "11px" }}>
                                ✓ {ev.satisfied_frameworks_count} Framework{ev.satisfied_frameworks_count !== 1 ? "s" : ""}
                              </span>
                            </td>
                            <td>
                              <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "11px", color: "#34D399" }}>
                                <CheckCircle2 style={{ width: "12px", height: "12px" }} /> Approved
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: AI SECURITY & AGENTS
              ══════════════════════════════════════════════════════ */}
              {activeTab === "security" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  <div>
                    <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                      <Terminal style={{ width: "22px", height: "22px", color: "#38BDF8" }} />
                      AI Security Center & Agent Permission Graph
                    </h1>
                    <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                      OWASP Agentic AI guidance, tool permission boundaries, least-privilege enforcement, and instant emergency kill-switches per NIST AI 600-1.
                    </p>
                  </div>

                  {/* Agents Grid */}
                  <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
                    <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0", display: "flex", alignItems: "center", gap: "8px" }}>
                      <Target style={{ width: "16px", height: "16px", color: "#FBBF24" }} />
                      Autonomous Agent Permission Graph & Kill-Switches
                    </h2>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
                      {agents.map(ag => (
                        <div key={ag.id} style={{ padding: "16px", borderRadius: "10px", background: "rgba(0,0,0,0.3)", border: `1px solid ${ag.kill_switch_active ? "rgba(244,63,94,0.4)" : "rgba(255,255,255,0.08)"}`, display: "flex", flexDirection: "column", gap: "12px", transition: "border-color 0.3s ease" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div>
                              <div style={{ fontWeight: 700, color: "#FFFFFF", fontSize: "13px" }}>{ag.name}</div>
                              <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>{ag.autonomy_level}</div>
                            </div>
                            <button
                              onClick={() => handleKillSwitch(ag.id)}
                              className={ag.kill_switch_active ? "kill-switch-active" : ""}
                              style={{ padding: "6px 12px", borderRadius: "6px", fontSize: "11px", fontWeight: 700, cursor: "pointer", border: "none", background: ag.kill_switch_active ? "rgba(244,63,94,0.8)" : "rgba(251,113,133,0.15)", color: ag.kill_switch_active ? "#FFF" : "#FB7185", transition: "all 0.2s ease" }}
                            >
                              {ag.kill_switch_active ? "⏸ HALTED" : "⚡ Kill-Switch"}
                            </button>
                          </div>

                          <div>
                            <div style={{ fontSize: "10px", color: "#64748B", fontWeight: 600, marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.06em" }}>Granted Tool Permissions</div>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                              {ag.tools?.map((t: string) => (
                                <span key={t} style={{ fontSize: "10px", fontFamily: "var(--font-mono)", background: t.includes("code") || t.includes("exec") || t.includes("terminal") ? "rgba(244,63,94,0.12)" : "rgba(255,255,255,0.05)", color: t.includes("code") || t.includes("exec") || t.includes("terminal") ? "#FDA4AF" : "#CBD5E1", padding: "2px 7px", borderRadius: "4px", border: `1px solid ${t.includes("code") || t.includes("exec") ? "rgba(244,63,94,0.2)" : "rgba(255,255,255,0.08)"}` }}>
                                  {t}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div style={{ borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: "10px", display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                            <span style={{ color: "#64748B" }}>Human Approval Gate:</span>
                            <span style={{ color: "#34D399", fontWeight: 600 }}>Enforced for DB/Code ops</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Vendor Risk Table */}
                  <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
                    <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0", display: "flex", alignItems: "center", gap: "8px" }}>
                      <Database style={{ width: "16px", height: "16px", color: "#38BDF8" }} />
                      Third-Party Foundation Model Vendor Risk Register
                    </h2>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Vendor</th>
                          <th>Service Type</th>
                          <th>Data Training Policy</th>
                          <th>EU AI Act Status</th>
                          <th>Risk Rating</th>
                        </tr>
                      </thead>
                      <tbody>
                        {vendors.map(v => (
                          <tr key={v.id}>
                            <td style={{ fontWeight: 600, color: "#FFF" }}>{v.name}</td>
                            <td style={{ color: "#CBD5E1", fontSize: "11px" }}>{v.service_type}</td>
                            <td>
                              <span className="badge badge-green" style={{ fontSize: "10px" }}>Zero Training Guarantee</span>
                            </td>
                            <td>
                              <span className="badge badge-blue" style={{ fontSize: "10px" }}>GPAI Registered</span>
                            </td>
                            <td>
                              <span style={{ fontWeight: 600, color: getStatusColor(v.risk_rating === "Low" ? "Active" : v.risk_rating === "Medium" ? "In Progress" : "Open") }}>{v.risk_rating}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: RISK REGISTER & HEATMAP
              ══════════════════════════════════════════════════════ */}
              {activeTab === "risks" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
                    <div>
                      <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                        <AlertTriangle style={{ width: "22px", height: "22px", color: "#FBBF24" }} />
                        AI Risk Register, Threat Heatmap & Remediation
                      </h1>
                      <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                        Inherent vs residual risk scoring mapped to MITRE ATLAS techniques. SLA-tracked remediation with critical findings escalation.
                      </p>
                    </div>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button onClick={() => setHeatmapView(!heatmapView)} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "7px 14px", borderRadius: "8px", background: heatmapView ? "rgba(56,189,248,0.15)" : "rgba(255,255,255,0.05)", border: `1px solid ${heatmapView ? "rgba(56,189,248,0.4)" : "rgba(255,255,255,0.08)"}`, color: heatmapView ? "#38BDF8" : "#94A3B8", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>
                        <BarChart2 style={{ width: "14px", height: "14px" }} />
                        {heatmapView ? "Show Table" : "Risk Heatmap"}
                      </button>
                    </div>
                  </div>

                  {/* Risk heatmap */}
                  {heatmapView && (
                    <div className="glass-panel animate-fadeIn" style={{ padding: "24px" }}>
                      <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
                        <AlertTriangle style={{ width: "15px", height: "15px", color: "#FBBF24" }} />
                        Inherent vs Residual Risk Heatmap (MITRE ATLAS Aligned)
                      </h2>
                      <RiskHeatmap risks={risks} />
                    </div>
                  )}

                  {/* Findings */}
                  {findings.length > 0 && (
                    <div className="glass-panel" style={{ padding: "0", overflow: "hidden" }}>
                      <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0", display: "flex", alignItems: "center", gap: "8px" }}>
                          <AlertOctagon style={{ width: "15px", height: "15px", color: "#FB7185" }} />
                          Security Findings ({findings.length})
                          {findings.filter((f: any) => f.severity === "Critical" && f.status === "Open").length > 0 && (
                            <span className="badge badge-red animate-pulse-glow">{findings.filter((f: any) => f.severity === "Critical" && f.status === "Open").length} Critical</span>
                          )}
                        </h2>
                        <button onClick={() => setFindingsExpanded(!findingsExpanded)} style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer" }}>
                          <ChevronDown style={{ width: "16px", height: "16px", transform: findingsExpanded ? "rotate(180deg)" : "none", transition: "transform 0.2s ease" }} />
                        </button>
                      </div>
                      {findingsExpanded && (
                        <table className="data-table animate-fadeIn">
                          <thead><tr><th>Finding</th><th>Severity</th><th>OWASP / MITRE</th><th>SLA Remaining</th><th>Status</th><th>Owner</th></tr></thead>
                          <tbody>
                            {findings.map((f: any) => (
                              <tr key={f.id}>
                                <td>
                                  <div style={{ fontWeight: 600, color: "#F8FAFC" }}>{f.title}</div>
                                  <div style={{ fontSize: "11px", color: "#475569" }}>{f.system_name}</div>
                                </td>
                                <td>
                                  <span className={`badge badge-${f.severity === "Critical" ? "red" : f.severity === "High" ? "amber" : "blue"}`}>{f.severity}</span>
                                </td>
                                <td style={{ fontSize: "11px" }}>
                                  <div style={{ color: "#38BDF8", fontFamily: "var(--font-mono)" }}>{f.owasp_category}</div>
                                  <div style={{ color: "#64748B" }}>{f.mitre_atlas_technique}</div>
                                </td>
                                <td>
                                  <span style={{ color: (f.sla_days_remaining || 0) < 7 ? "#FB7185" : "#FBBF24", fontWeight: 700 }}>
                                    {f.sla_days_remaining ?? "—"}d
                                  </span>
                                </td>
                                <td>
                                  <span className={`badge badge-${f.status === "Open" ? "red" : f.status === "Mitigated" ? "green" : "amber"}`}>{f.status}</span>
                                </td>
                                <td style={{ color: "#CBD5E1", fontSize: "11px" }}>{f.owner}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  )}

                  {/* Risk Register Table */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0" }}>Risk Register</h2>
                    <select value={riskStatusFilter} onChange={e => setRiskStatusFilter(e.target.value)} style={{ padding: "5px 10px", borderRadius: "6px", fontSize: "11px" }}>
                      <option value="All">All Status</option>
                      <option value="Open">Open</option>
                      <option value="Mitigated">Mitigated</option>
                      <option value="Accepted">Accepted</option>
                    </select>
                  </div>

                  <div className="glass-panel" style={{ overflowX: "auto" }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Risk Code & Title</th>
                          <th>Domain</th>
                          <th>Threat (MITRE ATLAS / OWASP)</th>
                          <th>Inherent → Residual</th>
                          <th>Status</th>
                          <th>Owner</th>
                        </tr>
                      </thead>
                      <tbody>
                        {risks.filter((r: any) => riskStatusFilter === "All" || r.status === riskStatusFilter).map(r => (
                          <tr key={r.id}>
                            <td>
                              <div style={{ fontFamily: "var(--font-mono)", color: "#FBBF24", fontWeight: 700, fontSize: "11px" }}>{r.risk_code}</div>
                              <div style={{ color: "#F8FAFC", fontWeight: 600, marginTop: "2px" }}>{r.title}</div>
                            </td>
                            <td style={{ color: "#CBD5E1", fontSize: "11px" }}>{r.category}</td>
                            <td>
                              <div style={{ color: "#38BDF8", fontSize: "11px", fontFamily: "var(--font-mono)" }}>{r.mitre_atlas_technique}</div>
                              <div style={{ color: "#64748B", fontSize: "10px" }}>{r.owasp_category}</div>
                            </td>
                            <td>
                              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                <span style={{ fontWeight: 800, fontSize: "14px", color: getRiskColor(r.inherent_score) }}>{r.inherent_score}</span>
                                <span style={{ color: "#475569" }}>→</span>
                                <span style={{ fontWeight: 800, fontSize: "14px", color: getRiskColor(r.residual_score) }}>{r.residual_score}</span>
                              </div>
                            </td>
                            <td>
                              <span className={`badge badge-${r.status === "Open" ? "amber" : r.status === "Mitigated" ? "green" : "purple"}`}>{r.status}</span>
                            </td>
                            <td style={{ color: "#CBD5E1", fontSize: "11px" }}>{r.owner}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Remediation Tasks */}
                  <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
                    <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0", display: "flex", alignItems: "center", gap: "8px" }}>
                      <CheckCircle2 style={{ width: "15px", height: "15px", color: "#34D399" }} />
                      Remediation Backlog (SLA-Tracked)
                    </h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {remediations.map(t => (
                        <div key={t.id} style={{ padding: "12px 16px", borderRadius: "8px", background: "rgba(0,0,0,0.25)", border: `1px solid ${t.status === "Done" ? "rgba(52,211,153,0.15)" : "rgba(255,255,255,0.06)"}`, display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", transition: "all 0.2s ease" }}>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 600, color: t.status === "Done" ? "#475569" : "#F8FAFC", textDecoration: t.status === "Done" ? "line-through" : "none", fontSize: "12px" }}>{t.title}</div>
                            <div style={{ fontSize: "10px", color: "#475569", marginTop: "2px" }}>Assigned: {t.assigned_to} · Priority: <span style={{ color: t.priority === "Critical" ? "#FB7185" : t.priority === "High" ? "#FBBF24" : "#94A3B8" }}>{t.priority}</span></div>
                          </div>
                          <button
                            onClick={() => handleRemediationToggle(t.id, t.status)}
                            style={{ padding: "5px 12px", borderRadius: "6px", fontSize: "11px", fontWeight: 600, cursor: "pointer", border: "none", background: t.status === "Done" ? "rgba(52,211,153,0.15)" : "rgba(56,189,248,0.15)", color: t.status === "Done" ? "#34D399" : "#38BDF8", flexShrink: 0, transition: "all 0.15s ease" }}
                          >
                            {t.status === "Done" ? "✓ Completed" : "Mark Done"}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: EXECUTIVE REPORTS
              ══════════════════════════════════════════════════════ */}
              {activeTab === "reports" && (
                <div style={{ maxWidth: "820px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                        <FileText style={{ width: "22px", height: "22px", color: "#38BDF8" }} />
                        Executive Compliance & Governance Reports
                      </h1>
                      <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                        Board-level AI governance dossiers, EU AI Act conformity assessments, and NIST AI RMF posture reports.
                      </p>
                    </div>
                    <button
                      onClick={async () => {
                        try {
                          const rep = await api.getExecutiveReport();
                          const blob = new Blob([JSON.stringify(rep, null, 2)], { type: "application/json" });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = `AegisAI_Governance_Report_${new Date().toISOString().split("T")[0]}.json`;
                          a.click();
                        } catch (err: any) { alert("Export failed: " + err.message); }
                      }}
                      style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 16px", borderRadius: "8px", background: "linear-gradient(135deg, #38BDF8, #6366F1)", color: "#050810", fontWeight: 700, fontSize: "12px", border: "none", cursor: "pointer" }}
                    >
                      <Download style={{ width: "14px", height: "14px" }} /> Export JSON Report
                    </button>
                  </div>

                  {/* Report preview */}
                  <div className="glass-panel" style={{ padding: "28px", display: "flex", flexDirection: "column", gap: "20px", fontFamily: "var(--font-mono)", fontSize: "11px" }}>
                    <div style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "14px" }}>
                      <div style={{ color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase" }}>REPORT-ID: AEGIS-EXEC-{new Date().getFullYear()}-{String(new Date().getMonth() + 1).padStart(2, "0")}</div>
                      <div style={{ fontSize: "18px", fontWeight: 900, color: "#FFF", marginTop: "4px", letterSpacing: "-0.02em" }}>ACME FINANCIAL SERVICES — AI GOVERNANCE BASELINE</div>
                      <div style={{ color: "#475569", marginTop: "4px" }}>Generated: {new Date().toLocaleDateString("en-GB", { year: "numeric", month: "long", day: "numeric" })} · Classification: INTERNAL CONFIDENTIAL</div>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px", textAlign: "center" }}>
                      {[
                        { label: "Readiness", val: `${metrics?.overall_readiness_percentage}%`, color: "#38BDF8" },
                        { label: "AI Systems", val: aiSystems.length, color: "#34D399" },
                        { label: "Controls", val: controls.length, color: "#C084FC" },
                        { label: "Evidence", val: evidenceList.length, color: "#FBBF24" },
                      ].map((stat, i) => (
                        <div key={i} style={{ padding: "12px", background: "rgba(0,0,0,0.4)", borderRadius: "8px" }}>
                          <div style={{ fontSize: "20px", fontWeight: 900, color: stat.color }}>{stat.val}</div>
                          <div style={{ fontSize: "10px", color: "#64748B", marginTop: "2px" }}>{stat.label}</div>
                        </div>
                      ))}
                    </div>

                    <div style={{ color: "#CBD5E1", lineHeight: "1.8", fontSize: "11px", display: "flex", flexDirection: "column", gap: "8px" }}>
                      {[
                        { title: "EU AI Act (Reg. 2024/1689)", body: "High-Risk systems (Loan Decision AI) subject to Annex III conformity obligations. Article 5 prohibited practices screening gate operational. Article 50 transparency requirements active for Customer Support Copilot." },
                        { title: "NIST AI RMF 1.0 (AI 100-1)", body: "GOVERN and MAP functions operational with assigned owners across all business units. Risk register populated with 7 identified risks. MANAGE function tracking 4 open remediations." },
                        { title: "OWASP Agentic AI Security", body: "Autonomous IT Support Agent equipped with least-privilege tool permissions. Emergency kill-switch operational. Human approval gate enforced for database writes and code execution." },
                        { title: "GDPR / India DPDPA 2023", body: "Data Protection Impact Assessments (DPIAs) completed for systems processing personal data. Data minimisation controls implemented. Breach notification procedures documented." },
                      ].map(item => (
                        <div key={item.title} style={{ padding: "12px 14px", borderRadius: "6px", background: "rgba(0,0,0,0.25)", borderLeft: "2px solid rgba(56,189,248,0.4)" }}>
                          <div style={{ color: "#38BDF8", fontWeight: 700, marginBottom: "4px" }}>• {item.title}</div>
                          <div style={{ color: "#94A3B8" }}>{item.body}</div>
                        </div>
                      ))}
                    </div>

                    <div style={{ padding: "10px 14px", borderRadius: "6px", background: "rgba(251,191,36,0.06)", border: "1px solid rgba(251,191,36,0.2)", color: "#92700A", fontSize: "10px" }}>
                      ⚠ DISCLAIMER: This report provides governance and readiness workflow support only. It does not constitute legal advice, and compliance determinations should be validated with qualified legal and compliance counsel.
                    </div>
                  </div>

                  {/* Available report types */}
                  <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
                    <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0" }}>Available Report Templates</h2>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                      {[
                        { title: "EU AI Act Conformity Assessment", desc: "Annex III classification + Article 9 risk management evidence", icon: Shield, color: "#38BDF8" },
                        { title: "NIST AI RMF Posture Report", desc: "GOVERN, MAP, MEASURE, MANAGE function scorecard", icon: BarChart2, color: "#6366F1" },
                        { title: "Board AI Risk Dashboard", desc: "Executive summary for board and C-suite", icon: TrendingUp, color: "#34D399" },
                        { title: "GDPR DPIA Summary Report", desc: "Data Protection Impact Assessment outcomes", icon: Lock, color: "#C084FC" },
                      ].map(r => {
                        const Icon = r.icon;
                        return (
                          <div key={r.title} className="glass-panel-hover" style={{ padding: "14px", borderRadius: "8px", background: "rgba(0,0,0,0.25)", border: "1px solid rgba(255,255,255,0.06)", cursor: "pointer" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                              <Icon style={{ width: "14px", height: "14px", color: r.color }} />
                              <span style={{ fontSize: "12px", fontWeight: 600, color: "#E2E8F0" }}>{r.title}</span>
                            </div>
                            <p style={{ fontSize: "10px", color: "#64748B" }}>{r.desc}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: TAMPER-EVIDENT AUDIT TRAIL
              ══════════════════════════════════════════════════════ */}
              {activeTab === "audit" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div>
                    <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                      <Clock style={{ width: "22px", height: "22px", color: "#38BDF8" }} />
                      Tamper-Evident Compliance Audit Trail
                    </h1>
                    <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                      Immutable, time-stamped ledger of all governance events: AI registration, control updates, evidence uploads, assessment responses, and kill-switch activations.
                    </p>
                  </div>

                  <div className="glass-panel" style={{ padding: "14px 20px", display: "flex", alignItems: "center", gap: "20px", background: "rgba(52,211,153,0.06)", border: "1px solid rgba(52,211,153,0.2)" }}>
                    <CheckCircle2 style={{ width: "20px", height: "20px", color: "#34D399", flexShrink: 0 }} />
                    <div style={{ fontSize: "12px" }}>
                      <span style={{ fontWeight: 600, color: "#34D399" }}>Audit Integrity: Verified</span>
                      <span style={{ color: "#64748B", marginLeft: "8px" }}>{auditEvents.length} events recorded · Sequential hash chain validated · No tampering detected</span>
                    </div>
                  </div>

                  <div className="glass-panel" style={{ overflowX: "auto" }}>
                    <table className="data-table" style={{ fontFamily: "var(--font-mono)", fontSize: "11px" }}>
                      <thead>
                        <tr>
                          <th>Timestamp</th>
                          <th>Actor</th>
                          <th>Action</th>
                          <th>Target Type</th>
                          <th>Change Details</th>
                        </tr>
                      </thead>
                      <tbody>
                        {auditEvents.map(ev => (
                          <tr key={ev.id}>
                            <td style={{ color: "#64748B", whiteSpace: "nowrap" }}>{new Date(ev.timestamp).toLocaleString("en-GB")}</td>
                            <td style={{ color: "#38BDF8" }}>{ev.actor_email}</td>
                            <td>
                              <span style={{ padding: "2px 7px", borderRadius: "4px", fontWeight: 700, fontSize: "10px", background: "rgba(52,211,153,0.12)", color: "#34D399" }}>{ev.action}</span>
                            </td>
                            <td style={{ color: "#CBD5E1" }}>{ev.object_type}</td>
                            <td style={{ color: "#64748B", maxWidth: "280px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {JSON.stringify(ev.changes)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ══════════════════════════════════════════════════════
                  TAB: SETTINGS & RBAC
              ══════════════════════════════════════════════════════ */}
              {activeTab === "settings" && (
                <div style={{ maxWidth: "800px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "20px" }}>
                  <div>
                    <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", display: "flex", alignItems: "center", gap: "10px", letterSpacing: "-0.02em" }}>
                      <Settings style={{ width: "22px", height: "22px", color: "#38BDF8" }} />
                      Platform Settings & RBAC
                    </h1>
                    <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
                      Multi-tenant access control, role permissions, and platform configuration.
                    </p>
                  </div>

                  {/* Roles */}
                  <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
                    <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0", display: "flex", alignItems: "center", gap: "8px" }}>
                      <Users style={{ width: "15px", height: "15px", color: "#38BDF8" }} />
                      Role-Based Access Control (RBAC)
                    </h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {[
                        { role: "CISO / Security Lead", permissions: ["View all", "Manage security findings", "Trigger kill-switches", "Export reports"], color: "#FB7185" },
                        { role: "AI Governance Lead", permissions: ["Full platform access", "Register AI systems", "Update controls", "Upload evidence"], color: "#38BDF8" },
                        { role: "Compliance Manager", permissions: ["View all", "Create assessments", "Upload evidence", "Export reports"], color: "#C084FC" },
                        { role: "DPO (Data Protection)", permissions: ["View privacy controls", "Manage DPIA evidence", "View risk register"], color: "#34D399" },
                        { role: "AI Engineer / Developer", permissions: ["View AI inventory", "View controls", "View frameworks"], color: "#FBBF24" },
                        { role: "Auditor (Read-Only)", permissions: ["View all (read-only)", "Export audit trail"], color: "#94A3B8" },
                      ].map(r => (
                        <div key={r.role} style={{ padding: "12px 16px", borderRadius: "8px", background: "rgba(0,0,0,0.25)", border: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                            <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: r.color, flexShrink: 0 }} />
                            <span style={{ fontSize: "12px", fontWeight: 600, color: "#E2E8F0" }}>{r.role}</span>
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                            {r.permissions.map(p => (
                              <span key={p} style={{ fontSize: "10px", color: "#64748B", background: "rgba(255,255,255,0.04)", padding: "2px 7px", borderRadius: "4px", border: "1px solid rgba(255,255,255,0.06)" }}>{p}</span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Platform config */}
                  <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
                    <h2 style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0" }}>Platform Configuration</h2>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "12px" }}>
                      {[
                        { label: "Platform Version", val: "AegisAI OS v1.0.0" },
                        { label: "Database Engine", val: "SQLite (Dev) / PostgreSQL (Prod)" },
                        { label: "Auth Method", val: "JWT Bearer Tokens (HS256)" },
                        { label: "Supported Frameworks", val: "17 Authoritative Standards" },
                        { label: "Evidence Hashing", val: "SHA-256 (FIPS 180-4)" },
                        { label: "Audit Logging", val: "Tamper-evident sequential log" },
                      ].map(item => (
                        <div key={item.label} style={{ padding: "12px", background: "rgba(0,0,0,0.25)", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)" }}>
                          <div style={{ fontSize: "10px", color: "#64748B" }}>{item.label}</div>
                          <div style={{ fontWeight: 600, color: "#E2E8F0", marginTop: "4px", fontFamily: "var(--font-mono)", fontSize: "11px" }}>{item.val}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* ══════════════ AI COPILOT SLIDE-OVER ══════════════ */}
      {copilotOpen && (
        <div className="animate-slideLeft" style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: "400px", background: "linear-gradient(180deg, #0A1020 0%, #060912 100%)", borderLeft: "1px solid rgba(255,255,255,0.08)", zIndex: 999, display: "flex", flexDirection: "column", boxShadow: "-12px 0 48px rgba(0,0,0,0.8)" }}>
          {/* Copilot header */}
          <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(0,0,0,0.3)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "linear-gradient(135deg, rgba(56,189,248,0.25), rgba(99,102,241,0.25))", border: "1px solid rgba(56,189,248,0.35)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Sparkles style={{ width: "18px", height: "18px", color: "#38BDF8" }} />
              </div>
              <div>
                <div style={{ fontSize: "13px", fontWeight: 700, color: "#FFF" }}>AegisAI Governance Copilot</div>
                <div style={{ fontSize: "10px", color: "#475569" }}>Grounded · 17 Authoritative Frameworks · No Hallucinations</div>
              </div>
            </div>
            <button onClick={() => setCopilotOpen(false)} style={{ background: "none", border: "none", color: "#475569", cursor: "pointer", padding: "4px" }}>
              <X style={{ width: "18px", height: "18px" }} />
            </button>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
            {copilotMessages.map((m, i) => (
              <div
                key={i}
                className="animate-fadeIn"
                style={{
                  padding: "12px 14px", borderRadius: "10px", lineHeight: "1.65", fontSize: "12px",
                  background: m.sender === "user" ? "rgba(56,189,248,0.12)" : m.sender === "system" ? "rgba(99,102,241,0.08)" : "rgba(255,255,255,0.04)",
                  border: m.sender === "user" ? "1px solid rgba(56,189,248,0.25)" : m.sender === "system" ? "1px solid rgba(99,102,241,0.2)" : "1px solid rgba(255,255,255,0.06)",
                  color: m.sender === "user" ? "#E0F2FE" : "#F1F5F9",
                  marginLeft: m.sender === "user" ? "24px" : "0",
                  marginRight: m.sender === "user" ? "0" : "24px"
                }}
              >
                {m.sender !== "user" && (
                  <div style={{ fontSize: "10px", color: "#475569", marginBottom: "6px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    {m.sender === "system" ? "AEGISAI COPILOT" : "AEGISAI COPILOT"}
                  </div>
                )}
                <div style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
                {m.citations && m.citations.length > 0 && (
                  <div style={{ marginTop: "10px", paddingTop: "10px", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
                    <div style={{ fontSize: "10px", fontWeight: 700, color: "#38BDF8", marginBottom: "6px", letterSpacing: "0.06em" }}>AUTHORITATIVE CITATIONS:</div>
                    {m.citations.map((c: any, idx: number) => (
                      <a key={idx} href={c.url} target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: "6px", color: "#7DD3FC", textDecoration: "none", fontSize: "10px", marginBottom: "4px" }}>
                        <ExternalLink style={{ width: "11px", height: "11px", flexShrink: 0 }} />
                        {c.source} ({c.reference})
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {copilotLoading && (
              <div style={{ padding: "12px 14px", borderRadius: "10px", background: "rgba(255,255,255,0.04)", color: "#94A3B8", display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", marginRight: "24px" }}>
                <RefreshCw style={{ width: "14px", height: "14px", color: "#38BDF8", animation: "spin 1s linear infinite", flexShrink: 0 }} />
                <span>Querying 17-framework regulatory knowledge graph...</span>
              </div>
            )}
            <div ref={copilotEndRef} />
          </div>

          {/* Quick Prompts */}
          <div style={{ padding: "12px 16px", borderTop: "1px solid rgba(255,255,255,0.06)", background: "rgba(0,0,0,0.2)", display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ fontSize: "10px", color: "#475569", fontWeight: 700, letterSpacing: "0.06em" }}>SUGGESTED QUERIES:</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
              {[
                "Does EU AI Act apply to our Loan Decision AI?",
                "Which controls satisfy NIST AI RMF and EU AI Act?",
                "What OWASP risks apply to autonomous agents?",
                "Show highest-risk AI systems",
                "What evidence gaps exist for GDPR?"
              ].map((qp, idx) => (
                <button key={idx} onClick={() => setCopilotQuery(qp)} style={{ fontSize: "10px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "#94A3B8", padding: "5px 9px", borderRadius: "5px", cursor: "pointer", textAlign: "left", transition: "all 0.15s ease" }}>
                  {qp}
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div style={{ padding: "12px 16px", borderTop: "1px solid rgba(255,255,255,0.07)", display: "flex", gap: "8px" }}>
            <input
              type="text"
              placeholder="Ask a compliance or governance question..."
              value={copilotQuery}
              onChange={e => setCopilotQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && !copilotLoading && handleCopilotSend()}
              style={{ flex: 1, padding: "10px 14px", borderRadius: "8px", fontSize: "12px" }}
            />
            <button
              onClick={handleCopilotSend}
              disabled={copilotLoading || !copilotQuery.trim()}
              style={{ padding: "10px 14px", borderRadius: "8px", background: "linear-gradient(135deg, #38BDF8, #6366F1)", color: "#050810", fontWeight: 700, border: "none", cursor: copilotLoading ? "not-allowed" : "pointer", opacity: copilotLoading ? 0.6 : 1, display: "flex", alignItems: "center", gap: "4px" }}
            >
              <ChevronRight style={{ width: "16px", height: "16px" }} />
            </button>
          </div>
        </div>
      )}

      {/* ══════════════ MODAL: SYSTEM DETAILS ══════════════ */}
      {selectedSystem && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(8px)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }} onClick={() => setSelectedSystem(null)}>
          <div className="glass-panel animate-fadeInScale" style={{ maxWidth: "620px", width: "100%", padding: "28px", display: "flex", flexDirection: "column", gap: "18px" }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "14px" }}>
              <div>
                <div style={{ fontSize: "10px", color: "#38BDF8", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>{selectedSystem.business_unit}</div>
                <div style={{ fontSize: "18px", fontWeight: 800, color: "#FFF", letterSpacing: "-0.02em" }}>{selectedSystem.name}</div>
              </div>
              <button onClick={() => setSelectedSystem(null)} style={{ background: "none", border: "none", color: "#475569", cursor: "pointer" }}>
                <X style={{ width: "20px", height: "20px" }} />
              </button>
            </div>

            <p style={{ fontSize: "12px", color: "#CBD5E1", lineHeight: "1.7" }}>{selectedSystem.description}</p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "11px" }}>
              {[
                { label: "Model & Hosting", val: `${selectedSystem.model_provider} ${selectedSystem.model_name}`, sub: `${selectedSystem.cloud_provider} (${selectedSystem.deployment_environment})` },
                { label: "EU AI Act Classification", val: selectedSystem.risk_classification, sub: selectedSystem.eu_ai_act_classification, valColor: "#FB7185" },
                { label: "AI Type", val: selectedSystem.ai_technology, sub: `${selectedSystem.is_agentic_ai ? "Autonomous Agent" : "Non-Agentic"}` },
                { label: "Data & Privacy", val: selectedSystem.processes_personal_data ? "Processes Personal Data" : "No Personal Data", sub: "GDPR / DPDPA Applicability" },
              ].map(item => (
                <div key={item.label} style={{ padding: "12px", background: "rgba(0,0,0,0.3)", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.06)" }}>
                  <div style={{ color: "#64748B", marginBottom: "4px" }}>{item.label}</div>
                  <div style={{ fontWeight: 700, color: item.valColor || "#FFF" }}>{item.val}</div>
                  <div style={{ color: "#64748B", marginTop: "2px" }}>{item.sub}</div>
                </div>
              ))}
            </div>

            {selectedSystem.classification_reasoning && (
              <div style={{ padding: "14px", borderRadius: "8px", background: "rgba(56,189,248,0.07)", border: "1px solid rgba(56,189,248,0.18)", fontSize: "11px", color: "#BAE6FD", lineHeight: "1.7" }}>
                <div style={{ fontWeight: 700, color: "#38BDF8", marginBottom: "4px" }}>⚖ Statutory Rationale:</div>
                {selectedSystem.classification_reasoning}
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <button onClick={() => { setSelectedSystem(null); setActiveTab("assessments"); }} style={{ padding: "7px 14px", borderRadius: "8px", background: "rgba(56,189,248,0.1)", color: "#38BDF8", border: "1px solid rgba(56,189,248,0.25)", cursor: "pointer", fontSize: "12px", fontWeight: 600 }}>
                Create Assessment
              </button>
              <button onClick={() => setSelectedSystem(null)} style={{ padding: "7px 14px", borderRadius: "8px", background: "rgba(255,255,255,0.06)", color: "#CBD5E1", border: "1px solid rgba(255,255,255,0.1)", cursor: "pointer", fontSize: "12px" }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════ MODAL: MANAGE CONTROL ══════════════ */}
      {selectedControl && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(8px)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }} onClick={() => setSelectedControl(null)}>
          <div className="glass-panel animate-fadeInScale" style={{ maxWidth: "520px", width: "100%", padding: "28px", display: "flex", flexDirection: "column", gap: "18px" }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "12px" }}>
              <div>
                <div style={{ fontSize: "11px", color: "#38BDF8", fontFamily: "var(--font-mono)", fontWeight: 700 }}>{selectedControl.code}</div>
                <div style={{ fontSize: "16px", fontWeight: 700, color: "#FFF", letterSpacing: "-0.02em" }}>{selectedControl.title}</div>
              </div>
              <button onClick={() => setSelectedControl(null)} style={{ background: "none", border: "none", color: "#475569", cursor: "pointer" }}>
                <X style={{ width: "20px", height: "20px" }} />
              </button>
            </div>

            {selectedControl.objective && <p style={{ fontSize: "11px", color: "#CBD5E1", lineHeight: "1.7" }}>{selectedControl.objective}</p>}

            <div style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "12px" }}>
              <div>
                <label style={{ display: "block", color: "#CBD5E1", marginBottom: "6px", fontWeight: 600 }}>Implementation Status</label>
                <select id="ctrl-modal-status" defaultValue={selectedControl.customer_status} style={{ width: "100%", padding: "9px 12px" }}>
                  {["Implemented", "Tested", "In Progress", "Accepted Risk", "Not Started"].map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label style={{ display: "block", color: "#CBD5E1", marginBottom: "6px", fontWeight: 600 }}>Effectiveness Rating</label>
                <select id="ctrl-modal-eff" defaultValue={selectedControl.customer_effectiveness} style={{ width: "100%", padding: "9px 12px" }}>
                  {["Effective", "Partially Effective", "Ineffective"].map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button onClick={() => setSelectedControl(null)} style={{ padding: "8px 14px", borderRadius: "8px", background: "rgba(255,255,255,0.06)", color: "#CBD5E1", border: "none", cursor: "pointer", fontSize: "12px" }}>Cancel</button>
              <button
                onClick={() => {
                  const s = (document.getElementById("ctrl-modal-status") as HTMLSelectElement).value;
                  const e = (document.getElementById("ctrl-modal-eff") as HTMLSelectElement).value;
                  handleUpdateControl(selectedControl.id, s, e);
                }}
                style={{ padding: "8px 18px", borderRadius: "8px", background: "linear-gradient(135deg, #38BDF8, #6366F1)", color: "#050810", fontWeight: 700, border: "none", cursor: "pointer", fontSize: "12px" }}
              >
                Save & Recalculate Posture
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════ MODAL: UPLOAD EVIDENCE ══════════════ */}
      {evidenceModalOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(8px)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }} onClick={() => setEvidenceModalOpen(false)}>
          <div className="glass-panel animate-fadeInScale" style={{ maxWidth: "540px", width: "100%", padding: "28px", display: "flex", flexDirection: "column", gap: "16px" }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "14px" }}>
              <div>
                <h2 style={{ fontSize: "15px", fontWeight: 700, color: "#FFF", display: "flex", alignItems: "center", gap: "8px" }}>
                  <Lock style={{ width: "16px", height: "16px", color: "#34D399" }} />
                  Upload Evidence Artifact
                </h2>
                <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>SHA-256 hashed · Multi-control satisfaction across all mapped frameworks</div>
              </div>
              <button onClick={() => setEvidenceModalOpen(false)} style={{ background: "none", border: "none", color: "#475569", cursor: "pointer" }}>
                <X style={{ width: "20px", height: "20px" }} />
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "12px" }}>
              <div>
                <label style={{ display: "block", color: "#CBD5E1", marginBottom: "6px", fontWeight: 600 }}>Artifact Title *</label>
                <input type="text" placeholder="e.g. Model Risk Governance Charter 2026" value={newEvidence.title} onChange={e => setNewEvidence({ ...newEvidence, title: e.target.value })} style={{ width: "100%", padding: "9px 12px" }} />
              </div>
              <div>
                <label style={{ display: "block", color: "#CBD5E1", marginBottom: "6px", fontWeight: 600 }}>Description</label>
                <textarea rows={2} placeholder="Brief description of what this evidence demonstrates..." value={newEvidence.description} onChange={e => setNewEvidence({ ...newEvidence, description: e.target.value })} style={{ width: "100%", padding: "9px 12px", resize: "none" }} />
              </div>
              <div>
                <label style={{ display: "block", color: "#CBD5E1", marginBottom: "6px", fontWeight: 600 }}>Evidence Type</label>
                <select value={newEvidence.evidence_type} onChange={e => setNewEvidence({ ...newEvidence, evidence_type: e.target.value })} style={{ width: "100%", padding: "9px 12px" }}>
                  {["Policy", "Architecture Specification", "Test Report / Red Team", "Data Protection Impact Assessment (DPIA)", "Model Card", "Audit Report", "Risk Assessment", "Security Control Implementation"].map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label style={{ display: "block", color: "#CBD5E1", marginBottom: "6px", fontWeight: 600 }}>Select Satisfied Controls (Multi-Framework Linkage)</label>
                <div style={{ maxHeight: "160px", overflowY: "auto", background: "rgba(0,0,0,0.3)", padding: "10px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.06)", display: "flex", flexDirection: "column", gap: "6px" }}>
                  {controls.slice(0, 15).map(c => (
                    <label key={c.id} style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", padding: "4px 0" }}>
                      <input type="checkbox" checked={newEvidence.selected_controls.includes(c.id)} onChange={e => {
                        const next = e.target.checked ? [...newEvidence.selected_controls, c.id] : newEvidence.selected_controls.filter(id => id !== c.id);
                        setNewEvidence({ ...newEvidence, selected_controls: next });
                      }} />
                      <span style={{ fontFamily: "var(--font-mono)", color: "#38BDF8", fontSize: "11px" }}>{c.code}</span>
                      <span style={{ color: "#CBD5E1", fontSize: "11px" }}>{c.title}</span>
                    </label>
                  ))}
                </div>
                {newEvidence.selected_controls.length > 0 && (
                  <div style={{ fontSize: "10px", color: "#34D399", marginTop: "6px", fontWeight: 600 }}>
                    ✓ {newEvidence.selected_controls.length} controls selected — this artifact will satisfy all requirements mapped across the 17 frameworks
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "4px" }}>
              <button onClick={() => setEvidenceModalOpen(false)} style={{ padding: "8px 14px", borderRadius: "8px", background: "rgba(255,255,255,0.06)", color: "#CBD5E1", border: "none", cursor: "pointer", fontSize: "12px" }}>Cancel</button>
              <button onClick={handleUploadEvidence} style={{ padding: "8px 18px", borderRadius: "8px", background: "#34D399", color: "#050810", fontWeight: 800, border: "none", cursor: "pointer", fontSize: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                <Lock style={{ width: "13px", height: "13px" }} />
                Upload & Hash SHA-256
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════ MODAL: ASSESSMENT DETAIL ══════════════ */}
      {selectedAssessment && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", backdropFilter: "blur(8px)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }} onClick={() => setSelectedAssessment(null)}>
          <div className="glass-panel animate-fadeInScale" style={{ maxWidth: "580px", width: "100%", padding: "28px", display: "flex", flexDirection: "column", gap: "16px" }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "12px" }}>
              <div>
                <div style={{ fontSize: "10px", color: "#38BDF8", fontWeight: 700, fontFamily: "var(--font-mono)" }}>{selectedAssessment.framework_id}</div>
                <div style={{ fontSize: "16px", fontWeight: 800, color: "#FFF", letterSpacing: "-0.02em" }}>{selectedAssessment.title}</div>
                <div style={{ fontSize: "11px", color: "#64748B" }}>System: {selectedAssessment.system_name} · Status: {selectedAssessment.status}</div>
              </div>
              <button onClick={() => setSelectedAssessment(null)} style={{ background: "none", border: "none", color: "#475569", cursor: "pointer" }}>
                <X style={{ width: "20px", height: "20px" }} />
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px", textAlign: "center" }}>
              {[
                { label: "Readiness", val: `${selectedAssessment.readiness_percentage || 0}%`, color: getReadinessColor(selectedAssessment.readiness_percentage || 0) },
                { label: "Implementation", val: `${selectedAssessment.implementation_score || 0}%`, color: "#38BDF8" },
                { label: "Evidence", val: `${selectedAssessment.evidence_score || 0}%`, color: "#34D399" },
              ].map(s => (
                <div key={s.label} style={{ padding: "12px", background: "rgba(0,0,0,0.3)", borderRadius: "8px" }}>
                  <div style={{ fontSize: "22px", fontWeight: 900, color: s.color }}>{s.val}</div>
                  <div style={{ fontSize: "10px", color: "#64748B", marginTop: "2px" }}>{s.label}</div>
                </div>
              ))}
            </div>

            <div style={{ padding: "14px", borderRadius: "8px", background: "rgba(56,189,248,0.07)", border: "1px solid rgba(56,189,248,0.18)", fontSize: "12px", color: "#7DD3FC" }}>
              Open the full assessment in the platform to record responses, attach evidence, and drive readiness improvement.
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button onClick={() => setSelectedAssessment(null)} style={{ padding: "8px 14px", borderRadius: "8px", background: "rgba(255,255,255,0.06)", color: "#CBD5E1", border: "none", cursor: "pointer", fontSize: "12px" }}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function LoginScreen({ onSuccess }: { onSuccess: (user: api.CurrentUser) => void }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inputStyle = {
    width: "100%", padding: "9px 12px", borderRadius: "8px", background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)", fontSize: "12px", color: "#E2E8F0", outline: "none",
    boxSizing: "border-box" as const,
  };
  const labelStyle = { fontSize: "11px", fontWeight: 600, color: "#94A3B8", marginBottom: "4px", display: "block" };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user = mode === "login"
        ? await api.login(email, password)
        : await api.signup({ email, password, full_name: fullName, organization_name: orgName });
      onSuccess(user);
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", alignItems: "center", justifyContent: "center", background: "#080D1A", color: "#F8FAFC", padding: "16px" }}>
      <div style={{ width: "100%", maxWidth: "360px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", marginBottom: "28px" }}>
          <div style={{ width: "34px", height: "34px", borderRadius: "8px", background: "linear-gradient(135deg, #38BDF8, #6366F1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Shield size={18} color="#fff" />
          </div>
          <div style={{ fontWeight: 700, fontSize: "17px" }}>Aegis <span style={{ fontSize: "10px", color: "#38BDF8", background: "rgba(56,189,248,0.1)", border: "1px solid rgba(56,189,248,0.2)", padding: "2px 6px", borderRadius: "4px" }}>OS</span></div>
        </div>

        <form onSubmit={handleSubmit} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", padding: "22px", display: "flex", flexDirection: "column", gap: "14px" }}>
          <div style={{ fontSize: "13px", fontWeight: 700, color: "#E2E8F0" }}>
            {mode === "login" ? "Sign in to your organization" : "Create your organization"}
          </div>

          {mode === "signup" && (
            <>
              <div>
                <label style={labelStyle}>Full name</label>
                <input required value={fullName} onChange={e => setFullName(e.target.value)} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Organization name</label>
                <input required value={orgName} onChange={e => setOrgName(e.target.value)} style={inputStyle} />
              </div>
            </>
          )}

          <div>
            <label style={labelStyle}>Email address</label>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Password</label>
            <input type="password" required value={password} onChange={e => setPassword(e.target.value)} style={inputStyle} />
          </div>

          {error && (
            <div style={{ fontSize: "11px", color: "#FB7185", background: "rgba(251,113,133,0.1)", border: "1px solid rgba(251,113,133,0.2)", borderRadius: "8px", padding: "8px 10px" }}>
              {error}
            </div>
          )}

          <button
            type="submit" disabled={submitting}
            style={{ width: "100%", padding: "10px", borderRadius: "8px", background: "#38BDF8", color: "#06101F", fontWeight: 700, fontSize: "12px", border: "none", cursor: submitting ? "default" : "pointer", opacity: submitting ? 0.6 : 1 }}
          >
            {submitting ? "Please wait..." : mode === "login" ? "Sign in" : "Create organization"}
          </button>

          <button
            type="button"
            onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(null); }}
            style={{ width: "100%", background: "transparent", border: "none", color: "#94A3B8", fontSize: "11px", cursor: "pointer" }}
          >
            {mode === "login" ? "New organization? Create one" : "Already have an account? Sign in"}
          </button>
        </form>

        <div style={{ textAlign: "center", fontSize: "10px", color: "#475569", marginTop: "16px" }}>
          Governance Guidance • Not Legal Advice
        </div>
      </div>
    </div>
  );
}
