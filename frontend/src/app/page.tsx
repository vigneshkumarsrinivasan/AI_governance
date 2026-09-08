"use client";

import React, { useState, useEffect } from "react";
import {
  Shield, Brain, CheckCircle2, AlertTriangle, AlertCircle, FileText,
  Layers, Lock, Terminal, Activity, FileCheck, Sliders, RefreshCw,
  Search, ExternalLink, ChevronRight, Zap, Play, X, Download, MessageSquare,
  Building, User, Cpu, AlertOctagon, HelpCircle, Check, Clock, Plus
} from "lucide-react";
import * as api from "@/lib/api";
import SmeExperience from "@/components/sme/SmeExperience";
import CompanySwitcher from "@/components/CompanySwitcher";

export default function AegisPlatform() {
  const [authChecked, setAuthChecked] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<api.CurrentUser | null>(null);

  const [activeTab, setActiveTab] = useState<string>("dashboard");
  // Set by drill-through from a dashboard stat card so the AI Systems Inventory
  // opens pre-filtered to the exact records the number represented.
  const [inventoryFilter, setInventoryFilter] = useState<"all" | "high-risk" | "genai" | "agentic">("all");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [metrics, setMetrics] = useState<any>(null);
  const [aiSystems, setAiSystems] = useState<any[]>([]);
  const [frameworks, setFrameworks] = useState<any[]>([]);
  // Real source-traceable regulatory content keyed by framework_key
  // (EU AI Act 419 requirements, GDPR 238, NIST 800-53 1014, …).
  const [regFrameworks, setRegFrameworks] = useState<Record<string, any>>({});
  const [portfolioWorkflow, setPortfolioWorkflow] = useState<any[]>([]);
  const [assessmentsList, setAssessmentsList] = useState<any[]>([]);
  const [openAssessment, setOpenAssessment] = useState<any>(null);
  const [assessmentBusy, setAssessmentBusy] = useState(false);
  const [newAssessmentSystem, setNewAssessmentSystem] = useState("");
  const [newAssessmentFramework, setNewAssessmentFramework] = useState("eu_ai_act");

  const loadAssessments = async () => {
    try { setAssessmentsList(await api.getAssessments()); } catch { /* ignore */ }
  };
  const openAssessmentDetail = async (id: string) => {
    try { setOpenAssessment(await api.getAssessmentDetail(id)); }
    catch (e: any) { alert(e?.message || "Could not open assessment"); }
  };
  const createAssessmentFlow = async () => {
    if (!newAssessmentSystem) { alert("Choose an AI system first."); return; }
    setAssessmentBusy(true);
    try {
      const fwName = frameworks.find((f: any) => f.id === newAssessmentFramework)?.name || newAssessmentFramework;
      const res: any = await api.createAssessment({
        system_id: newAssessmentSystem, framework_id: newAssessmentFramework, title: `${fwName} assessment`,
      });
      await loadAssessments();
      api.getPortfolioWorkflow().then(setPortfolioWorkflow).catch(() => {});
      if (res?.id) await openAssessmentDetail(res.id);
    } catch (e: any) {
      alert("Could not create assessment: " + (e?.message || e));
    } finally { setAssessmentBusy(false); }
  };
  const assessmentApprovalAction = async (id: string, decision: "submit" | "approve" | "reject") => {
    setAssessmentBusy(true);
    try {
      await api.assessmentApproval(id, decision);
      await openAssessmentDetail(id);
      await loadAssessments();
      await loadPlatformData();
    } catch (e: any) {
      alert(e?.message || "Action failed");
    } finally { setAssessmentBusy(false); }
  };
  const [frameworkReqFilter, setFrameworkReqFilter] = useState("");
  // A couple of legacy catalog ids differ from the regulatory subsystem's keys.
  const REG_KEY_ALIAS: Record<string, string> = { gdpr_ai: "gdpr", india_dpdpa: "india_dpdp" };
  const regKeyFor = (id: string) => REG_KEY_ALIAS[id] || id;
  const [controls, setControls] = useState<any[]>([]);
  const [crosswalk, setCrosswalk] = useState<any[]>([]);
  const [evidenceList, setEvidenceList] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [vendors, setVendors] = useState<any[]>([]);
  const [risks, setRisks] = useState<any[]>([]);
  const [findings, setFindings] = useState<any[]>([]);
  const [remediations, setRemediations] = useState<any[]>([]);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);

  // Registry data (Phase 1: Model / Agent / Vendor Registries)
  const [registryModels, setRegistryModels] = useState<any[]>([]);
  const [registryAgents, setRegistryAgents] = useState<any[]>([]);
  const [registryVendors, setRegistryVendors] = useState<any[]>([]);
  const [permissionGraph, setPermissionGraph] = useState<any>(null);
  const [modelDependents, setModelDependents] = useState<any>(null);
  const [vendorImpact, setVendorImpact] = useState<any>(null);
  const [newModelForm, setNewModelForm] = useState({ name: "", provider: "OpenAI", version: "1.0", model_type: "LLM", system_id: "" });
  const [newAgentForm, setNewAgentForm] = useState({
    name: "", system_id: "", purpose: "", has_code_execution: false, has_database_access: false,
    has_payment_access: false, has_git_access: false, has_git_write_access: false, accesses_pii: false,
    autonomy_level: "Semi-Autonomous", human_approval_required: true
  });
  const [newVendorForm, setNewVendorForm] = useState({ name: "", service_type: "Foundation Model Provider", risk_rating: "Low", data_processing_role: "Processor" });
  const [registryModalOpen, setRegistryModalOpen] = useState<"model" | "agent" | "vendor" | null>(null);

  // Findings / remediation quick-add (advanced view, Risk Register tab)
  const [newFindingOpen, setNewFindingOpen] = useState(false);
  const [newFindingForm, setNewFindingForm] = useState({ title: "", severity: "High", source: "Manual Review", description: "", control_id: "", system_id: "" });
  const [findingBusy, setFindingBusy] = useState(false);

  const submitNewFinding = async () => {
    if (!newFindingForm.title.trim()) return;
    setFindingBusy(true);
    try {
      await api.createFinding({
        title: newFindingForm.title.trim(),
        severity: newFindingForm.severity,
        source: newFindingForm.source,
        description: newFindingForm.description || undefined,
        control_id: newFindingForm.control_id || undefined,
        system_id: newFindingForm.system_id || undefined,
      });
      setNewFindingForm({ title: "", severity: "High", source: "Manual Review", description: "", control_id: "", system_id: "" });
      setNewFindingOpen(false);
      await loadPlatformData();
    } catch (e: any) {
      alert("Could not create finding: " + (e?.message || e));
    } finally {
      setFindingBusy(false);
    }
  };

  const addRemediationForFinding = async (findingId: string, findingTitle: string) => {
    const title = window.prompt(`Remediation task for "${findingTitle}":`, `Remediate: ${findingTitle}`);
    if (!title) return;
    const assignee = window.prompt("Assign to (name / role):", "AI Engineer") || "AI Engineer";
    try {
      await api.createRemediation({ finding_id: findingId, title, assigned_to: assignee, priority: "High" });
      await loadPlatformData();
    } catch (e: any) {
      alert("Could not create remediation: " + (e?.message || e));
    }
  };

  const closeFinding = async (findingId: string) => {
    if (!window.confirm("Mark this finding Resolved? It stays in the audit trail.")) return;
    try {
      await api.updateFinding(findingId, { status: "Resolved" });
      await loadPlatformData();
    } catch (e: any) {
      alert("Could not update finding: " + (e?.message || e));
    }
  };

  // Knowledge Graph query panel (Phase 2)
  const [graphRequirementId, setGraphRequirementId] = useState("EU-AIA-ART-09");
  const [graphRequirementResult, setGraphRequirementResult] = useState<any>(null);
  const [graphFrameworksInput, setGraphFrameworksInput] = useState("owasp_llm,mitre_atlas");
  const [graphControlsResult, setGraphControlsResult] = useState<any[] | null>(null);
  const [graphToolInput, setGraphToolInput] = useState("");
  const [graphToolResult, setGraphToolResult] = useState<any>(null);
  const [graphVendorExposureResult, setGraphVendorExposureResult] = useState<any[] | null>(null);
  const [graphSharedModelsResult, setGraphSharedModelsResult] = useState<any[] | null>(null);
  const [graphEvidenceResult, setGraphEvidenceResult] = useState<any[] | null>(null);

  // Modals & Drawers
  const [copilotOpen, setCopilotOpen] = useState<boolean>(false);
  const [copilotQuery, setCopilotQuery] = useState<string>("");
  const [copilotLoading, setCopilotLoading] = useState<boolean>(false);
  const [copilotMessages, setCopilotMessages] = useState<any[]>([
    {
      sender: "system",
      text: "Welcome to AegisAI Copilot. I answer from your live tenant data (registered AI systems, controls, evidence) and cited regulatory sources using deterministic rules - not a generative model - so I never fabricate a requirement. Ask me about applicability, crosswalks, or missing controls."
    }
  ]);

  const [selectedSystem, setSelectedSystem] = useState<any>(null);
  const [selectedControl, setSelectedControl] = useState<any>(null);
  const [evidenceModalOpen, setEvidenceModalOpen] = useState<boolean>(false);

  // ---- Cross-linking / deep navigation --------------------------------
  // Any reference to a control, framework requirement, AI system, model,
  // vendor or agent anywhere in the UI can be made clickable and route to the
  // page that owns that record (optionally opening its detail / scrolling to
  // it). `openFramework` + `frameworkHighlight` drive the Frameworks tab's
  // requirement browser.
  const [openFramework, setOpenFramework] = useState<string | null>(null);
  const [frameworkDetail, setFrameworkDetail] = useState<any>(null);
  const [frameworkDetailLoading, setFrameworkDetailLoading] = useState(false);
  const [frameworkHighlight, setFrameworkHighlight] = useState<string | null>(null);
  const [vendorFocusId, setVendorFocusId] = useState<string | null>(null);
  const [modelFocusId, setModelFocusId] = useState<string | null>(null);
  const [agentFocusId, setAgentFocusId] = useState<string | null>(null);

  const [pendingControlCode, setPendingControlCode] = useState<string | null>(null);
  const goToControl = (code: string) => {
    if (!code) return;
    setControlDomainFilter("All");
    setActiveTab("controls");
    setPendingControlCode(code);
  };
  useEffect(() => {
    if (!pendingControlCode) return;
    const ctrl = controls.find((c: any) => c.code === pendingControlCode || c.id === pendingControlCode);
    if (ctrl) { setSelectedControl(ctrl); setPendingControlCode(null); }
    else if (controls.length > 0) { setPendingControlCode(null); }  // not found; give up quietly
  }, [pendingControlCode, controls]);

  const goToFrameworkRequirement = (frameworkId: string, ref?: string, articleLabel?: string) => {
    if (!frameworkId) return;
    setActiveTab("frameworks");
    setFrameworkReqFilter("");   // a deep-link must not be hidden by a stale search
    setOpenFramework(frameworkId);
    // Store both the raw id and the human article label ("Article 9") so the
    // scroll effect can match even when the legacy crosswalk id (EU-AIA-ART-09)
    // differs from the regulatory requirement key (EU-AIA-ARTICLE-9).
    setFrameworkHighlight(ref ? `${ref}␟${articleLabel || ""}` : (articleLabel || null));
  };

  const [pendingSystemId, setPendingSystemId] = useState<string | null>(null);
  const goToSystem = (systemId: string) => {
    if (!systemId) return;
    setInventoryFilter("all");
    setActiveTab("inventory");
    setPendingSystemId(systemId);
  };
  useEffect(() => {
    if (!pendingSystemId) return;
    const sys = aiSystems.find((s: any) => s.id === pendingSystemId);
    if (sys) { setSelectedSystem(sys); setPendingSystemId(null); }
    else if (aiSystems.length > 0) { setPendingSystemId(null); }
  }, [pendingSystemId, aiSystems]);

  // Route to an AI system's next incomplete governance step (spec sections 27, 64).
  const continueGovernance = (systemId: string) => {
    const wf = portfolioWorkflow.find((w: any) => w.system_id === systemId);
    const tab = wf?.next_action?.target_tab || "intake";
    const sys = aiSystems.find((s: any) => s.id === systemId);
    if (tab === "intake" && sys) {
      // seed the intake wizard with this system's name so applicability is for it
      setIntakeForm((f: any) => ({ ...f, system_name: sys.name, business_purpose: sys.business_purpose || sys.description || f.business_purpose }));
      setIntakeStep(1);
    }
    if (tab === "inventory" && sys) { setInventoryFilter("all"); setActiveTab("inventory"); setTimeout(() => setSelectedSystem(sys), 30); return; }
    setActiveTab(tab);
  };

  const goToVendor = (vendorId: string) => { if (!vendorId) return; setVendorFocusId(vendorId); setActiveTab("vendor-registry"); };
  const goToModel = (modelId: string) => { if (!modelId) return; setModelFocusId(modelId); setActiveTab("model-registry"); };
  const goToAgent = (agentId: string) => { if (!agentId) return; setAgentFocusId(agentId); setActiveTab("agent-registry"); };

  // Load a framework's FULL requirement set when one is opened in the Frameworks
  // tab. Prefers the real regulatory ingestion subsystem (source-traceable, the
  // complete set - EU AI Act 419, GDPR 238, NIST 800-53 1014, …); falls back to
  // the legacy catalog only for frameworks that have not been ingested.
  useEffect(() => {
    if (!openFramework) { setFrameworkDetail(null); setFrameworkReqFilter(""); return; }
    let cancelled = false;
    setFrameworkDetailLoading(true);
    setFrameworkReqFilter("");

    const regKey = regKeyFor(openFramework);
    const reg = regFrameworks[regKey];
    const loader = (reg && (reg.requirement_count || 0) > 0)
      ? api.getRegulatoryRequirements(regKey).then((reqs: any[]) => {
          // group by `domain` (chapter/part/function) preserving first-seen order
          const groups: Record<string, any[]> = {};
          const order: string[] = [];
          (reqs || []).forEach(r => {
            const g = r.domain || "Requirements";
            if (!(g in groups)) { groups[g] = []; order.push(g); }
            groups[g].push({
              id: r.requirement_key,
              article: r.source_reference || r.requirement_key,
              title: r.source_reference || r.requirement_key,
              normalized_requirement: r.normalized_requirement,
              source_text: r.source_text,
              obligation_type: r.obligation_type,
              mandatory: r.mandatory,
              review_status: r.review_status,
              effective_from: r.effective_from,
              source_anchor_url: r.source_anchor_url,
            });
          });
          return {
            _regulatory: true,
            name: reg.framework_name,
            official_reference: reg.canonical_identifier || reg.version_label,
            jurisdiction: reg.jurisdiction,
            version: reg.version_label,
            official_url: reg.official_url,
            published_status: reg.published_status,
            coverage: reg.coverage,
            total_requirements: (reqs || []).length,
            chapters: order.map(g => ({ chapter_id: g, title: "", requirements: groups[g] })),
          };
        })
      : api.getFrameworkDetail(openFramework);

    Promise.resolve(loader)
      .then(d => { if (!cancelled) setFrameworkDetail(d); })
      .catch(() => { if (!cancelled) setFrameworkDetail(null); })
      .finally(() => { if (!cancelled) setFrameworkDetailLoading(false); });
    return () => { cancelled = true; };
  }, [openFramework, regFrameworks]);

  // Once a framework detail is loaded and a highlight ref is set, scroll to it.
  // Best-effort match: exact requirement-key id, then by the article label
  // ("Article 9"), then a normalised form (ART-09 ~ ARTICLE-9).
  useEffect(() => {
    if (!frameworkDetail || !frameworkHighlight) return;
    const [rawRef, articleLabel] = frameworkHighlight.split("␟");
    const norm = (s: string) => (s || "").toUpperCase().replace(/ARTICLE|ART\.?|SECTION|SEC\.?|POINT|PARA(GRAPH)?/g, "A").replace(/[^A-Z0-9]/g, "").replace(/A0+/g, "A");
    const t = setTimeout(() => {
      let el: HTMLElement | null = rawRef ? document.getElementById(`req-${rawRef}`) : null;
      if (!el) {
        const rows = Array.from(document.querySelectorAll<HTMLElement>('[id^="req-"]'));
        const targetNorm = norm(rawRef || articleLabel || "");
        el =
          (articleLabel && rows.find(r => r.querySelector(".font-mono")?.textContent?.trim().toLowerCase() === articleLabel.trim().toLowerCase())) ||
          (targetNorm && rows.find(r => norm(r.id.replace(/^req-/, "")) === targetNorm)) ||
          (articleLabel && rows.find(r => (r.textContent || "").toLowerCase().includes(articleLabel.trim().toLowerCase()))) ||
          null;
      }
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("ring-2", "ring-sky-400");
        setTimeout(() => el && el.classList.remove("ring-2", "ring-sky-400"), 2600);
      }
    }, 160);
    return () => clearTimeout(t);
  }, [frameworkDetail, frameworkHighlight]);

  // Scroll to and briefly highlight a model / vendor / agent when arriving from a cross-link.
  useEffect(() => {
    const map: [string, string | null, () => void][] = [
      ["model", modelFocusId, () => setModelFocusId(null)],
      ["vendor", vendorFocusId, () => setVendorFocusId(null)],
      ["agent", agentFocusId, () => setAgentFocusId(null)],
    ];
    const active = map.find(([, id]) => id);
    if (!active) return;
    const [prefix, id, clear] = active;
    const t = setTimeout(() => {
      document.getElementById(`${prefix}-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 250);
    const c = setTimeout(clear, 3000);
    return () => { clearTimeout(t); clearTimeout(c); };
  }, [modelFocusId, vendorFocusId, agentFocusId]);

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

  // New Evidence Form State
  const [newEvidence, setNewEvidence] = useState({
    title: "",
    description: "",
    evidence_type: "Policy",
    file_url: "https://storage.acmefinancial.internal/evidence/doc.pdf",
    selected_controls: [] as string[]
  });

  // Filter states
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [controlDomainFilter, setControlDomainFilter] = useState<string>("All");

  // Load initial data
  const loadPlatformData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [
        dashData,
        systemsData,
        fwData,
        ctrlData,
        cwData,
        evData,
        agentData,
        vndData,
        riskData,
        findData,
        remData,
        auditData,
        regModels,
        regAgents,
        regVendors,
        permGraph
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
        api.getModels(),
        api.getAgentRegistry(),
        api.getVendorRegistry(),
        api.getAgentPermissionGraph()
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
      setRegistryModels(regModels);
      setRegistryAgents(regAgents);
      setRegistryVendors(regVendors);
      setPermissionGraph(permGraph);

      // Non-blocking: pull the real regulatory framework catalog (full
      // requirement counts + source metadata). A failure here must not break
      // the rest of the dashboard, so it is fetched separately.
      api.getRegulatoryFrameworks()
        .then((rf: any[]) => {
          const byKey: Record<string, any> = {};
          (rf || []).forEach(f => { byKey[f.framework_key] = f; });
          setRegFrameworks(byKey);
        })
        .catch(() => { /* regulatory subsystem unavailable - keep legacy counts */ });

      api.getPortfolioWorkflow()
        .then((pw: any[]) => setPortfolioWorkflow(pw || []))
        .catch(() => setPortfolioWorkflow([]));

      api.getAssessments().then((a: any[]) => setAssessmentsList(a || [])).catch(() => setAssessmentsList([]));
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
    if (user && user.ui_mode !== "simple") {
      loadPlatformData();
    } else {
      setLoading(false);
    }
  }, []);

  const handleLoginSuccess = (user: api.CurrentUser) => {
    setCurrentUser(user);
    if (user.ui_mode !== "simple") loadPlatformData();
  };

  // Handle Intake Evaluation
  const runIntakeEvaluation = async () => {
    try {
      setEvaluatingIntake(true);
      const res = await api.evaluateIntake(intakeForm);
      setIntakeResult(res);
      setIntakeStep(4);
    } catch (err: any) {
      alert("Evaluation error: " + err.message);
    } finally {
      setEvaluatingIntake(false);
    }
  };

  // Register Evaluated System to Inventory
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
      alert(`System '${intakeForm.system_name}' successfully added to AI Inventory!`);
      loadPlatformData();
      setActiveTab("inventory");
      setIntakeStep(1);
      setIntakeResult(null);
    } catch (err: any) {
      alert("Registration failed: " + err.message);
    }
  };

  // Toggle Kill-Switch
  const handleKillSwitch = async (agentId: string) => {
    try {
      const res = await api.triggerKillSwitch(agentId);
      alert(res.message);
      loadPlatformData();
    } catch (err: any) {
      alert("Kill switch trigger failed: " + err.message);
    }
  };

  // Registry: Model / Agent / Vendor creation handlers
  const handleCreateModel = async () => {
    if (!newModelForm.name || !newModelForm.system_id) {
      alert("Model name and originating AI System are required");
      return;
    }
    try {
      await api.createModel(newModelForm);
      setRegistryModalOpen(null);
      setNewModelForm({ name: "", provider: "OpenAI", version: "1.0", model_type: "LLM", system_id: "" });
      loadPlatformData();
    } catch (err: any) {
      alert("Failed to create model: " + err.message);
    }
  };

  const handleCreateAgent = async () => {
    if (!newAgentForm.name || !newAgentForm.system_id) {
      alert("Agent name and owning AI System are required");
      return;
    }
    try {
      await api.createAgent(newAgentForm);
      setRegistryModalOpen(null);
      setNewAgentForm({
        name: "", system_id: "", purpose: "", has_code_execution: false, has_database_access: false,
        has_payment_access: false, has_git_access: false, has_git_write_access: false, accesses_pii: false,
        autonomy_level: "Semi-Autonomous", human_approval_required: true
      });
      loadPlatformData();
    } catch (err: any) {
      alert("Failed to create agent: " + err.message);
    }
  };

  const handleCreateVendor = async () => {
    if (!newVendorForm.name) {
      alert("Vendor name is required");
      return;
    }
    try {
      await api.createVendor(newVendorForm);
      setRegistryModalOpen(null);
      setNewVendorForm({ name: "", service_type: "Foundation Model Provider", risk_rating: "Low", data_processing_role: "Processor" });
      loadPlatformData();
    } catch (err: any) {
      alert("Failed to create vendor: " + err.message);
    }
  };

  const viewModelDependents = async (modelId: string) => {
    try {
      const deps = await api.getModelDependents(modelId);
      setModelDependents(deps);
    } catch (err: any) {
      alert("Failed to load model dependents: " + err.message);
    }
  };

  // Knowledge Graph query handlers
  const runRequirementQuery = async () => {
    try { setGraphRequirementResult(await api.graphRequirementAffectedSystems(graphRequirementId.trim())); }
    catch (err: any) { alert("Query failed: " + err.message); }
  };
  const runControlsQuery = async () => {
    try { setGraphControlsResult(await api.graphControlsMultiFramework(graphFrameworksInput.split(",").map(f => f.trim()).filter(Boolean))); }
    catch (err: any) { alert("Query failed: " + err.message); }
  };
  const runToolQuery = async () => {
    if (!graphToolInput.trim()) return;
    try { setGraphToolResult(await api.graphAgentToolDependents(graphToolInput.trim())); }
    catch (err: any) { alert("Query failed: " + err.message); }
  };
  const loadVendorExposure = async () => {
    try { setGraphVendorExposureResult(await api.graphVendorExposure()); }
    catch (err: any) { alert("Query failed: " + err.message); }
  };
  const loadSharedModels = async () => {
    try { setGraphSharedModelsResult(await api.graphSharedHighRiskModels()); }
    catch (err: any) { alert("Query failed: " + err.message); }
  };
  const loadEvidenceCoverage = async () => {
    try { setGraphEvidenceResult(await api.graphEvidenceHighestCoverage()); }
    catch (err: any) { alert("Query failed: " + err.message); }
  };

  const viewVendorImpact = async (vendorId: string) => {
    try {
      const impact = await api.getVendorImpact(vendorId);
      setVendorImpact(impact);
    } catch (err: any) {
      alert("Failed to load vendor impact: " + err.message);
    }
  };

  // Update Control Status
  const handleUpdateControl = async (controlId: string, status: string, eff: string) => {
    try {
      await api.updateControl(controlId, {
        status,
        effectiveness: eff,
        implementation_notes: "Updated from AegisAI Control Operations"
      });
      loadPlatformData();
      setSelectedControl(null);
    } catch (err: any) {
      alert("Failed to update control: " + err.message);
    }
  };

  // Handle Evidence Upload
  const handleUploadEvidence = async () => {
    if (!newEvidence.title) {
      alert("Please provide an evidence title");
      return;
    }
    try {
      await api.uploadEvidence({
        title: newEvidence.title,
        description: newEvidence.description,
        evidence_type: newEvidence.evidence_type,
        file_url: newEvidence.file_url,
        control_ids: newEvidence.selected_controls
      });
      alert("Evidence artifact successfully uploaded and mapped across frameworks!");
      setEvidenceModalOpen(false);
      setNewEvidence({ title: "", description: "", evidence_type: "Policy", file_url: "", selected_controls: [] });
      loadPlatformData();
    } catch (err: any) {
      alert("Evidence upload failed: " + err.message);
    }
  };

  // Handle Remediation Status
  const handleRemediationToggle = async (taskId: string, currentStatus: string) => {
    const nextStatus = currentStatus === "Done" ? "In Progress" : "Done";
    try {
      await api.updateRemediation(taskId, nextStatus);
      loadPlatformData();
    } catch (err: any) {
      alert("Failed to update task: " + err.message);
    }
  };

  // Handle Copilot Query
  const handleCopilotSend = async () => {
    if (!copilotQuery.trim()) return;
    const userQ = copilotQuery;
    setCopilotQuery("");
    setCopilotMessages(prev => [...prev, { sender: "user", text: userQ }]);
    setCopilotLoading(true);

    try {
      const res = await api.queryCopilot(userQ);
      setCopilotMessages(prev => [
        ...prev,
        {
          sender: "copilot",
          text: res.answer,
          citations: res.citations
        }
      ]);
    } catch (err: any) {
      setCopilotMessages(prev => [
        ...prev,
        { sender: "copilot", text: "Error contacting Copilot engine: " + err.message }
      ]);
    } finally {
      setCopilotLoading(false);
    }
  };

  if (!authChecked) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#090D16]">
        <RefreshCw className="w-6 h-6 text-sky-400 animate-spin" />
      </div>
    );
  }

  if (!currentUser) {
    return <LoginScreen onSuccess={handleLoginSuccess} />;
  }

  // SME "simple" experience - same backend, guided lens. Switching to advanced
  // flips ui_mode and drops through to the full enterprise console below.
  if (currentUser.ui_mode === "simple") {
    return (
      <SmeExperience
        key={currentUser.organization_id || "sme"}
        user={currentUser}
        onUserChange={(u) => {
          setCurrentUser(u);
          if (u.ui_mode !== "simple") loadPlatformData();
        }}
        onLogout={() => { api.logout(); setCurrentUser(null); }}
      />
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#090D16] text-[#F8FAFC]">
      {/* ========================================================================= */}
      {/* 1. SIDEBAR NAVIGATION                                                    */}
      {/* ========================================================================= */}
      <aside className="w-64 flex-shrink-0 flex flex-col border-r border-white/10 bg-[#0B0F1A]/95 backdrop-blur-xl">
        {/* Brand Header */}
        <div className="p-5 border-b border-white/10 flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/25">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-bold text-lg tracking-tight flex items-center gap-1.5">
              <span>Aegis</span>
              <span className="text-sky-400 font-extrabold text-xs px-1.5 py-0.5 rounded bg-sky-500/10 border border-sky-500/20">OS</span>
            </div>
            <div className="text-[11px] text-slate-400">AI Trust & Compliance</div>
          </div>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Core Governance
          </div>
          {[
            { id: "dashboard", label: "Executive Dashboard", icon: Activity },
            { id: "inventory", label: "AI Systems Inventory", icon: Brain, badge: aiSystems.length },
            { id: "intake", label: "Intake & Classification", icon: Sliders },
            { id: "controls", label: "Unified Controls", icon: Layers, badge: controls.length },
            { id: "crosswalk", label: "17-Framework Crosswalk", icon: RefreshCw }
          ].map(item => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  active
                    ? "bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm shadow-sky-500/10"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${active ? "text-sky-400" : "text-slate-400"}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
                    active ? "bg-sky-400/20 text-sky-300" : "bg-white/10 text-slate-400"
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}

          <div className="pt-4 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            AI Registry
          </div>
          {[
            { id: "model-registry", label: "Models", icon: Cpu, badge: registryModels.length },
            { id: "agent-registry", label: "Agents", icon: Terminal, badge: registryAgents.length },
            { id: "vendor-registry", label: "Vendors", icon: Building, badge: registryVendors.length },
            { id: "governance-graph", label: "Governance Graph", icon: RefreshCw }
          ].map(item => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  active
                    ? "bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm shadow-sky-500/10"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${active ? "text-sky-400" : "text-slate-400"}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
                    active ? "bg-sky-400/20 text-sky-300" : "bg-white/10 text-slate-400"
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}

          <div className="pt-4 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Compliance & Assurance
          </div>
          {[
            { id: "assessments", label: "Assessments", icon: FileCheck, badge: assessmentsList.length },
            { id: "frameworks", label: "Authoritative Frameworks", icon: FileCheck, badge: "17" },
            { id: "evidence", label: "Evidence Vault", icon: Lock, badge: evidenceList.length },
            { id: "security", label: "AI Security & Agents", icon: Terminal, badge: agents.length },
            { id: "risks", label: "Risk Register & SLA", icon: AlertTriangle, badge: findings.length },
            { id: "reports", label: "Executive Reports", icon: FileText },
            { id: "audit", label: "Audit Trail", icon: Clock }
          ].map(item => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  active
                    ? "bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm shadow-sky-500/10"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${active ? "text-sky-400" : "text-slate-400"}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
                    active ? "bg-sky-400/20 text-sky-300" : "bg-white/10 text-slate-400"
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Tenant Profile Footer */}
        <div className="p-3 border-t border-white/10 bg-black/20">
          <div className="flex items-center gap-2.5 p-2 rounded-lg bg-white/5 border border-white/5">
            <div className="w-8 h-8 rounded-full bg-indigo-600/30 border border-indigo-400/30 flex items-center justify-center text-xs font-bold text-indigo-300">
              {(currentUser?.full_name || "?").split(" ").map((n: string) => n[0]).slice(0, 2).join("").toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-slate-200 truncate">{currentUser?.full_name || "Unknown User"}</div>
              <div className="text-[10px] text-slate-400 truncate">{currentUser?.role || ""}</div>
            </div>
            <button
              onClick={() => { api.logout(); setCurrentUser(null); }}
              className="text-[10px] text-slate-400 hover:text-red-400 font-medium px-1.5 py-1 rounded hover:bg-white/5 transition-colors"
              title="Sign out"
            >
              Sign out
            </button>
          </div>
          <button
            onClick={async () => {
              try {
                const u = await api.setUiMode("simple");
                setCurrentUser(u);
              } catch { /* ignore */ }
            }}
            className="mt-2 w-full text-[10px] text-slate-500 hover:text-sky-300 py-1 rounded hover:bg-white/5 transition-colors"
            title="Switch to the simplified SME view (same data, guided experience)"
          >
            Switch to simple view
          </button>
        </div>
      </aside>

      {/* ========================================================================= */}
      {/* 2. MAIN CONTENT AREA                                                     */}
      {/* ========================================================================= */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Global Header */}
        <header className="h-16 flex-shrink-0 border-b border-white/10 px-6 flex items-center justify-between bg-[#0B0F1A]/80 backdrop-blur-lg">
          <div className="flex items-center gap-4">
            <CompanySwitcher
              activeName={currentUser?.organization_name}
              onSwitched={async () => {
                const me = await api.getCurrentUser();
                setCurrentUser(me);
                setActiveTab("dashboard");
                await loadPlatformData();
              }}
            />
            <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-400">
              <span>Readiness Posture:</span>
              <span className="font-bold text-sky-400">{metrics?.overall_readiness_percentage ?? 0}%</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Disclaimer pill */}
            <div className="hidden md:flex items-center gap-1.5 text-[11px] text-amber-300/80 bg-amber-500/10 px-2.5 py-1 rounded border border-amber-500/20">
              <AlertOctagon className="w-3.5 h-3.5 text-amber-400" />
              <span>Governance Guidance • Not Legal Advice</span>
            </div>

            {/* AI Copilot trigger button */}
            <button
              onClick={() => setCopilotOpen(true)}
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-sky-500/20 to-indigo-500/20 border border-sky-400/40 text-xs font-semibold text-sky-300 hover:border-sky-400 transition-all shadow-sm shadow-sky-500/20"
            >
              <SparklesIcon className="w-3.5 h-3.5 text-sky-400 animate-pulse" />
              <span>Ask AI Copilot</span>
            </button>
          </div>
        </header>

        {/* Scrollable Workspace View */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="h-64 flex flex-col items-center justify-center gap-3">
              <RefreshCw className="w-6 h-6 text-sky-400 animate-spin" />
              <div className="text-xs text-slate-400">Connecting to AegisAI Governance Engine...</div>
            </div>
          )}

          {!loading && error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <div>{error}</div>
            </div>
          )}

          {!loading && !error && (
            <>
              {/* ============================================================ */}
              {/* TAB 1: EXECUTIVE DASHBOARD                                  */}
              {/* ============================================================ */}
              {activeTab === "dashboard" && metrics && aiSystems.length === 0 && (
                <div className="max-w-xl mx-auto mt-16 text-center space-y-4 animate-fadeIn">
                  <div className="w-14 h-14 mx-auto rounded-2xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center">
                    <Brain className="w-7 h-7 text-sky-400" />
                  </div>
                  <h1 className="text-xl font-bold text-white">
                    {currentUser?.organization_name || "Your organization"} is ready.
                  </h1>
                  <p className="text-sm text-slate-400">
                    The primary governance journey is: register an AI system → assess applicability → run an assessment →
                    assign controls → add evidence → test → resolve findings → approve → report.
                    Start by registering your first AI system.
                  </p>
                  <button
                    onClick={() => { setIntakeStep(1); setActiveTab("intake"); }}
                    className="px-5 py-2.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-sm inline-flex items-center gap-2"
                  >
                    <Play className="w-4 h-4" /> Add your first AI system
                  </button>
                  <div className="text-[11px] text-slate-500 pt-2">
                    Wrong company? Use the company selector in the header to switch or add another.
                  </div>
                </div>
              )}

              {activeTab === "dashboard" && metrics && aiSystems.length > 0 && (
                <div className="space-y-6 animate-fadeIn">
                  {/* Governance journey - needs attention + per-system next action (spec §7, §27, §43, §44) */}
                  {(() => {
                    const pw = portfolioWorkflow;
                    const byAction: Record<string, any[]> = {};
                    pw.forEach((s: any) => {
                      const k = s.next_action?.key || "monitor";
                      (byAction[k] = byAction[k] || []).push(s);
                    });
                    const ATTN: [string, string][] = [
                      ["assess_applicability", "need an applicability review"],
                      ["start_assessment", "ready to start an assessment"],
                      ["continue_assessment", "have an assessment in progress"],
                      ["add_evidence", "need evidence"],
                      ["test_controls", "need control testing"],
                      ["fix_findings", "have open findings to fix"],
                      ["submit_for_approval", "are ready to submit for approval"],
                      ["await_approval", "are awaiting approval"],
                      ["generate_report", "are approved - generate the report"],
                    ];
                    const rows = ATTN.filter(([k]) => byAction[k]?.length);
                    if (rows.length === 0) return null;
                    return (
                      <div className="p-5 rounded-xl glass-panel border border-amber-500/20 space-y-3">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-amber-400" />
                          <h2 className="text-sm font-bold text-slate-100">Needs attention</h2>
                        </div>
                        <div className="space-y-1.5">
                          {rows.map(([k, phrase]) => {
                            const systems = byAction[k];
                            return (
                              <button key={k}
                                onClick={() => continueGovernance(systems[0].system_id)}
                                className="w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-black/30 border border-white/5 hover:border-sky-500/40 text-left text-xs transition-colors"
                              >
                                <span className="text-slate-200">
                                  <span className="font-bold text-sky-300">{systems.length}</span> AI system{systems.length === 1 ? "" : "s"} {phrase}
                                  <span className="text-slate-500"> — {systems.slice(0, 3).map((s: any) => s.name).join(", ")}{systems.length > 3 ? "…" : ""}</span>
                                </span>
                                <span className="text-sky-400 flex items-center gap-1 flex-shrink-0">{systems[0].next_action.label} <ChevronRight className="w-3.5 h-3.5" /></span>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Hero Metric Banner */}
                  <div className="p-6 rounded-2xl bg-gradient-to-br from-sky-950/40 via-indigo-950/20 to-slate-900/60 border border-sky-500/20 relative overflow-hidden">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
                      <div>
                        <div className="inline-flex items-center gap-2 text-[11px] font-semibold text-sky-400 uppercase tracking-wider mb-2">
                          <Shield className="w-3.5 h-3.5" /> Enterprise AI Trust & Compliance Baseline
                        </div>
                        <h1 className="text-2xl font-bold tracking-tight text-white">
                          {(currentUser?.organization_name || "Your organization")} AI Governance Health: <span className="text-sky-400">{metrics.overall_readiness_percentage}% Readiness</span>
                        </h1>
                        <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
                          Unified compliance across 17 authoritative international standards including EU AI Act, NIST AI RMF, NIST AI 600-1, OWASP LLM, CRA, GDPR, and DORA.
                        </p>
                      </div>

                      {/* Multi-Dimensional Readiness Score Card - each dimension links to where it is managed.
                          Readiness = 40% implementation + 35% evidence + 25% effectiveness, minus open-finding deductions. */}
                      <div className="flex items-center gap-4 bg-black/40 p-3 rounded-xl border border-white/10 backdrop-blur-md"
                        title="Overall readiness = 40% implementation + 35% evidence + 25% effectiveness, minus open-finding deductions (max 30). Click a dimension to manage it.">
                        <button onClick={() => setActiveTab("controls")} className="text-center px-3 border-r border-white/10 hover:bg-white/5 rounded transition-colors">
                          <div className="text-lg font-extrabold text-emerald-400">{metrics.implementation_score}%</div>
                          <div className="text-[10px] text-slate-400">Implemented</div>
                        </button>
                        <button onClick={() => setActiveTab("evidence")} className="text-center px-3 border-r border-white/10 hover:bg-white/5 rounded transition-colors">
                          <div className="text-lg font-extrabold text-sky-400">{metrics.evidence_completeness_score}%</div>
                          <div className="text-[10px] text-slate-400">Evidence</div>
                        </button>
                        <button onClick={() => setActiveTab("controls")} className="text-center px-3 hover:bg-white/5 rounded transition-colors">
                          <div className="text-lg font-extrabold text-indigo-400">{metrics.control_effectiveness_score}%</div>
                          <div className="text-[10px] text-slate-400">Effective</div>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* 6 Key Stat Cards - each drills through to the page that holds those records */}
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                    {[
                      { label: "Total AI Systems", val: metrics.total_ai_systems, desc: "Active in Inventory", color: "text-white", target: "inventory" },
                      { label: "High-Risk (Annex III)", val: metrics.high_risk_systems_count, desc: "Mandatory EU Oversight", color: "text-rose-400", target: "inventory", filter: "high-risk" },
                      { label: "Generative AI", val: metrics.genai_systems_count, desc: "LLM / RAG Pipelines", color: "text-purple-400", target: "inventory", filter: "genai" },
                      { label: "Agentic AI", val: metrics.agentic_systems_count, desc: "Tool & Code Execution", color: "text-amber-400", target: "agent-registry" },
                      { label: "Active Evidence", val: metrics.active_evidence_artifacts_count, desc: "Cryptographic Vault", color: "text-emerald-400", target: "evidence" },
                      { label: "Open Findings", val: metrics.open_findings_count, desc: `${metrics.critical_findings_count} Critical SLA`, color: "text-amber-300", target: "risks" }
                    ].map((stat, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => { setInventoryFilter((stat.filter as "all" | "high-risk" | "genai" | "agentic") || "all"); setActiveTab(stat.target); }}
                        title={`View ${stat.label} in ${stat.target === "inventory" ? "AI Systems Inventory" : stat.target === "agent-registry" ? "Agents" : stat.target === "evidence" ? "Evidence Vault" : "Risk Register"}`}
                        className="p-4 rounded-xl glass-panel glass-panel-hover text-left hover:border-sky-500/40 transition-colors group"
                      >
                        <div className="text-xs text-slate-400 flex items-center justify-between">
                          {stat.label}
                          <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-sky-400 transition-colors" />
                        </div>
                        <div className={`text-2xl font-bold mt-1 ${stat.color}`}>{stat.val}</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">{stat.desc}</div>
                      </button>
                    ))}
                  </div>

                  {/* Framework Readiness Progress Matrix */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="p-5 rounded-xl glass-panel space-y-4">
                      <div className="flex items-center justify-between">
                        <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                          <FileCheck className="w-4 h-4 text-sky-400" />
                          Framework Readiness Breakdown
                        </h2>
                        <span className="text-[11px] text-slate-400">17 Ingested Standards</span>
                      </div>

                      <div className="space-y-3">
                        {Object.keys(metrics.framework_readiness || {}).length === 0 && (metrics.unassessed_frameworks || []).length === 0 && (
                          <div className="text-xs text-slate-500 italic">No frameworks recommended yet. Run intake classification on an AI system to begin.</div>
                        )}
                        {Object.entries(metrics.framework_readiness || {}).map(([fwName, pct]: any) => (
                          <button key={fwName} type="button" onClick={() => setActiveTab("frameworks")}
                            className="w-full space-y-1 text-left group" title={`Open ${fwName} in Authoritative Frameworks`}>
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-medium text-slate-300 group-hover:text-sky-300 transition-colors">{fwName}</span>
                              <span className="font-bold text-sky-400">{pct}%</span>
                            </div>
                            <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-sky-500 to-indigo-500 transition-all duration-500"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </button>
                        ))}
                        {(metrics.unassessed_frameworks || []).map((fwName: string) => (
                          <button key={fwName} type="button" onClick={() => setActiveTab("frameworks")}
                            className="w-full space-y-1 text-left opacity-60 hover:opacity-100 transition-opacity group" title={`Open ${fwName} in Authoritative Frameworks`}>
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-medium text-slate-400 group-hover:text-sky-300 transition-colors">{fwName}</span>
                              <span className="font-semibold text-slate-500">Not Assessed</span>
                            </div>
                            <div className="w-full h-2 rounded-full bg-slate-800/60 overflow-hidden">
                              <div className="h-full rounded-full bg-slate-700 border border-dashed border-slate-600" style={{ width: "100%" }} />
                            </div>
                          </button>
                        ))}
                      </div>
                      <div className="text-[10px] text-slate-500 pt-1">
                        Readiness is calculated only from frameworks with a completed Assessment for this tenant - never estimated from an unrelated overall score.
                      </div>
                    </div>

                    {/* Risk Categories & Quick Actions */}
                    <div className="space-y-6">
                      <div className="p-5 rounded-xl glass-panel space-y-3">
                        <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-amber-400" />
                          AI Risk Distribution by Domain
                        </h2>
                        <div className="grid grid-cols-3 gap-3 pt-2">
                          {Object.entries(metrics.risk_category_distribution || {}).map(([cat, count]: any) => (
                            <button key={cat} type="button" onClick={() => setActiveTab("risks")}
                              className="p-3 rounded-lg bg-black/30 border border-white/5 text-center hover:border-amber-500/40 transition-colors" title={`View ${cat} risks in the Risk Register`}>
                              <div className="text-lg font-bold text-slate-200">{count}</div>
                              <div className="text-[11px] text-slate-400 capitalize">{cat}</div>
                            </button>
                          ))}
                          {Object.keys(metrics.risk_category_distribution || {}).length === 0 && (
                            <div className="col-span-3 text-[11px] text-slate-500 text-center py-2">No risks recorded yet.</div>
                          )}
                        </div>
                      </div>

                      <div className="p-5 rounded-xl glass-panel space-y-3">
                        <h2 className="text-sm font-bold text-slate-200">Governance Quick Actions</h2>
                        <div className="grid grid-cols-2 gap-3">
                          <button
                            onClick={() => setActiveTab("intake")}
                            className="p-3 rounded-lg bg-sky-500/10 border border-sky-500/20 text-left hover:border-sky-500/40 transition-all"
                          >
                            <div className="text-xs font-semibold text-sky-300 flex items-center gap-1.5">
                              <Play className="w-3 h-3" /> New System Intake
                            </div>
                            <div className="text-[10px] text-slate-400 mt-1">Classify risk & regulatory applicability</div>
                          </button>
                          <button
                            onClick={() => setEvidenceModalOpen(true)}
                            className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-left hover:border-emerald-500/40 transition-all"
                          >
                            <div className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
                              <Lock className="w-3 h-3" /> Upload Evidence
                            </div>
                            <div className="text-[10px] text-slate-400 mt-1">Attach artifact to multiple controls</div>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB 2: AI SYSTEMS INVENTORY                                 */}
              {/* ============================================================ */}
              {activeTab === "inventory" && (
                <div className="space-y-4 animate-fadeIn">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <h1 className="text-lg font-bold text-white flex items-center gap-2">
                        <Brain className="w-5 h-5 text-sky-400" />
                        AI System Inventory & Registry
                      </h1>
                      <p className="text-xs text-slate-400">
                        Central registry mapping AI systems to foundation models, datasets, autonomous agents, and regulatory risk tiers.
                      </p>
                    </div>
                    <button
                      onClick={() => { setIntakeStep(1); setActiveTab("intake"); }}
                      className="px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 shadow-md shadow-sky-500/25 transition-all flex-shrink-0"
                    >
                      <Plus className="w-4 h-4" /> Add AI System
                    </button>
                  </div>

                  {/* Filter chips (set when arriving from a dashboard stat card) */}
                  <div className="flex items-center gap-2 flex-wrap text-[11px]">
                    {([
                      ["all", "All systems"],
                      ["high-risk", "High-Risk (Annex III)"],
                      ["genai", "Generative AI"],
                      ["agentic", "Agentic AI"],
                    ] as [typeof inventoryFilter, string][]).map(([key, label]) => (
                      <button
                        key={key}
                        onClick={() => setInventoryFilter(key)}
                        className={`px-2.5 py-1 rounded-full border transition-colors ${
                          inventoryFilter === key
                            ? "bg-sky-500/15 border-sky-500/40 text-sky-200"
                            : "bg-white/5 border-white/10 text-slate-400 hover:border-white/20"
                        }`}
                      >
                        {label}
                        {key !== "all" && (
                          <span className="ml-1.5 text-slate-500">
                            {aiSystems.filter((s: any) =>
                              key === "high-risk" ? String(s.risk_classification || "").includes("High")
                              : key === "genai" ? s.is_generative_ai
                              : key === "agentic" ? s.is_agentic_ai : true
                            ).length}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>

                  {/* Systems Table */}
                  <div className="rounded-xl glass-panel overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/80 border-b border-white/10 text-slate-400 font-semibold">
                        <tr>
                          <th className="p-3.5">System Name & Purpose</th>
                          <th className="p-3.5">Business Unit</th>
                          <th className="p-3.5">Tech & Model</th>
                          <th className="p-3.5">Risk Tier</th>
                          <th className="p-3.5">EU AI Act Tier</th>
                          <th className="p-3.5">Governance Progress</th>
                          <th className="p-3.5 text-right">Next Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {aiSystems
                          .filter((sys: any) =>
                            inventoryFilter === "high-risk" ? String(sys.risk_classification || "").includes("High")
                            : inventoryFilter === "genai" ? sys.is_generative_ai
                            : inventoryFilter === "agentic" ? sys.is_agentic_ai
                            : true
                          )
                          .map(sys => (
                          <tr key={sys.id} className="hover:bg-white/[0.02] transition-colors">
                            <td className="p-3.5">
                              <div className="font-semibold text-slate-100">{sys.name}</div>
                              <div className="text-[11px] text-slate-400 line-clamp-1 max-w-sm">{sys.description}</div>
                            </td>
                            <td className="p-3.5 text-slate-300">{sys.business_unit}</td>
                            <td className="p-3.5">
                              <div className="text-slate-200 font-medium">{sys.model_provider} {sys.model_name}</div>
                              <div className="text-[10px] text-slate-400">{sys.ai_technology}</div>
                            </td>
                            <td className="p-3.5">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                sys.risk_classification.includes("High")
                                  ? "bg-rose-500/10 text-rose-300 border-rose-500/20"
                                  : sys.risk_classification.includes("Transparency")
                                  ? "bg-purple-500/10 text-purple-300 border-purple-500/20"
                                  : "bg-slate-500/10 text-slate-300 border-slate-500/20"
                              }`}>
                                {sys.risk_classification}
                              </span>
                            </td>
                            <td className="p-3.5 text-[11px] text-slate-300 font-mono">
                              {sys.eu_ai_act_classification}
                            </td>
                            <td className="p-3.5">
                              {(() => {
                                const wf = portfolioWorkflow.find((w: any) => w.system_id === sys.id);
                                if (!wf) return <span className="text-[10px] text-slate-500">—</span>;
                                return (
                                  <div className="flex items-center gap-2">
                                    <div className="w-20 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                                      <div className="h-full rounded-full bg-gradient-to-r from-sky-500 to-emerald-500" style={{ width: `${Math.round(100 * wf.completed_steps / wf.total_steps)}%` }} />
                                    </div>
                                    <span className="text-[10px] text-slate-400">{wf.completed_steps}/{wf.total_steps}</span>
                                    {wf.open_findings > 0 && <span className="text-[9px] text-rose-300 bg-rose-500/10 px-1 rounded border border-rose-500/30">{wf.open_findings} finding{wf.open_findings === 1 ? "" : "s"}</span>}
                                  </div>
                                );
                              })()}
                            </td>
                            <td className="p-3.5 text-right">
                              {(() => {
                                const wf = portfolioWorkflow.find((w: any) => w.system_id === sys.id);
                                return (
                                  <div className="flex items-center gap-1.5 justify-end">
                                    {wf?.next_action && (
                                      <button
                                        onClick={() => continueGovernance(sys.id)}
                                        title={wf.next_action.helper}
                                        className="px-2.5 py-1 rounded bg-sky-500 hover:bg-sky-400 text-slate-950 text-[11px] font-semibold transition-all"
                                      >
                                        {wf.next_action.label}
                                      </button>
                                    )}
                                    <button
                                      onClick={() => setSelectedSystem(sys)}
                                      className="px-2.5 py-1 rounded bg-white/5 hover:bg-white/10 text-sky-400 text-[11px] border border-white/10 transition-all"
                                    >
                                      Details
                                    </button>
                                  </div>
                                );
                              })()}
                            </td>
                          </tr>
                        ))}
                        {aiSystems.length === 0 && (
                          <tr><td colSpan={7} className="p-6 text-center text-xs text-slate-500">
                            <div className="space-y-2">
                              <p>No AI systems registered yet. Register your first AI system to determine applicable regulations and begin governance.</p>
                              <button onClick={() => { setIntakeStep(1); setActiveTab("intake"); }}
                                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs">
                                <Plus className="w-4 h-4" /> Add AI System
                              </button>
                            </div>
                          </td></tr>
                        )}
                        {aiSystems.length > 0 && aiSystems.filter((sys: any) =>
                            inventoryFilter === "high-risk" ? String(sys.risk_classification || "").includes("High")
                            : inventoryFilter === "genai" ? sys.is_generative_ai
                            : inventoryFilter === "agentic" ? sys.is_agentic_ai : true).length === 0 && (
                          <tr><td colSpan={7} className="p-6 text-center text-xs text-slate-500">
                            No systems match this filter. <button onClick={() => setInventoryFilter("all")} className="text-sky-400 hover:underline">Show all</button>
                          </td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB 3: DYNAMIC INTAKE & CLASSIFICATION WIZARD               */}
              {/* ============================================================ */}
              {activeTab === "intake" && (
                <div className="space-y-6 max-w-4xl mx-auto animate-fadeIn">
                  <div>
                    <h1 className="text-lg font-bold text-white flex items-center gap-2">
                      <Sliders className="w-5 h-5 text-sky-400" />
                      Guided AI System Intake & Applicability Wizard
                    </h1>
                    <p className="text-xs text-slate-400">
                      Answer dynamic architectural and legal questions to automatically determine EU AI Act classification, privacy obligations, and required unified controls.
                    </p>
                  </div>

                  {/* Step Progress Bar */}
                  <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-white/10 text-xs">
                    {[
                      { step: 1, label: "1. Scope & Geography" },
                      { step: 2, label: "2. Decision & Data Impact" },
                      { step: 3, label: "3. GenAI & Agent Autonomy" },
                      { step: 4, label: "4. Automated Classification" }
                    ].map(s => (
                      <div
                        key={s.step}
                        className={`flex items-center gap-2 font-medium ${
                          intakeStep === s.step ? "text-sky-400 font-bold" : intakeStep > s.step ? "text-emerald-400" : "text-slate-400"
                        }`}
                      >
                        <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                          intakeStep === s.step ? "bg-sky-500 text-slate-950 font-bold" : intakeStep > s.step ? "bg-emerald-500/20 text-emerald-300" : "bg-white/10"
                        }`}>
                          {s.step}
                        </span>
                        <span>{s.label}</span>
                      </div>
                    ))}
                  </div>

                  {/* Wizard Step 1 */}
                  {intakeStep === 1 && (
                    <div className="p-6 rounded-xl glass-panel space-y-4">
                      <h2 className="text-sm font-bold text-slate-200">Step 1: System Purpose & Boundaries</h2>
                      <div className="space-y-3 text-xs">
                        <div>
                          <label className="block text-slate-300 mb-1 font-semibold">AI System Name</label>
                          <input
                            type="text"
                            value={intakeForm.system_name}
                            onChange={e => setIntakeForm({ ...intakeForm, system_name: e.target.value })}
                            className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-slate-100 focus:border-sky-400 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-slate-300 mb-1 font-semibold">Business Purpose & Context of Use</label>
                          <textarea
                            rows={3}
                            value={intakeForm.business_purpose}
                            onChange={e => setIntakeForm({ ...intakeForm, business_purpose: e.target.value })}
                            className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-slate-100 focus:border-sky-400 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-slate-300 mb-1 font-semibold">Business Unit</label>
                          <input
                            type="text"
                            value={intakeForm.business_unit}
                            onChange={e => setIntakeForm({ ...intakeForm, business_unit: e.target.value })}
                            className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-slate-100 focus:border-sky-400 focus:outline-none"
                          />
                        </div>
                      </div>
                      <div className="pt-4 flex justify-end">
                        <button
                          onClick={() => setIntakeStep(2)}
                          className="px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold text-xs transition-all"
                        >
                          Continue to Step 2 →
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Wizard Step 2 */}
                  {intakeStep === 2 && (
                    <div className="p-6 rounded-xl glass-panel space-y-4">
                      <h2 className="text-sm font-bold text-slate-200">Step 2: Decision Making & Data Sensitivity</h2>
                      <div className="space-y-3 text-xs">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={intakeForm.makes_decisions_about_individuals}
                            onChange={e => setIntakeForm({ ...intakeForm, makes_decisions_about_individuals: e.target.checked })}
                            className="rounded border-white/20 text-sky-500 focus:ring-0"
                          />
                          <span className="font-semibold text-slate-200">Does this system make or influence decisions concerning natural persons?</span>
                        </label>

                        {intakeForm.makes_decisions_about_individuals && (
                          <div className="pl-6 space-y-2 border-l-2 border-sky-500/30">
                            <div className="text-slate-400 text-[11px]">Select critical Annex III decision domains:</div>
                            {["credit", "employment", "education", "insurance", "healthcare", "biometrics"].map(domain => (
                              <label key={domain} className="flex items-center gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={intakeForm.decision_domains.includes(domain)}
                                  onChange={e => {
                                    const next = e.target.checked
                                      ? [...intakeForm.decision_domains, domain]
                                      : intakeForm.decision_domains.filter(d => d !== domain);
                                    setIntakeForm({ ...intakeForm, decision_domains: next });
                                  }}
                                  className="rounded border-white/20 text-sky-500 focus:ring-0"
                                />
                                <span className="capitalize text-slate-300">{domain}</span>
                              </label>
                            ))}
                          </div>
                        )}

                        <label className="flex items-center gap-2 cursor-pointer pt-2">
                          <input
                            type="checkbox"
                            checked={intakeForm.processes_personal_data}
                            onChange={e => setIntakeForm({ ...intakeForm, processes_personal_data: e.target.checked })}
                            className="rounded border-white/20 text-sky-500 focus:ring-0"
                          />
                          <span className="font-semibold text-slate-200">Processes personal data of individuals (GDPR / India DPDPA scope)</span>
                        </label>

                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={intakeForm.interacts_directly_with_humans}
                            onChange={e => setIntakeForm({ ...intakeForm, interacts_directly_with_humans: e.target.checked })}
                            className="rounded border-white/20 text-sky-500 focus:ring-0"
                          />
                          <span className="font-semibold text-slate-200">Interacts directly with natural persons (Chatbot / Conversational Copilot)</span>
                        </label>
                      </div>

                      <div className="pt-4 flex justify-between">
                        <button
                          onClick={() => setIntakeStep(1)}
                          className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-xs transition-all"
                        >
                          ← Back
                        </button>
                        <button
                          onClick={() => setIntakeStep(3)}
                          className="px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold text-xs transition-all"
                        >
                          Continue to Step 3 →
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Wizard Step 3 */}
                  {intakeStep === 3 && (
                    <div className="p-6 rounded-xl glass-panel space-y-4">
                      <h2 className="text-sm font-bold text-slate-200">Step 3: Technology, GenAI & Agent Autonomy</h2>
                      <div className="space-y-3 text-xs">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={intakeForm.is_generative_ai}
                            onChange={e => setIntakeForm({ ...intakeForm, is_generative_ai: e.target.checked })}
                            className="rounded border-white/20 text-sky-500 focus:ring-0"
                          />
                          <span className="font-semibold text-slate-200">Uses Generative AI / Large Language Models (LLM)</span>
                        </label>

                        {intakeForm.is_generative_ai && (
                          <div className="pl-6 space-y-2 border-l-2 border-purple-500/30">
                            <div>
                              <label className="block text-slate-400 text-[11px] mb-1">Foundation Model Provider</label>
                              <select
                                value={intakeForm.foundation_model_provider}
                                onChange={e => setIntakeForm({ ...intakeForm, foundation_model_provider: e.target.value })}
                                className="px-3 py-1.5 rounded bg-black/40 border border-white/10 text-slate-100"
                              >
                                <option value="Anthropic">Anthropic (Claude 3.5)</option>
                                <option value="OpenAI">OpenAI (GPT-4o)</option>
                                <option value="AWS Bedrock">AWS Bedrock</option>
                                <option value="Google Cloud">Google Cloud (Gemini)</option>
                                <option value="Self-Hosted">Self-Hosted Open Source</option>
                              </select>
                            </div>
                          </div>
                        )}

                        <label className="flex items-center gap-2 cursor-pointer pt-2">
                          <input
                            type="checkbox"
                            checked={intakeForm.is_autonomous_agent}
                            onChange={e => setIntakeForm({ ...intakeForm, is_autonomous_agent: e.target.checked })}
                            className="rounded border-white/20 text-sky-500 focus:ring-0"
                          />
                          <span className="font-semibold text-slate-200">Autonomous Agent with tool-calling capabilities</span>
                        </label>

                        {intakeForm.is_autonomous_agent && (
                          <div className="pl-6 space-y-2 border-l-2 border-amber-500/30">
                            <label className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={intakeForm.can_execute_code}
                                onChange={e => setIntakeForm({ ...intakeForm, can_execute_code: e.target.checked })}
                              />
                              <span className="text-slate-300">Agent can dynamically execute code (Python, Shell)</span>
                            </label>
                            <label className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={intakeForm.can_access_database}
                                onChange={e => setIntakeForm({ ...intakeForm, can_access_database: e.target.checked })}
                              />
                              <span className="text-slate-300">Agent can read or modify production database records</span>
                            </label>
                          </div>
                        )}
                      </div>

                      <div className="pt-4 flex justify-between">
                        <button
                          onClick={() => setIntakeStep(2)}
                          className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-xs transition-all"
                        >
                          ← Back
                        </button>
                        <button
                          onClick={runIntakeEvaluation}
                          disabled={evaluatingIntake}
                          className="px-5 py-2 rounded-lg bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-slate-950 font-bold text-xs flex items-center gap-2 shadow-lg shadow-sky-500/25 transition-all"
                        >
                          {evaluatingIntake ? <RefreshCw className="w-4 h-4 animate-spin" /> : <SparklesIcon className="w-4 h-4" />}
                          <span>Execute Regulatory Classification Engine</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Wizard Step 4: Results */}
                  {intakeStep === 4 && intakeResult && (
                    <div className="p-6 rounded-xl glass-panel space-y-5 animate-fadeIn">
                      <div className="flex items-center justify-between pb-3 border-b border-white/10">
                        <div>
                          <div className="text-[10px] text-slate-400 uppercase tracking-wider">Evaluation Complete</div>
                          <h2 className="text-base font-bold text-white">{intakeResult.system_name}</h2>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                          intakeResult.risk_level.includes("High")
                            ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                            : intakeResult.risk_level.includes("Transparency")
                            ? "bg-purple-500/20 text-purple-300 border-purple-500/40"
                            : "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                        }`}>
                          {intakeResult.risk_level}
                        </span>
                      </div>

                      <div className="space-y-4 text-xs">
                        <div className="p-3.5 rounded-lg bg-black/40 border border-white/10">
                          <div className="font-bold text-sky-400 mb-1 flex items-center gap-1.5">
                            <Shield className="w-3.5 h-3.5" /> EU AI Act Classification Reasoning
                          </div>
                          <p className="text-slate-300 leading-relaxed">{intakeResult.eu_ai_act_rationale}</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                            <div className="font-semibold text-slate-200 mb-1">Recommended Frameworks</div>
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              {intakeResult.recommended_frameworks.map((fw: string) => (
                                <span key={fw} className="text-[10px] bg-sky-500/15 text-sky-300 px-2 py-0.5 rounded border border-sky-500/20 font-mono">
                                  {fw}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                            <div className="font-semibold text-slate-200 mb-1">Mandatory Unified Controls</div>
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              {intakeResult.required_unified_controls.map((ctrl: string) => (
                                <span key={ctrl} className="text-[10px] bg-indigo-500/15 text-indigo-300 px-2 py-0.5 rounded border border-indigo-500/20 font-mono">
                                  {ctrl}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>

                        <div className="text-[11px] text-amber-300/80 italic p-2.5 rounded bg-amber-500/5 border border-amber-500/15">
                          {intakeResult.disclaimer}
                        </div>
                      </div>

                      <div className="pt-4 flex justify-between">
                        <button
                          onClick={() => setIntakeStep(3)}
                          className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-xs"
                        >
                          ← Re-adjust Inputs
                        </button>
                        <button
                          onClick={registerIntakeSystem}
                          className="px-5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-emerald-500/20 transition-all"
                        >
                          <Check className="w-4 h-4" />
                          <span>Commit to AI Inventory Registry</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB 4: UNIFIED CONTROLS LIBRARY                             */}
              {/* ============================================================ */}
              {activeTab === "controls" && (
                <div className="space-y-4 animate-fadeIn">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <h1 className="text-lg font-bold text-white flex items-center gap-2">
                        <Layers className="w-5 h-5 text-sky-400" />
                        Unified Control Library & Implementation State
                      </h1>
                      <p className="text-xs text-slate-400">
                        Normalized controls mapped across 17 standards. One control satisfies requirements in EU AI Act, NIST AI RMF, CRA, OWASP, and NIS2.
                      </p>
                    </div>

                    {/* Domain Filter */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">Domain:</span>
                      <select
                        value={controlDomainFilter}
                        onChange={e => setControlDomainFilter(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-slate-200 focus:outline-none"
                      >
                        <option value="All">All Domains</option>
                        <option value="AI Governance">AI Governance</option>
                        <option value="Prompt Security">Prompt Security</option>
                        <option value="Agent Security">Agent Security</option>
                        <option value="Human Oversight">Human Oversight</option>
                        <option value="Privacy">Privacy</option>
                        <option value="Supply Chain Security">Supply Chain Security</option>
                      </select>
                    </div>
                  </div>

                  <div className="rounded-xl glass-panel overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/80 border-b border-white/10 text-slate-400 font-semibold">
                        <tr>
                          <th className="p-3.5">Control ID & Title</th>
                          <th className="p-3.5">Domain</th>
                          <th className="p-3.5">Type & Frequency</th>
                          <th className="p-3.5">Status</th>
                          <th className="p-3.5">Effectiveness</th>
                          <th className="p-3.5 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {controls
                          .filter(c => controlDomainFilter === "All" || c.domain === controlDomainFilter)
                          .map(ctrl => (
                            <tr key={ctrl.id} className="hover:bg-white/[0.02] transition-colors">
                              <td className="p-3.5">
                                <button onClick={() => setSelectedControl(ctrl)}
                                  className="font-mono text-sky-400 text-[11px] hover:text-sky-300 hover:underline">{ctrl.code}</button>
                                <div className="font-semibold text-slate-100">{ctrl.title}</div>
                              </td>
                              <td className="p-3.5 text-slate-300">{ctrl.domain}</td>
                              <td className="p-3.5 text-[11px] text-slate-400">
                                {ctrl.control_type} • {ctrl.control_frequency}
                              </td>
                              <td className="p-3.5">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                  ctrl.customer_status === "Implemented"
                                    ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                                    : ctrl.customer_status === "Tested"
                                    ? "bg-sky-500/10 text-sky-300 border-sky-500/20"
                                    : "bg-amber-500/10 text-amber-300 border-amber-500/20"
                                }`}>
                                  {ctrl.customer_status}
                                </span>
                              </td>
                              <td className="p-3.5 text-slate-300">
                                {ctrl.customer_effectiveness}
                              </td>
                              <td className="p-3.5 text-right">
                                <button
                                  onClick={() => setSelectedControl(ctrl)}
                                  className="px-2.5 py-1 rounded bg-white/5 hover:bg-white/10 text-sky-400 text-[11px] border border-white/10"
                                >
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

              {/* ============================================================ */}
              {/* TAB 5: 17-FRAMEWORK CROSSWALK MATRIX                        */}
              {/* ============================================================ */}
              {activeTab === "crosswalk" && (
                <div className="space-y-4 animate-fadeIn">
                  <div>
                    <h1 className="text-lg font-bold text-white flex items-center gap-2">
                      <RefreshCw className="w-5 h-5 text-sky-400" />
                      17-Framework Compliance Crosswalk Matrix
                    </h1>
                    <p className="text-xs text-slate-400">
                      Authoritative cross-walk: One Unified Control mapped across EU AI Act, NIST AI RMF, CRA, OWASP, CSF, GDPR, DORA, NIS2, and Singapore AI Verify.
                    </p>
                  </div>

                  <div className="rounded-xl glass-panel overflow-x-auto">
                    <table className="w-full text-left text-xs min-w-[900px]">
                      <thead className="bg-slate-900/80 border-b border-white/10 text-slate-400 font-semibold">
                        <tr>
                          <th className="p-3.5 w-1/3">Unified Control</th>
                          <th className="p-3.5">Mapped Frameworks & Specific Articles</th>
                          <th className="p-3.5 w-1/4">Mapping Rationale</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {crosswalk.map(row => (
                          <tr key={row.control_id} className="hover:bg-white/[0.02]">
                            <td className="p-3.5 align-top">
                              <button onClick={() => goToControl(row.control_code)}
                                className="font-mono text-sky-400 text-[11px] font-bold hover:text-sky-300 hover:underline">
                                {row.control_code} ↗
                              </button>
                              <div className="font-semibold text-slate-100">{row.control_title}</div>
                              <div className="text-[10px] text-slate-400 mt-0.5">{row.domain}</div>
                            </td>
                            <td className="p-3.5 align-top space-y-1.5">
                              {row.mappings.map((m: any, idx: number) => (
                                <div key={idx} className="flex items-center gap-2 text-[11px]">
                                  <span className="font-semibold text-slate-200">{m.framework_name}:</span>
                                  <button
                                    onClick={() => goToFrameworkRequirement(m.framework_id, m.requirement_id, m.article)}
                                    title={`Open ${m.framework_name} ${m.article || m.requirement_id}${m.requirement_title ? " — " + m.requirement_title : ""}`}
                                    className="font-mono text-sky-300 bg-sky-500/10 px-1.5 py-0.5 rounded border border-sky-500/20 hover:border-sky-400 hover:text-sky-200 transition-colors"
                                  >
                                    {m.article || m.requirement_id} ↗
                                  </button>
                                  <span className={`text-[9px] px-1 rounded font-semibold ${
                                    m.confidence === "Exact" ? "text-emerald-400 bg-emerald-500/10" : "text-indigo-300 bg-indigo-500/10"
                                  }`}>
                                    {m.confidence}
                                  </span>
                                </div>
                              ))}
                            </td>
                            <td className="p-3.5 align-top text-[11px] text-slate-300 leading-relaxed">
                              {row.mappings[0]?.rationale || "Normalized mapping across security and governance baselines."}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB 6: AUTHORITATIVE FRAMEWORKS LIBRARY                     */}
              {/* ============================================================ */}
              {activeTab === "frameworks" && (
                <div className="space-y-4 animate-fadeIn">
                  <div>
                    <h1 className="text-lg font-bold text-white flex items-center gap-2">
                      <FileCheck className="w-5 h-5 text-sky-400" />
                      Authoritative Regulatory & Security Standards (17 Supported)
                    </h1>
                    <p className="text-xs text-slate-400">
                      Direct, legally usable/publicly accessible government and standard bodies. Zero invented requirements.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {frameworks.map(fw => (
                      <button
                        key={fw.id}
                        type="button"
                        onClick={() => { setOpenFramework(fw.id); setFrameworkHighlight(null); }}
                        className={`p-4 rounded-xl glass-panel glass-panel-hover flex flex-col justify-between text-left transition-colors ${
                          openFramework === fw.id ? "border-sky-500/50 ring-1 ring-sky-500/40" : "hover:border-sky-500/30"
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                            <span className="font-semibold text-sky-400">{fw.jurisdiction}</span>
                            <span>{fw.type}</span>
                          </div>
                          <h2 className="font-bold text-slate-100 text-sm">{fw.name}</h2>
                          <div className="text-[11px] font-mono text-slate-400 mt-1">{fw.official_reference}</div>
                          <p className="text-xs text-slate-400 mt-2 line-clamp-3 leading-relaxed">{fw.description}</p>
                        </div>

                        <div className="pt-4 mt-3 border-t border-white/5 flex items-center justify-between">
                          <div className="text-[11px] text-emerald-400 font-medium">
                            {(regFrameworks[regKeyFor(fw.id)]?.requirement_count ?? fw.requirement_count) || 0} requirements
                            {regFrameworks[regKeyFor(fw.id)] && (
                              <span className="text-slate-500 font-normal"> · {regFrameworks[regKeyFor(fw.id)].hierarchy_node_count} nodes</span>
                            )}
                          </div>
                          <span className="text-xs text-sky-400 flex items-center gap-1">
                            {openFramework === fw.id ? "Viewing" : "Browse requirements"} <ChevronRight className="w-3 h-3" />
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>

                  {Object.keys(regFrameworks).length > 0 && (
                    <div className="text-[11px] text-slate-500">
                      {Object.values(regFrameworks).reduce((n: number, f: any) => n + (f.requirement_count || 0), 0).toLocaleString()} source-traceable requirements ingested across {Object.values(regFrameworks).filter((f: any) => (f.requirement_count || 0) > 0).length} standards.
                      Counts on cards without a "nodes" figure are from the legacy catalog.
                    </div>
                  )}

                  {/* Framework requirement browser (opens on card click; also the
                      target of "EU AI Act: Article 9" style links from Crosswalk,
                      Controls, Evidence, Findings). */}
                  {openFramework && (
                    <div id="framework-detail" className="rounded-xl glass-panel p-5 space-y-4 border border-sky-500/20">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <h2 className="text-sm font-bold text-white">
                            {frameworkDetail?.name || frameworks.find((f: any) => f.id === openFramework)?.name || openFramework}
                          </h2>
                          {frameworkDetail && (
                            <div className="text-[11px] text-slate-400 mt-0.5 font-mono">
                              {frameworkDetail.official_reference} · {frameworkDetail.jurisdiction} · v{frameworkDetail.version}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {(frameworkDetail?.official_url || frameworks.find((f: any) => f.id === openFramework)?.official_url) && (
                            <a href={frameworkDetail?.official_url || frameworks.find((f: any) => f.id === openFramework)?.official_url}
                              target="_blank" rel="noopener noreferrer"
                              className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1">
                              Official source <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                          <button onClick={() => { setOpenFramework(null); setFrameworkHighlight(null); }}
                            className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
                        </div>
                      </div>

                      {frameworkDetailLoading && <div className="text-xs text-slate-500 flex items-center gap-2"><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Loading full requirement set…</div>}

                      {!frameworkDetailLoading && !frameworkDetail && (
                        <div className="text-xs text-slate-500">A structured requirement view is not available for this framework yet. Use the official source link above.</div>
                      )}

                      {frameworkDetail && (() => {
                        const q = frameworkReqFilter.trim().toLowerCase();
                        const allChapters = frameworkDetail.chapters || [];
                        const total = frameworkDetail.total_requirements ?? allChapters.reduce((n: number, c: any) => n + (c.requirements?.length || 0), 0);
                        const filtered = allChapters
                          .map((ch: any) => ({
                            ...ch,
                            requirements: (ch.requirements || []).filter((r: any) =>
                              !q ||
                              String(r.article || "").toLowerCase().includes(q) ||
                              String(r.title || "").toLowerCase().includes(q) ||
                              String(r.normalized_requirement || "").toLowerCase().includes(q) ||
                              String(r.source_text || "").toLowerCase().includes(q) ||
                              String(ch.chapter_id || "").toLowerCase().includes(q)
                            ),
                          }))
                          .filter((ch: any) => ch.requirements.length > 0);
                        const shown = filtered.reduce((n: number, c: any) => n + c.requirements.length, 0);
                        return (
                          <>
                            <div className="flex items-center gap-3 flex-wrap">
                              <input
                                value={frameworkReqFilter}
                                onChange={e => setFrameworkReqFilter(e.target.value)}
                                placeholder={`Search ${total} requirements (article, keyword, source text)…`}
                                className="flex-1 min-w-[220px] px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs text-slate-200 focus:outline-none focus:border-sky-500/50"
                              />
                              <span className="text-[11px] text-slate-500">
                                {q ? `${shown} of ${total}` : `${total}`} requirement{total === 1 ? "" : "s"}
                                {frameworkDetail._regulatory && <span className="text-emerald-400"> · source-traceable</span>}
                                {frameworkDetail.published_status && frameworkDetail.published_status !== "PUBLISHED" && (
                                  <span className="text-amber-400" title="Machine-extracted; pending human verification"> · {frameworkDetail.published_status}</span>
                                )}
                              </span>
                            </div>

                            {filtered.map((ch: any) => (
                        <div key={ch.chapter_id} className="space-y-2">
                          <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wide border-b border-white/5 pb-1 sticky top-0 bg-[#0d1117]/95 py-1 z-10">
                            {ch.chapter_id}{ch.title ? ` — ${ch.title}` : ""} <span className="text-slate-500 font-normal">({ch.requirements.length})</span>
                          </div>
                          {ch.requirements.map((r: any) => {
                            const systemsFor = aiSystems.filter((s: any) => (s.applicable_frameworks || []).includes(openFramework));
                            const mappedControls = crosswalk.filter((cw: any) => (cw.mappings || []).some((m: any) => m.requirement_id === r.id || m.article === r.article));
                            return (
                              <div key={r.id} id={`req-${r.id}`}
                                className="rounded-lg bg-black/30 border border-white/5 p-3 space-y-1.5 scroll-mt-28 transition-all">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="font-mono text-[11px] text-sky-300 bg-sky-500/10 px-1.5 py-0.5 rounded border border-sky-500/20">{r.article || r.id}</span>
                                  {r.title && r.title !== r.article && <span className="text-xs font-semibold text-slate-100">{r.title}</span>}
                                  {r.obligation_type && <span className="text-[9px] text-slate-400 bg-white/5 px-1 rounded border border-white/10">{String(r.obligation_type).replace(/_/g, " ").toLowerCase()}</span>}
                                  {r.mandatory === false && <span className="text-[9px] text-slate-400">recommended</span>}
                                </div>
                                {r.normalized_requirement && (
                                  <p className="text-[11px] text-slate-400 leading-relaxed">{r.normalized_requirement}</p>
                                )}
                                {r.source_text && r.source_text !== r.normalized_requirement && (
                                  <p className="text-[10px] text-slate-500 italic border-l-2 border-white/10 pl-2">“{r.source_text}”</p>
                                )}
                                <div className="flex items-center gap-3 flex-wrap pt-1 text-[10px]">
                                  {mappedControls.map((cw: any) => (
                                    <button key={cw.control_id} onClick={() => goToControl(cw.control_code)}
                                      className="font-mono text-indigo-300 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20 hover:border-indigo-400">
                                      {cw.control_code} ↗
                                    </button>
                                  ))}
                                  {systemsFor.length > 0 && (
                                    <button onClick={() => { setInventoryFilter("all"); setActiveTab("inventory"); }}
                                      className="text-slate-400 hover:text-sky-300">
                                      {systemsFor.length} affected system{systemsFor.length === 1 ? "" : "s"} ↗
                                    </button>
                                  )}
                                  {r.effective_from && <span className="text-slate-500">effective {r.effective_from}</span>}
                                  {r.source_anchor_url && (
                                    <a href={r.source_anchor_url} target="_blank" rel="noopener noreferrer" className="text-sky-400 hover:text-sky-300 inline-flex items-center gap-0.5">
                                      source <ExternalLink className="w-2.5 h-2.5" />
                                    </a>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                            ))}
                            {q && shown === 0 && <div className="text-[11px] text-slate-500">No requirements match “{frameworkReqFilter}”.</div>}
                          </>
                        );
                      })()}
                    </div>
                  )}
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB: ASSESSMENTS + APPROVAL WORKFLOW                        */}
              {/* ============================================================ */}
              {activeTab === "assessments" && (
                <div className="space-y-4 animate-fadeIn">
                  <div>
                    <h1 className="text-lg font-bold text-white flex items-center gap-2">
                      <FileCheck className="w-5 h-5 text-sky-400" /> Assessments
                    </h1>
                    <p className="text-xs text-slate-400">Evaluate an AI system against a framework's applicable requirements, then route it for approval.</p>
                  </div>

                  {/* Start a new assessment */}
                  <div className="p-4 rounded-xl glass-panel flex flex-wrap items-end gap-3">
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-400">AI System</label>
                      <select value={newAssessmentSystem} onChange={e => setNewAssessmentSystem(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-slate-200 min-w-[200px]">
                        <option value="">Select…</option>
                        {aiSystems.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-400">Framework</label>
                      <select value={newAssessmentFramework} onChange={e => setNewAssessmentFramework(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-slate-200 min-w-[200px]">
                        {frameworks.map((f: any) => <option key={f.id} value={f.id}>{f.name}</option>)}
                      </select>
                    </div>
                    <button onClick={createAssessmentFlow} disabled={assessmentBusy || !newAssessmentSystem}
                      className="px-4 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:opacity-40 text-slate-950 text-xs font-bold">
                      {assessmentBusy ? "Working…" : "Start assessment"}
                    </button>
                  </div>

                  <div className="rounded-xl glass-panel overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/80 border-b border-white/10 text-slate-400 font-semibold">
                        <tr>
                          <th className="p-3.5">Assessment</th>
                          <th className="p-3.5">Framework</th>
                          <th className="p-3.5">Readiness</th>
                          <th className="p-3.5">Approval</th>
                          <th className="p-3.5 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {assessmentsList.map((a: any) => (
                          <tr key={a.id} className="hover:bg-white/[0.02]">
                            <td className="p-3.5">
                              <div className="font-semibold text-slate-100">{a.title}</div>
                              <div className="text-[10px] text-slate-400">{a.system_name || a.system_id}</div>
                            </td>
                            <td className="p-3.5 text-slate-300">{a.framework_id}</td>
                            <td className="p-3.5 font-semibold text-sky-300">{Math.round(a.readiness_percentage || 0)}%</td>
                            <td className="p-3.5">
                              <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                                a.approval_status === "APPROVED" ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                                : a.approval_status === "SUBMITTED" ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
                                : a.approval_status === "REJECTED" ? "bg-rose-500/10 text-rose-300 border-rose-500/30"
                                : "bg-white/5 text-slate-400 border-white/10"}`}>
                                {(a.approval_status || "NOT_SUBMITTED").replace(/_/g, " ").toLowerCase()}
                              </span>
                            </td>
                            <td className="p-3.5 text-right">
                              <button onClick={() => openAssessmentDetail(a.id)}
                                className="px-2.5 py-1 rounded bg-white/5 hover:bg-white/10 text-sky-400 text-[11px] border border-white/10">Open</button>
                            </td>
                          </tr>
                        ))}
                        {assessmentsList.length === 0 && (
                          <tr><td colSpan={5} className="p-6 text-center text-xs text-slate-500">
                            No assessments yet. Start one above, or use "Start assessment" from an AI system's next action.
                          </td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB 7: EVIDENCE VAULT                                       */}
              {/* ============================================================ */}
              {activeTab === "evidence" && (
                <div className="space-y-4 animate-fadeIn">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <h1 className="text-lg font-bold text-white flex items-center gap-2">
                        <Lock className="w-5 h-5 text-sky-400" />
                        Evidence Vault & Multi-Framework Satisfaction
                      </h1>
                      <p className="text-xs text-slate-400">
                        Core Moat: Upload an evidence artifact once; AegisAI satisfies multiple controls and all mapped frameworks with cryptographic SHA-256 integrity.
                      </p>
                    </div>
                    <button
                      onClick={() => setEvidenceModalOpen(true)}
                      className="px-3.5 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-xs flex items-center gap-1.5 transition-all shadow-md shadow-emerald-500/20"
                    >
                      <Lock className="w-3.5 h-3.5" /> Upload Evidence Artifact
                    </button>
                  </div>

                  <div className="rounded-xl glass-panel overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/80 border-b border-white/10 text-slate-400 font-semibold">
                        <tr>
                          <th className="p-3.5">Artifact Title & Type</th>
                          <th className="p-3.5">Cryptographic SHA-256 Hash</th>
                          <th className="p-3.5">Satisfied Unified Controls</th>
                          <th className="p-3.5">Multi-Framework Impact</th>
                          <th className="p-3.5">Approval</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {evidenceList.map(ev => (
                          <tr key={ev.id} className="hover:bg-white/[0.02]">
                            <td className="p-3.5">
                              <div className="font-semibold text-slate-100">{ev.title}</div>
                              <div className="text-[11px] text-slate-400">{ev.evidence_type} • Owner: {ev.owner}</div>
                            </td>
                            <td className="p-3.5 font-mono text-[10px] text-slate-400 max-w-xs truncate">
                              {ev.file_hash_sha256}
                            </td>
                            <td className="p-3.5">
                              <div className="flex flex-wrap gap-1">
                                {ev.satisfied_controls.map((cid: string) => (
                                  <button key={cid} onClick={() => goToControl(cid)}
                                    className="text-[10px] font-mono bg-indigo-500/15 text-indigo-300 px-1.5 py-0.5 rounded border border-indigo-500/20 hover:border-indigo-400 transition-colors">
                                    {cid} ↗
                                  </button>
                                ))}
                              </div>
                            </td>
                            <td className="p-3.5">
                              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px] font-bold">
                                Satisfies {ev.satisfied_frameworks_count} Frameworks
                              </span>
                            </td>
                            <td className="p-3.5">
                              <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-semibold">
                                <Check className="w-2.5 h-2.5" /> Approved
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB 8: AI SECURITY & AGENT GOVERNANCE                       */}
              {/* ============================================================ */}
              {activeTab === "security" && (
                <div className="space-y-6 animate-fadeIn">
                  <div>
                    <h1 className="text-lg font-bold text-white flex items-center gap-2">
                      <Terminal className="w-5 h-5 text-sky-400" />
                      AI Security Center & Agent Permission Graph
                    </h1>
                    <p className="text-xs text-slate-400">
                      Autonomous agent tool boundaries, OWASP Agentic AI guidance, and instant hardware/software kill-switches.
                    </p>
                  </div>

                  {/* Agent Permission Graph & Kill-Switch Grid */}
                  <div className="p-5 rounded-xl glass-panel space-y-4">
                    <h2 className="text-sm font-bold text-slate-200 flex items-center justify-between">
                      <span>Registered Autonomous Agents</span>
                      <span className="text-xs text-slate-400 font-normal">OWASP Agentic AI Monitored</span>
                    </h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {agents.map(ag => (
                        <div key={ag.id} className="p-4 rounded-xl bg-black/40 border border-white/10 space-y-3">
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="font-bold text-slate-100 text-sm">{ag.name}</div>
                              <div className="text-[11px] text-slate-400">{ag.autonomy_level}</div>
                            </div>
                            <button
                              onClick={() => handleKillSwitch(ag.id)}
                              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                                ag.kill_switch_active
                                  ? "bg-rose-500 hover:bg-rose-400 text-white shadow-lg shadow-rose-500/30"
                                  : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-rose-500 hover:text-white"
                              }`}
                            >
                              {ag.kill_switch_active ? "HALTED (Kill-Switch Active)" : "Trigger Kill-Switch"}
                            </button>
                          </div>

                          <div className="space-y-1.5 text-xs">
                            <div className="text-[11px] text-slate-400 font-semibold">Authorized Tools & Scope:</div>
                            <div className="flex flex-wrap gap-1">
                              {ag.tools.map((t: string) => (
                                <span key={t} className="text-[10px] font-mono bg-white/5 text-slate-300 px-2 py-0.5 rounded border border-white/10">
                                  {t}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px]">
                            <span className="text-slate-400">Human Approval Gate:</span>
                            <span className="font-semibold text-emerald-400">Required for Code/DB</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Third-Party Model Vendor Table */}
                  <div className="p-5 rounded-xl glass-panel space-y-3">
                    <h2 className="text-sm font-bold text-slate-200">Third-Party AI Foundation Model Vendors</h2>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-900/60 border-b border-white/10 text-slate-400 font-semibold">
                          <tr>
                            <th className="p-3">Vendor Name</th>
                            <th className="p-3">Service Type</th>
                            <th className="p-3">Customer Data Training</th>
                            <th className="p-3">Certifications</th>
                            <th className="p-3">Risk Rating</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {vendors.map(v => (
                            <tr key={v.id}>
                              <td className="p-3 font-semibold text-slate-200">{v.name}</td>
                              <td className="p-3 text-slate-300">{v.service_type}</td>
                              <td className="p-3">
                                <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded text-[10px] font-semibold border border-emerald-500/20">
                                  Zero Training (Opt-Out Verified)
                                </span>
                              </td>
                              <td className="p-3 text-slate-400 text-[11px]">{v.certifications.join(", ")}</td>
                              <td className="p-3">
                                <span className="text-emerald-400 font-semibold">{v.risk_rating}</span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* ============================================================ */}
              {/* MODEL REGISTRY                                              */}
              {/* ============================================================ */}
              {activeTab === "model-registry" && (
                <div className="space-y-6 animate-fadeIn">
                  <div className="flex items-center justify-between">
                    <div>
                      <h1 className="text-lg font-bold text-white flex items-center gap-2">
                        <Cpu className="w-5 h-5 text-sky-400" />
                        Model Registry
                      </h1>
                      <p className="text-xs text-slate-400">
                        Tenant-wide model catalog. A model can be used by more than one AI System - see "Dependents" for the real Model → AI Systems graph.
                      </p>
                    </div>
                    <button
                      onClick={() => setRegistryModalOpen("model")}
                      className="px-3 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold"
                    >
                      + Register Model
                    </button>
                  </div>

                  <div className="p-5 rounded-xl glass-panel">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-900/60 border-b border-white/10 text-slate-400 font-semibold">
                          <tr>
                            <th className="p-3">Model</th>
                            <th className="p-3">Provider</th>
                            <th className="p-3">Version</th>
                            <th className="p-3">Type</th>
                            <th className="p-3">Status</th>
                            <th className="p-3">Foundation Model</th>
                            <th className="p-3"></th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {registryModels.length === 0 && (
                            <tr><td colSpan={7} className="p-6 text-center text-slate-500 italic">No models registered yet.</td></tr>
                          )}
                          {registryModels.map((m: any) => (
                            <tr key={m.id} id={`model-${m.id}`} className={`scroll-mt-24 transition-all ${modelFocusId === m.id ? "ring-2 ring-sky-400 bg-sky-500/5" : ""}`}>
                              <td className="p-3 font-semibold text-slate-200">{m.name}</td>
                              <td className="p-3 text-slate-300">{m.provider}</td>
                              <td className="p-3 text-slate-400">{m.version}</td>
                              <td className="p-3 text-slate-400">{m.model_type}</td>
                              <td className="p-3">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${m.status === "Active" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-slate-500/10 text-slate-400 border-slate-500/20"}`}>
                                  {m.status}
                                </span>
                              </td>
                              <td className="p-3 text-slate-400">{m.is_foundation_model ? "Yes" : "No"}</td>
                              <td className="p-3">
                                <button onClick={() => viewModelDependents(m.id)} className="text-sky-400 hover:text-sky-300 font-semibold">
                                  Dependents →
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {modelDependents && (
                    <div className="p-5 rounded-xl glass-panel space-y-3">
                      <div className="flex items-center justify-between">
                        <h2 className="text-sm font-bold text-slate-200">Dependency Graph: {modelDependents.model_name}</h2>
                        <button onClick={() => setModelDependents(null)} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                        <div>
                          <div className="text-slate-400 font-semibold mb-1.5">AI Systems ({modelDependents.dependent_systems.length}) · {modelDependents.high_risk_system_count} High-Risk</div>
                          {modelDependents.dependent_systems.map((s: any) => (
                            <div key={s.id} className="text-slate-300 py-0.5">• {s.name} <span className="text-slate-500">({s.role})</span></div>
                          ))}
                        </div>
                        <div>
                          <div className="text-slate-400 font-semibold mb-1.5">Agents Using This Model ({modelDependents.dependent_agents.length})</div>
                          {modelDependents.dependent_agents.map((a: any) => (
                            <div key={a.id} className="text-slate-300 py-0.5">• {a.name}</div>
                          ))}
                        </div>
                        <div>
                          <div className="text-slate-400 font-semibold mb-1.5">Vendor</div>
                          <div className="text-slate-300">{modelDependents.vendor ? modelDependents.vendor.name : "None linked"}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ============================================================ */}
              {/* AGENT REGISTRY                                              */}
              {/* ============================================================ */}
              {activeTab === "agent-registry" && (
                <div className="space-y-6 animate-fadeIn">
                  <div className="flex items-center justify-between">
                    <div>
                      <h1 className="text-lg font-bold text-white flex items-center gap-2">
                        <Terminal className="w-5 h-5 text-sky-400" />
                        Agent Registry &amp; Permission Graph
                      </h1>
                      <p className="text-xs text-slate-400">Explainable risk score computed from permission breadth, autonomy level, and approval-gate presence.</p>
                    </div>
                    <button
                      onClick={() => setRegistryModalOpen("agent")}
                      className="px-3 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold"
                    >
                      + Register Agent
                    </button>
                  </div>

                  {permissionGraph && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {[
                        { label: "Code Execution", n: permissionGraph.agents_with_code_execution.length },
                        { label: "GitHub Write", n: permissionGraph.agents_with_github_write.length },
                        { label: "PII Access", n: permissionGraph.agents_with_pii_access.length },
                        { label: "Financial Actions", n: permissionGraph.agents_with_financial_actions.length },
                        { label: "Can Invoke Agents", n: permissionGraph.agents_that_can_invoke_other_agents.length },
                        { label: "No Approval Gate", n: permissionGraph.agents_without_human_approval_gate.length },
                        { label: "No Kill-Switch", n: permissionGraph.agents_with_no_kill_switch.length },
                        { label: "Total Agents", n: permissionGraph.total_agents },
                      ].map(stat => (
                        <div key={stat.label} className="p-3 rounded-xl glass-panel text-center">
                          <div className="text-xl font-bold text-sky-400">{stat.n}</div>
                          <div className="text-[10px] text-slate-400 mt-0.5">{stat.label}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="p-5 rounded-xl glass-panel">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-900/60 border-b border-white/10 text-slate-400 font-semibold">
                          <tr>
                            <th className="p-3">Agent</th>
                            <th className="p-3">Autonomy</th>
                            <th className="p-3">Risk Score</th>
                            <th className="p-3">Approval Gate</th>
                            <th className="p-3">Permissions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {registryAgents.length === 0 && (
                            <tr><td colSpan={5} className="p-6 text-center text-slate-500 italic">No agents registered yet.</td></tr>
                          )}
                          {registryAgents.map((a: any) => (
                            <tr key={a.id} id={`agent-${a.id}`} className={`scroll-mt-24 transition-all ${agentFocusId === a.id ? "ring-2 ring-sky-400 bg-sky-500/5" : ""}`}>
                              <td className="p-3 font-semibold text-slate-200">{a.name}</td>
                              <td className="p-3 text-slate-400">{a.autonomy_level}</td>
                              <td className="p-3">
                                <span className={`font-bold ${a.risk_score >= 50 ? "text-rose-400" : a.risk_score >= 25 ? "text-amber-400" : "text-emerald-400"}`}>
                                  {a.risk_score}
                                </span>
                              </td>
                              <td className="p-3">
                                {a.human_approval_required
                                  ? <span className="text-emerald-400 text-[11px]">Required</span>
                                  : <span className="text-rose-400 text-[11px] font-semibold">None</span>}
                              </td>
                              <td className="p-3">
                                <div className="flex flex-wrap gap-1">
                                  {a.has_code_execution && <span className="text-[9px] px-1.5 py-0.5 bg-white/5 rounded border border-white/10">code-exec</span>}
                                  {a.has_git_write_access && <span className="text-[9px] px-1.5 py-0.5 bg-white/5 rounded border border-white/10">git-write</span>}
                                  {a.has_payment_access && <span className="text-[9px] px-1.5 py-0.5 bg-white/5 rounded border border-white/10">payments</span>}
                                  {a.accesses_pii && <span className="text-[9px] px-1.5 py-0.5 bg-white/5 rounded border border-white/10">pii</span>}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* ============================================================ */}
              {/* VENDOR REGISTRY                                             */}
              {/* ============================================================ */}
              {activeTab === "vendor-registry" && (
                <div className="space-y-6 animate-fadeIn">
                  <div className="flex items-center justify-between">
                    <div>
                      <h1 className="text-lg font-bold text-white flex items-center gap-2">
                        <Building className="w-5 h-5 text-sky-400" />
                        Vendor Registry
                      </h1>
                      <p className="text-xs text-slate-400">Third-party AI vendor risk with dependency propagation to affected AI Systems.</p>
                    </div>
                    <button
                      onClick={() => setRegistryModalOpen("vendor")}
                      className="px-3 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold"
                    >
                      + Register Vendor
                    </button>
                  </div>

                  <div className="p-5 rounded-xl glass-panel">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-900/60 border-b border-white/10 text-slate-400 font-semibold">
                          <tr>
                            <th className="p-3">Vendor</th>
                            <th className="p-3">Service Type</th>
                            <th className="p-3">Data Processing Role</th>
                            <th className="p-3">Risk Rating</th>
                            <th className="p-3"></th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {registryVendors.length === 0 && (
                            <tr><td colSpan={5} className="p-6 text-center text-slate-500 italic">No vendors registered yet.</td></tr>
                          )}
                          {registryVendors.map((v: any) => (
                            <tr key={v.id} id={`vendor-${v.id}`} className={`scroll-mt-24 transition-all ${vendorFocusId === v.id ? "ring-2 ring-sky-400 bg-sky-500/5" : ""}`}>
                              <td className="p-3 font-semibold text-slate-200">{v.name}</td>
                              <td className="p-3 text-slate-300">{v.service_type}</td>
                              <td className="p-3 text-slate-400">{v.data_processing_role || "—"}</td>
                              <td className="p-3">
                                <span className={`font-semibold ${v.risk_rating === "Critical" || v.risk_rating === "High" ? "text-rose-400" : v.risk_rating === "Medium" ? "text-amber-400" : "text-emerald-400"}`}>
                                  {v.risk_rating}
                                </span>
                              </td>
                              <td className="p-3">
                                <button onClick={() => viewVendorImpact(v.id)} className="text-sky-400 hover:text-sky-300 font-semibold">
                                  Impact →
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {vendorImpact && (
                    <div className="p-5 rounded-xl glass-panel space-y-3">
                      <div className="flex items-center justify-between">
                        <h2 className="text-sm font-bold text-slate-200">Impact: {vendorImpact.vendor_name}</h2>
                        <button onClick={() => setVendorImpact(null)} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                        <div className="p-3 rounded-lg bg-black/30 text-center">
                          <div className="text-xl font-bold text-sky-400">{vendorImpact.dependent_models.length}</div>
                          <div className="text-slate-400 text-[10px]">Models</div>
                        </div>
                        <div className="p-3 rounded-lg bg-black/30 text-center">
                          <div className="text-xl font-bold text-sky-400">{vendorImpact.dependent_systems_count}</div>
                          <div className="text-slate-400 text-[10px]">Dependent Systems</div>
                        </div>
                        <div className="p-3 rounded-lg bg-black/30 text-center">
                          <div className="text-xl font-bold text-rose-400">{vendorImpact.high_risk_systems_count}</div>
                          <div className="text-slate-400 text-[10px]">High-Risk Systems</div>
                        </div>
                      </div>
                      {vendorImpact.high_risk_systems.length > 0 && (
                        <div className="text-xs pt-2 border-t border-white/5">
                          <div className="text-slate-400 font-semibold mb-1">Affected High-Risk Systems:</div>
                          {vendorImpact.high_risk_systems.map((s: any) => <div key={s.id} className="text-slate-300 py-0.5">• {s.name}</div>)}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ============================================================ */}
              {/* GOVERNANCE GRAPH                                            */}
              {/* ============================================================ */}
              {activeTab === "governance-graph" && (
                <div className="space-y-6 animate-fadeIn">
                  <div>
                    <h1 className="text-lg font-bold text-white flex items-center gap-2">
                      <RefreshCw className="w-5 h-5 text-sky-400" />
                      Regulatory &amp; Asset Knowledge Graph
                    </h1>
                    <p className="text-xs text-slate-400">
                      Live graph traversal queries joining the 17-framework regulatory content with your registered AI Systems, Models, Agents, and Vendors.
                    </p>
                  </div>

                  {/* Requirement -> Affected Systems */}
                  <div className="p-5 rounded-xl glass-panel space-y-3">
                    <h2 className="text-sm font-bold text-slate-200">Which AI Systems are subject to a given requirement?</h2>
                    <div className="flex gap-2">
                      <input value={graphRequirementId} onChange={e => setGraphRequirementId(e.target.value)}
                        placeholder="e.g. EU-AIA-ART-09" className="flex-1 px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs" />
                      <button onClick={runRequirementQuery} className="px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs">Query</button>
                    </div>
                    {graphRequirementResult && (
                      <div className="text-xs text-slate-300 space-y-1 pt-2 border-t border-white/5">
                        <div><span className="text-slate-400">Framework:</span> {graphRequirementResult.framework_name} — <span className="text-slate-400">Requirement:</span> {graphRequirementResult.requirement_title}</div>
                        <div className="font-semibold">{graphRequirementResult.affected_systems_count} affected system(s):</div>
                        {graphRequirementResult.affected_systems.map((s: any) => <div key={s.id}>• {s.name} <span className="text-slate-500">({s.risk_classification})</span></div>)}
                      </div>
                    )}
                  </div>

                  {/* Controls satisfying multiple frameworks */}
                  <div className="p-5 rounded-xl glass-panel space-y-3">
                    <h2 className="text-sm font-bold text-slate-200">Which controls satisfy requirements across multiple frameworks?</h2>
                    <div className="flex gap-2">
                      <input value={graphFrameworksInput} onChange={e => setGraphFrameworksInput(e.target.value)}
                        placeholder="comma-separated framework ids" className="flex-1 px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs" />
                      <button onClick={runControlsQuery} className="px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs">Query</button>
                    </div>
                    {graphControlsResult && (
                      <div className="text-xs text-slate-300 space-y-1 pt-2 border-t border-white/5">
                        {graphControlsResult.length === 0 && <div className="italic text-slate-500">No single control covers all requested frameworks.</div>}
                        {graphControlsResult.map((c: any) => (
                          <div key={c.control_id}>• <span className="font-semibold">{c.control_code}</span> — {c.control_title}</div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Agent tool dependents */}
                  <div className="p-5 rounded-xl glass-panel space-y-3">
                    <h2 className="text-sm font-bold text-slate-200">Which agents depend on a given tool? (e.g. incident response after a supply-chain advisory)</h2>
                    <div className="flex gap-2">
                      <input value={graphToolInput} onChange={e => setGraphToolInput(e.target.value)}
                        placeholder="tool name, e.g. jira_api_client" className="flex-1 px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs" />
                      <button onClick={runToolQuery} className="px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs">Query</button>
                    </div>
                    {graphToolResult && (
                      <div className="text-xs text-slate-300 space-y-1 pt-2 border-t border-white/5">
                        <div className="font-semibold">{graphToolResult.dependent_agents_count} agent(s) depend on "{graphToolResult.tool}":</div>
                        {graphToolResult.dependent_agents.map((a: any) => <div key={a.id}>• {a.name} <span className="text-slate-500">(risk {a.risk_score})</span></div>)}
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl glass-panel space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-bold text-slate-200">Vendor Regulatory Exposure</h3>
                        <button onClick={loadVendorExposure} className="text-[10px] text-sky-400 hover:text-sky-300 font-semibold">Load</button>
                      </div>
                      {graphVendorExposureResult?.map((v: any) => (
                        <div key={v.vendor_id} className="text-[11px] text-slate-300 flex justify-between"><span>{v.vendor_name}</span><span className="text-sky-400 font-semibold">{v.regulatory_requirement_exposure}</span></div>
                      ))}
                    </div>
                    <div className="p-4 rounded-xl glass-panel space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-bold text-slate-200">Shared High-Risk Models</h3>
                        <button onClick={loadSharedModels} className="text-[10px] text-sky-400 hover:text-sky-300 font-semibold">Load</button>
                      </div>
                      {graphSharedModelsResult?.map((m: any) => (
                        <div key={m.model_id} className="text-[11px] text-slate-300 flex justify-between"><span>{m.model_name}</span><span className="text-rose-400 font-semibold">{m.high_risk_systems_count} systems</span></div>
                      ))}
                      {graphSharedModelsResult?.length === 0 && <div className="text-[11px] text-slate-500 italic">None found.</div>}
                    </div>
                    <div className="p-4 rounded-xl glass-panel space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-bold text-slate-200">Highest-Coverage Evidence</h3>
                        <button onClick={loadEvidenceCoverage} className="text-[10px] text-sky-400 hover:text-sky-300 font-semibold">Load</button>
                      </div>
                      {graphEvidenceResult?.slice(0, 5).map((e: any) => (
                        <div key={e.evidence_id} className="text-[11px] text-slate-300 flex justify-between"><span className="truncate">{e.title}</span><span className="text-sky-400 font-semibold">{e.satisfied_requirements_count}</span></div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB 9: RISK REGISTER & REMEDIATION                          */}
              {/* ============================================================ */}
              {activeTab === "risks" && (
                <div className="space-y-6 animate-fadeIn">
                  <div>
                    <h1 className="text-lg font-bold text-white flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-amber-400" />
                      AI Risk Register & Remediation Tasks
                    </h1>
                    <p className="text-xs text-slate-400">
                      Inherent vs residual risk scoring mapped to MITRE ATLAS techniques, OWASP GenAI risks, and SLA tracking.
                    </p>
                  </div>

                  {/* Risks Table */}
                  <div className="rounded-xl glass-panel overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/80 border-b border-white/10 text-slate-400 font-semibold">
                        <tr>
                          <th className="p-3.5">Risk Code & Title</th>
                          <th className="p-3.5">Category</th>
                          <th className="p-3.5">Threat Mapping</th>
                          <th className="p-3.5">Inherent / Residual Score</th>
                          <th className="p-3.5">Status</th>
                          <th className="p-3.5">Owner</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {risks.map(r => (
                          <tr key={r.id} className="hover:bg-white/[0.02]">
                            <td className="p-3.5">
                              <div className="font-mono text-amber-400 text-[11px] font-bold">{r.risk_code}</div>
                              <div className="font-semibold text-slate-100">{r.title}</div>
                              {r.system_id && (
                                <button onClick={() => goToSystem(r.system_id)} className="text-[10px] text-sky-300 hover:text-sky-200 hover:underline mt-0.5">
                                  {aiSystems.find((s: any) => s.id === r.system_id)?.name || "affected system"} ↗
                                </button>
                              )}
                            </td>
                            <td className="p-3.5 text-slate-300">{r.category}</td>
                            <td className="p-3.5">
                              {r.mitre_atlas_technique ? (
                                <a href={`https://atlas.mitre.org/techniques/${String(r.mitre_atlas_technique).replace(/[^A-Za-z0-9.]/g, "")}`}
                                  target="_blank" rel="noopener noreferrer"
                                  className="text-[11px] text-sky-300 font-mono hover:text-sky-200 hover:underline inline-flex items-center gap-0.5">
                                  {r.mitre_atlas_technique} <ExternalLink className="w-2.5 h-2.5" />
                                </a>
                              ) : <span className="text-[11px] text-slate-500 font-mono">ATLAS</span>}
                              <div className="text-[10px] text-slate-400">{r.owasp_category}</div>
                            </td>
                            <td className="p-3.5 font-semibold">
                              <span className="text-rose-400">{r.inherent_score}</span>
                              <span className="text-slate-500 mx-1">→</span>
                              <span className="text-emerald-400">{r.residual_score}</span>
                            </td>
                            <td className="p-3.5">
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20">
                                {r.status}
                              </span>
                            </td>
                            <td className="p-3.5 text-slate-300">{r.owner}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Findings */}
                  <div className="p-5 rounded-xl glass-panel space-y-3">
                    <div className="flex items-center justify-between">
                      <h2 className="text-sm font-bold text-slate-200">Findings <span className="text-slate-500 font-normal">· {findings.length}</span></h2>
                      <button
                        onClick={() => setNewFindingOpen(v => !v)}
                        className="px-3 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold text-[11px]"
                      >
                        {newFindingOpen ? "Cancel" : "+ New Finding"}
                      </button>
                    </div>

                    {newFindingOpen && (
                      <div className="p-3 rounded-lg bg-black/40 border border-white/10 space-y-2">
                        <input
                          placeholder="Finding title *"
                          value={newFindingForm.title}
                          onChange={e => setNewFindingForm(f => ({ ...f, title: e.target.value }))}
                          className="w-full px-2.5 py-1.5 rounded bg-white/5 border border-white/10 text-[11px] text-slate-200"
                        />
                        <textarea
                          placeholder="Description"
                          value={newFindingForm.description}
                          onChange={e => setNewFindingForm(f => ({ ...f, description: e.target.value }))}
                          className="w-full px-2.5 py-1.5 rounded bg-white/5 border border-white/10 text-[11px] text-slate-200 h-14"
                        />
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          <select value={newFindingForm.severity} onChange={e => setNewFindingForm(f => ({ ...f, severity: e.target.value }))}
                            className="px-2 py-1.5 rounded bg-white/5 border border-white/10 text-[11px] text-slate-200">
                            {["Critical", "High", "Medium", "Low"].map(s => <option key={s} value={s}>{s}</option>)}
                          </select>
                          <select value={newFindingForm.source} onChange={e => setNewFindingForm(f => ({ ...f, source: e.target.value }))}
                            className="px-2 py-1.5 rounded bg-white/5 border border-white/10 text-[11px] text-slate-200">
                            {["Manual Review", "Assessment", "Red Team", "Vendor Assessment", "Runtime Violation", "Regulatory Change"].map(s => <option key={s} value={s}>{s}</option>)}
                          </select>
                          <select value={newFindingForm.control_id} onChange={e => setNewFindingForm(f => ({ ...f, control_id: e.target.value }))}
                            className="px-2 py-1.5 rounded bg-white/5 border border-white/10 text-[11px] text-slate-200">
                            <option value="">(no control)</option>
                            {controls.map((c: any) => <option key={c.id || c.code} value={c.code || c.id}>{c.code || c.id}</option>)}
                          </select>
                          <select value={newFindingForm.system_id} onChange={e => setNewFindingForm(f => ({ ...f, system_id: e.target.value }))}
                            className="px-2 py-1.5 rounded bg-white/5 border border-white/10 text-[11px] text-slate-200">
                            <option value="">(no system)</option>
                            {aiSystems.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
                          </select>
                        </div>
                        <button onClick={submitNewFinding} disabled={findingBusy || !newFindingForm.title.trim()}
                          className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-slate-950 font-semibold text-[11px]">
                          {findingBusy ? "Creating…" : "Create finding"}
                        </button>
                      </div>
                    )}

                    {findings.length === 0 && !newFindingOpen && (
                      <p className="text-[11px] text-slate-500">No findings yet. Findings are raised here manually, and automatically when a control fails a test or evidence is rejected.</p>
                    )}
                    <div className="space-y-1.5">
                      {findings.map((f: any) => (
                        <div key={f.id} className="p-2.5 rounded-lg bg-black/40 border border-white/10 flex items-center gap-3 text-[11px]">
                          <span className={`px-1.5 py-0.5 rounded border text-[9px] font-semibold ${
                            f.severity === "Critical" ? "bg-rose-500/10 text-rose-300 border-rose-500/30"
                            : f.severity === "High" ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
                            : "bg-sky-500/10 text-sky-300 border-sky-500/30"}`}>{f.severity}</span>
                          <div className="flex-1 min-w-0">
                            <div className={`font-semibold ${f.status === "Resolved" ? "line-through text-slate-500" : "text-slate-100"}`}>{f.title}</div>
                            <div className="text-[10px] text-slate-500 flex items-center gap-1 flex-wrap">
                              <span>{f.source}</span>
                              <span>·</span>
                              {f.control_id ? (
                                <button onClick={() => goToControl(f.control_id)} className="text-indigo-300 hover:text-indigo-200 hover:underline font-mono">{f.control_id} ↗</button>
                              ) : <span>no control</span>}
                              <span>·</span>
                              {f.system_id ? (
                                <button onClick={() => goToSystem(f.system_id)} className="text-sky-300 hover:text-sky-200 hover:underline">{f.system_name || "system"} ↗</button>
                              ) : <span>{f.system_name || "enterprise-wide"}</span>}
                              <span>·</span>
                              <span className="text-slate-400">{f.status}</span>
                              {f.due_date ? <span>· due {new Date(f.due_date).toLocaleDateString()}</span> : null}
                            </div>
                          </div>
                          {f.status !== "Resolved" && (
                            <>
                              <button onClick={() => addRemediationForFinding(f.id, f.title)}
                                className="px-2 py-1 rounded bg-sky-500/20 text-sky-300 hover:bg-sky-500 hover:text-slate-950 text-[10px] font-semibold">+ Remediation</button>
                              <button onClick={() => closeFinding(f.id)}
                                className="px-2 py-1 rounded bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500 hover:text-slate-950 text-[10px] font-semibold">Resolve</button>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Remediation Tasks with Toggle */}
                  <div className="p-5 rounded-xl glass-panel space-y-3">
                    <h2 className="text-sm font-bold text-slate-200">Remediation SLA Tasks</h2>
                    <div className="space-y-2">
                      {remediations.map(task => (
                        <div
                          key={task.id}
                          className="p-3 rounded-lg bg-black/40 border border-white/10 flex items-center justify-between text-xs"
                        >
                          <div>
                            <div className={`font-semibold ${task.status === "Done" ? "line-through text-slate-500" : "text-slate-100"}`}>
                              {task.title}
                            </div>
                            <div className="text-[11px] text-slate-400">Assigned to: {task.assigned_to} • Priority: {task.priority}</div>
                          </div>
                          <button
                            onClick={() => handleRemediationToggle(task.id, task.status)}
                            className={`px-3 py-1 rounded text-[11px] font-semibold transition-all ${
                              task.status === "Done"
                                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                : "bg-sky-500/20 text-sky-300 hover:bg-sky-500 hover:text-slate-950"
                            }`}
                          >
                            {task.status === "Done" ? "✓ Completed" : "Mark Done"}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB 10: EXECUTIVE REPORTS                                   */}
              {/* ============================================================ */}
              {activeTab === "reports" && (
                <div className="space-y-4 max-w-4xl mx-auto animate-fadeIn">
                  <div className="flex items-center justify-between">
                    <div>
                      <h1 className="text-lg font-bold text-white flex items-center gap-2">
                        <FileText className="w-5 h-5 text-sky-400" />
                        Executive Compliance & Audit Reports
                      </h1>
                      <p className="text-xs text-slate-400">
                        Export board-ready AI governance dossiers, EU AI Act conformity readiness reports, and NIST AI RMF gap analysis.
                      </p>
                    </div>
                    <button
                      onClick={async () => {
                        const rep = await api.getExecutiveReport();
                        const blob = new Blob([JSON.stringify(rep, null, 2)], { type: "application/json" });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = "AegisAI_Executive_Report_2026.json";
                        a.click();
                      }}
                      className="px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold text-xs flex items-center gap-1.5 shadow-md shadow-sky-500/20"
                    >
                      <Download className="w-3.5 h-3.5" /> Export Executive JSON / Report
                    </button>
                  </div>

                  <div className="p-6 rounded-2xl glass-panel space-y-4 font-mono text-xs">
                    <div className="border-b border-white/10 pb-3">
                      <div className="text-slate-400">AI-TRUST-COMPLIANCE-REPORT • {new Date().toISOString().slice(0, 10)}</div>
                      <div className="text-base font-bold text-white mt-1">
                        {(currentUser?.organization_name || "Your Organization").toUpperCase()} — AI GOVERNANCE BASELINE
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {aiSystems.length} AI system{aiSystems.length === 1 ? "" : "s"} governed • Multi-tenant isolated • Generated from live tenant data
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center py-2">
                      <div className="p-2.5 rounded bg-black/40 border border-white/5">
                        <div className="text-lg font-bold text-sky-400">{metrics?.overall_readiness_percentage}%</div>
                        <div className="text-[10px] text-slate-400">Overall Readiness</div>
                      </div>
                      <div className="p-2.5 rounded bg-black/40 border border-white/5">
                        <div className="text-lg font-bold text-emerald-400">{aiSystems.length}</div>
                        <div className="text-[10px] text-slate-400">Governed AI Systems</div>
                      </div>
                      <div className="p-2.5 rounded bg-black/40 border border-white/5">
                        <div className="text-lg font-bold text-purple-400">{controls.length}</div>
                        <div className="text-[10px] text-slate-400">Unified Controls</div>
                      </div>
                      <div className="p-2.5 rounded bg-black/40 border border-white/5">
                        <div className="text-lg font-bold text-amber-400">{evidenceList.length}</div>
                        <div className="text-[10px] text-slate-400">Evidence Artifacts</div>
                      </div>
                    </div>

                    <div className="text-slate-300 space-y-2 text-[11px] leading-relaxed">
                      {(() => {
                        const highRisk = aiSystems.filter((s: any) => String(s.risk_classification || "").includes("High"));
                        const agentic = aiSystems.filter((s: any) => s.is_agentic_ai);
                        const genai = aiSystems.filter((s: any) => s.is_generative_ai);
                        const pii = aiSystems.filter((s: any) => s.processes_personal_data);
                        const lines: string[] = [];
                        if (aiSystems.length === 0) {
                          lines.push("No AI systems registered yet. Register your AI systems to generate a substantive governance baseline.");
                        } else {
                          lines.push(`${highRisk.length} of ${aiSystems.length} registered system(s) are classified High-Risk${highRisk.length ? ` (${highRisk.slice(0, 3).map((s: any) => s.name).join(", ")})` : ""} and carry the full obligation set for their applicable frameworks.`);
                          if (genai.length) lines.push(`${genai.length} generative-AI system(s) in scope for the OWASP LLM Top 10 and NIST GenAI Profile.`);
                          if (agentic.length) lines.push(`${agentic.length} agentic system(s) in scope for OWASP Agentic and MITRE ATLAS — verify least-privilege tool permissions, human-approval gates and kill-switches in the Agents module.`);
                          if (pii.length) lines.push(`${pii.length} system(s) process personal data — GDPR / India DPDP obligations apply; confirm DPAs and DPIAs.`);
                          lines.push(`Overall readiness ${metrics?.overall_readiness_percentage ?? 0}% (implementation ${metrics?.implementation_score ?? 0}%, evidence ${metrics?.evidence_completeness_score ?? 0}%, effectiveness ${metrics?.control_effectiveness_score ?? 0}%). ${metrics?.open_findings_count ?? 0} open finding(s).`);
                        }
                        return lines.map((l, i) => <p key={i}>• {l}</p>);
                      })()}
                    </div>
                    <p className="text-[10px] text-slate-500 border-t border-white/10 pt-2">
                      This summary is generated from your live tenant data. Use "Export Executive JSON / Report" above for the full machine-readable report with per-system detail and source citations.
                    </p>
                  </div>
                </div>
              )}

              {/* ============================================================ */}
              {/* TAB 11: AUDIT TRAIL                                         */}
              {/* ============================================================ */}
              {activeTab === "audit" && (
                <div className="space-y-4 animate-fadeIn">
                  <div>
                    <h1 className="text-lg font-bold text-white flex items-center gap-2">
                      <Clock className="w-5 h-5 text-sky-400" />
                      Tamper-Evident Compliance Audit Trail
                    </h1>
                    <p className="text-xs text-slate-400">
                      Immutable log of all governance events: AI system creation, control updates, evidence uploads, and kill-switch activations.
                    </p>
                  </div>

                  <div className="rounded-xl glass-panel overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/80 border-b border-white/10 text-slate-400 font-semibold">
                        <tr>
                          <th className="p-3.5">Timestamp</th>
                          <th className="p-3.5">Actor</th>
                          <th className="p-3.5">Action</th>
                          <th className="p-3.5">Target Object</th>
                          <th className="p-3.5">Audit Changes</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 font-mono text-[11px]">
                        {auditEvents.map(ev => (
                          <tr key={ev.id} className="hover:bg-white/[0.02]">
                            <td className="p-3.5 text-slate-400">{new Date(ev.timestamp).toLocaleString()}</td>
                            <td className="p-3.5 text-sky-300">{ev.actor_email}</td>
                            <td className="p-3.5 font-bold text-emerald-400">{ev.action}</td>
                            <td className="p-3.5 text-slate-300">{ev.object_type}</td>
                            <td className="p-3.5 text-slate-400 max-w-sm truncate">{JSON.stringify(ev.changes)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      {/* ========================================================================= */}
      {/* 3. AI GOVERNANCE COPILOT SLIDE-OVER DRAWER                               */}
      {/* ========================================================================= */}
      {copilotOpen && (
        <div className="fixed inset-y-0 right-0 w-96 bg-[#0B0F1A] border-l border-white/10 shadow-2xl z-50 flex flex-col backdrop-blur-2xl animate-slideLeft">
          <div className="p-4 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded bg-sky-500/20 text-sky-400 flex items-center justify-center">
                <SparklesIcon className="w-4 h-4" />
              </div>
              <div>
                <div className="text-xs font-bold text-white">AI Governance Copilot</div>
                <div className="text-[10px] text-slate-400">Grounded in 17 Standards</div>
              </div>
            </div>
            <button
              onClick={() => setCopilotOpen(false)}
              className="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
            {copilotMessages.map((msg, i) => (
              <div
                key={i}
                className={`p-3 rounded-xl leading-relaxed ${
                  msg.sender === "user"
                    ? "bg-sky-500/20 text-sky-200 ml-6 border border-sky-500/30"
                    : "bg-white/5 text-slate-200 mr-4 border border-white/5"
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.text}</div>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-white/10 space-y-1">
                    <div className="text-[10px] font-bold text-sky-400 uppercase tracking-wider">Authoritative Citations:</div>
                    {msg.citations.map((c: any, idx: number) => (
                      <a
                        key={idx}
                        href={c.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-[10px] text-sky-300 hover:underline"
                      >
                        • {c.source} ({c.reference})
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {copilotLoading && (
              <div className="p-3 rounded-xl bg-white/5 text-slate-400 flex items-center gap-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-sky-400" />
                <span>Searching authoritative regulatory knowledge graph...</span>
              </div>
            )}
          </div>

          {/* Quick Prompts */}
          <div className="px-4 py-2 border-t border-white/5 space-y-1 bg-black/20">
            <div className="text-[10px] text-slate-400 font-semibold">Quick Prompts:</div>
            <div className="flex flex-wrap gap-1">
              {[
                "Which controls satisfy both NIST AI RMF and EU AI Act?",
                "Why does the EU AI Act apply?",
                "Which agents can execute code?",
                "Show critical findings"
              ].map((qp, idx) => (
                <button
                  key={idx}
                  onClick={() => setCopilotQuery(qp)}
                  className="text-[10px] bg-white/5 hover:bg-white/10 text-slate-300 px-2 py-0.5 rounded border border-white/10 truncate max-w-full"
                >
                  {qp}
                </button>
              ))}
            </div>
          </div>

          {/* Input Box */}
          <div className="p-3 border-t border-white/10 flex items-center gap-2">
            <input
              type="text"
              placeholder="Ask a compliance or security question..."
              value={copilotQuery}
              onChange={e => setCopilotQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleCopilotSend()}
              className="flex-1 px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-xs text-white focus:outline-none focus:border-sky-400"
            />
            <button
              onClick={handleCopilotSend}
              disabled={copilotLoading}
              className="p-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 4. MODAL: SYSTEM DETAILS                                                 */}
      {/* ========================================================================= */}
      {selectedSystem && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-2xl w-full rounded-2xl glass-panel p-6 space-y-4 border border-white/15 animate-scaleUp">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <span className="text-[10px] text-sky-400 font-bold uppercase tracking-wider">{selectedSystem.business_unit}</span>
                <h2 className="text-base font-bold text-white">{selectedSystem.name}</h2>
              </div>
              <button onClick={() => setSelectedSystem(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              {/* Governance workflow status bar (spec §41) */}
              {(() => {
                const wf = portfolioWorkflow.find((w: any) => w.system_id === selectedSystem.id);
                if (!wf) return null;
                const STEPS = ["Inventory", "Applicability", "Assessment", "Controls", "Evidence", "Testing", "Remediation", "Approval", "Report"];
                return (
                  <div className="p-3 rounded-lg bg-black/30 border border-white/5 space-y-2">
                    <div className="flex items-center flex-wrap gap-1">
                      {(wf.steps || []).map((s: any, i: number) => (
                        <React.Fragment key={s.key}>
                          <button
                            onClick={() => { setSelectedSystem(null); continueGovernance(selectedSystem.id); }}
                            title={s.label}
                            className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-semibold ${
                              s.state === "done" ? "bg-emerald-500/15 text-emerald-300"
                              : s.state === "active" ? "bg-sky-500/20 text-sky-200"
                              : "bg-white/5 text-slate-500"}`}
                          >
                            {s.state === "done" ? <Check className="w-2.5 h-2.5" /> : <span>{i + 1}</span>}
                            {s.label}
                          </button>
                          {i < STEPS.length - 1 && <span className="text-slate-700">·</span>}
                        </React.Fragment>
                      ))}
                    </div>
                    {wf.next_action && (
                      <button
                        onClick={() => { setSelectedSystem(null); continueGovernance(selectedSystem.id); }}
                        className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold transition-colors"
                      >
                        <span>Continue governance: {wf.next_action.label}</span>
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    )}
                    <p className="text-[10px] text-slate-500">{wf.next_action?.helper}</p>
                  </div>
                );
              })()}

              <p className="text-slate-300 leading-relaxed">{selectedSystem.description}</p>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                  <div className="text-[10px] text-slate-400 font-semibold">Technical Architecture</div>
                  <div className="font-bold text-slate-200 mt-0.5">{selectedSystem.model_provider} {selectedSystem.model_name}</div>
                  <div className="text-[11px] text-slate-400 mt-1">Hosting: {selectedSystem.cloud_provider} ({selectedSystem.deployment_environment})</div>
                </div>

                <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                  <div className="text-[10px] text-slate-400 font-semibold">Regulatory Classification</div>
                  <div className="font-bold text-rose-300 mt-0.5">{selectedSystem.risk_classification}</div>
                  <div className="text-[11px] text-slate-400 mt-1">{selectedSystem.eu_ai_act_classification}</div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-200">
                <span className="font-bold">Legal Reasoning: </span>
                <span>{selectedSystem.classification_reasoning}</span>
              </div>

              {/* Cross-links to the rest of this system's governance graph */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {(() => {
                  const m = registryModels.find((x: any) => x.name === selectedSystem.model_name || (x.provider === selectedSystem.model_provider && selectedSystem.model_name?.includes(x.name)));
                  return m ? (
                    <button onClick={() => { setSelectedSystem(null); goToModel(m.id); }} className="text-[10px] text-sky-300 bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20 hover:border-sky-400">Model: {m.name} ↗</button>
                  ) : null;
                })()}
                {(() => {
                  const v = registryVendors.find((x: any) => x.name?.toLowerCase() === String(selectedSystem.model_provider || "").toLowerCase());
                  return v ? (
                    <button onClick={() => { setSelectedSystem(null); goToVendor(v.id); }} className="text-[10px] text-fuchsia-300 bg-fuchsia-500/10 px-2 py-0.5 rounded border border-fuchsia-500/20 hover:border-fuchsia-400">Vendor: {v.name} ↗</button>
                  ) : null;
                })()}
                {registryAgents.filter((a: any) => a.system_id === selectedSystem.id).map((a: any) => (
                  <button key={a.id} onClick={() => { setSelectedSystem(null); goToAgent(a.id); }} className="text-[10px] text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20 hover:border-amber-400">Agent: {a.name} ↗</button>
                ))}
                {findings.filter((f: any) => f.system_id === selectedSystem.id).length > 0 && (
                  <button onClick={() => { setSelectedSystem(null); setActiveTab("risks"); }} className="text-[10px] text-rose-300 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20 hover:border-rose-400">
                    {findings.filter((f: any) => f.system_id === selectedSystem.id).length} finding(s) ↗
                  </button>
                )}
                {(selectedSystem.applicable_frameworks || []).map((fk: string) => (
                  <button key={fk} onClick={() => { setSelectedSystem(null); goToFrameworkRequirement(fk); }} className="text-[10px] text-slate-300 bg-white/5 px-2 py-0.5 rounded border border-white/10 hover:border-sky-400">
                    {(frameworks.find((f: any) => f.id === fk)?.short_name || fk)} ↗
                  </button>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-white/10 flex justify-end">
              <button
                onClick={() => setSelectedSystem(null)}
                className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-xs text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 5. MODAL: MANAGE CONTROL STATUS                                          */}
      {/* ========================================================================= */}
      {openAssessment && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setOpenAssessment(null)}>
          <div className="max-w-2xl w-full max-h-[85vh] overflow-y-auto rounded-2xl glass-panel p-6 space-y-4 border border-white/15" onClick={e => e.stopPropagation()}>
            <div className="flex items-start justify-between border-b border-white/10 pb-3">
              <div>
                <h2 className="text-sm font-bold text-white">{openAssessment.title}</h2>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  {openAssessment.system_name} · {openAssessment.framework_name || openAssessment.framework_id} · {openAssessment.responses?.length || 0} requirements
                </div>
              </div>
              <button onClick={() => setOpenAssessment(null)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>

            <div className="grid grid-cols-4 gap-2 text-center">
              {[["Readiness", openAssessment.readiness_percentage], ["Implemented", openAssessment.implementation_score], ["Evidence", openAssessment.evidence_score], ["Effective", openAssessment.effectiveness_score]].map(([l, v]: any) => (
                <div key={l} className="p-2 rounded-lg bg-black/30 border border-white/5">
                  <div className="text-base font-bold text-sky-300">{Math.round(v || 0)}%</div>
                  <div className="text-[9px] text-slate-400">{l}</div>
                </div>
              ))}
            </div>

            {/* Approval workflow */}
            <div className="p-3 rounded-lg bg-black/30 border border-white/5 space-y-2">
              <div className="flex items-center gap-2 text-[11px]">
                <span className="text-slate-400">Approval:</span>
                <span className={`px-2 py-0.5 rounded-full border ${
                  openAssessment.approval_status === "APPROVED" ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                  : openAssessment.approval_status === "SUBMITTED" ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
                  : openAssessment.approval_status === "REJECTED" ? "bg-rose-500/10 text-rose-300 border-rose-500/30"
                  : "bg-white/5 text-slate-400 border-white/10"}`}>
                  {(openAssessment.approval_status || "NOT_SUBMITTED").replace(/_/g, " ").toLowerCase()}
                </span>
                {openAssessment.submitted_by && <span className="text-slate-500">submitted by {openAssessment.submitted_by}</span>}
                {openAssessment.approved_by && <span className="text-slate-500">· by {openAssessment.approved_by}</span>}
              </div>
              <div className="flex gap-2">
                {(openAssessment.approval_status === "NOT_SUBMITTED" || openAssessment.approval_status === "REJECTED") && (
                  <button onClick={() => assessmentApprovalAction(openAssessment.id, "submit")} disabled={assessmentBusy}
                    className="px-3 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 text-[11px] font-bold disabled:opacity-40">Submit for approval</button>
                )}
                {openAssessment.approval_status === "SUBMITTED" && (
                  <>
                    <button onClick={() => assessmentApprovalAction(openAssessment.id, "approve")} disabled={assessmentBusy}
                      className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-[11px] font-bold disabled:opacity-40">Approve</button>
                    <button onClick={() => assessmentApprovalAction(openAssessment.id, "reject")} disabled={assessmentBusy}
                      className="px-3 py-1.5 rounded-lg bg-rose-500/20 text-rose-300 border border-rose-500/30 hover:bg-rose-500 hover:text-white text-[11px] font-bold disabled:opacity-40">Reject</button>
                  </>
                )}
                {openAssessment.approval_status === "APPROVED" && (
                  <button onClick={() => { setOpenAssessment(null); setActiveTab("reports"); }}
                    className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-[11px] font-bold">Generate report →</button>
                )}
              </div>
              <p className="text-[10px] text-slate-500">Approve/reject requires a Tenant Admin, Governance Lead, Compliance Manager, CISO or Legal Reviewer role.</p>
            </div>

            {/* Requirements (first 40, with quick status set) */}
            <div className="space-y-1.5">
              <div className="text-[11px] font-bold text-slate-300">Requirements</div>
              {(openAssessment.responses || []).slice(0, 40).map((r: any) => (
                <div key={r.requirement_id} className="flex items-center gap-2 p-2 rounded-lg bg-black/30 border border-white/5 text-[11px]">
                  <span className="font-mono text-sky-300 flex-shrink-0">{r.article || r.requirement_id}</span>
                  <span className="flex-1 min-w-0 truncate text-slate-300" title={r.normalized_requirement || r.title}>{r.title || r.normalized_requirement || r.requirement_id}</span>
                  <select
                    value={r.status || "Unknown"}
                    onChange={async (e) => {
                      try {
                        await api.submitAssessmentResponse(openAssessment.id, { requirement_id: r.requirement_id, status: e.target.value, rationale: r.rationale || "Set from assessment view", evidence_ids: r.evidence_ids || [] });
                        await openAssessmentDetail(openAssessment.id);
                        api.getPortfolioWorkflow().then(setPortfolioWorkflow).catch(() => {});
                      } catch (err: any) { alert(err?.message || "Could not save"); }
                    }}
                    className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-[10px] text-slate-200 flex-shrink-0"
                  >
                    {["Unknown", "Yes", "Partial", "No", "N/A"].map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              ))}
              {(openAssessment.responses || []).length > 40 && (
                <div className="text-[10px] text-slate-500">Showing 40 of {openAssessment.responses.length}. Full per-requirement work continues here in a later iteration.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {selectedControl && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-lg w-full rounded-2xl glass-panel p-6 space-y-4 border border-white/15 animate-scaleUp">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <span className="text-[10px] text-sky-400 font-mono font-bold">{selectedControl.code}</span>
                <h2 className="text-sm font-bold text-white">{selectedControl.title}</h2>
              </div>
              <button onClick={() => setSelectedControl(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-slate-300">{selectedControl.objective}</p>

              {(() => {
                const cw = crosswalk.find((c: any) => c.control_code === selectedControl.code || c.control_id === selectedControl.id);
                const maps = cw?.mappings || [];
                if (maps.length === 0) return null;
                return (
                  <div>
                    <label className="block text-slate-300 font-semibold mb-1">Satisfies requirements in {maps.length} framework{maps.length === 1 ? "" : "s"}</label>
                    <div className="flex flex-wrap gap-1.5">
                      {maps.map((m: any, i: number) => (
                        <button key={i}
                          onClick={() => { setSelectedControl(null); goToFrameworkRequirement(m.framework_id, m.requirement_id, m.article); }}
                          title={`${m.framework_name} ${m.article || m.requirement_id}${m.requirement_title ? " — " + m.requirement_title : ""} (${m.confidence})`}
                          className="text-[10px] font-mono text-sky-300 bg-sky-500/10 px-1.5 py-0.5 rounded border border-sky-500/20 hover:border-sky-400">
                          {m.framework_name}: {m.article || m.requirement_id} ↗
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })()}

              {(() => {
                const relatedEvidence = evidenceList.filter((ev: any) => (ev.satisfied_controls || []).includes(selectedControl.code));
                if (relatedEvidence.length === 0) return null;
                return (
                  <div>
                    <label className="block text-slate-300 font-semibold mb-1">Linked evidence ({relatedEvidence.length})</label>
                    <div className="flex flex-wrap gap-1.5">
                      {relatedEvidence.map((ev: any) => (
                        <button key={ev.id} onClick={() => { setSelectedControl(null); setActiveTab("evidence"); }}
                          className="text-[10px] text-indigo-300 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20 hover:border-indigo-400">
                          {ev.title} ↗
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })()}

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Implementation Status</label>
                <select
                  id="ctrl-status-select"
                  defaultValue={selectedControl.customer_status}
                  className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs"
                >
                  <option value="Implemented">Implemented</option>
                  <option value="Tested">Tested</option>
                  <option value="In Progress">In Progress</option>
                  <option value="Accepted Risk">Accepted Risk</option>
                  <option value="Not Started">Not Started</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Effectiveness Rating</label>
                <select
                  id="ctrl-eff-select"
                  defaultValue={selectedControl.customer_effectiveness}
                  className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs"
                >
                  <option value="Effective">Effective</option>
                  <option value="Partially Effective">Partially Effective</option>
                  <option value="Ineffective">Ineffective</option>
                </select>
              </div>
            </div>

            <div className="pt-3 border-t border-white/10 flex justify-end gap-2">
              <button
                onClick={() => setSelectedControl(null)}
                className="px-3 py-1.5 rounded-lg bg-white/10 text-xs text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const s = (document.getElementById("ctrl-status-select") as HTMLSelectElement).value;
                  const e = (document.getElementById("ctrl-eff-select") as HTMLSelectElement).value;
                  handleUpdateControl(selectedControl.id, s, e);
                }}
                className="px-4 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs"
              >
                Save & Recalculate Score
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 6. MODAL: UPLOAD EVIDENCE                                                */}
      {/* ========================================================================= */}
      {evidenceModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-lg w-full rounded-2xl glass-panel p-6 space-y-4 border border-white/15 animate-scaleUp">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Lock className="w-4 h-4 text-emerald-400" />
                Upload Evidence Artifact (Multi-Control Satisfaction)
              </h2>
              <button onClick={() => setEvidenceModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Artifact Title</label>
                <input
                  type="text"
                  placeholder="e.g. Red Team Adversarial Penetration Test Report"
                  value={newEvidence.title}
                  onChange={e => setNewEvidence({ ...newEvidence, title: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Evidence Type</label>
                <select
                  value={newEvidence.evidence_type}
                  onChange={e => setNewEvidence({ ...newEvidence, evidence_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs"
                >
                  <option value="Policy">Policy</option>
                  <option value="Architecture">Architecture Specification</option>
                  <option value="Test Report">Test / Red Team Report</option>
                  <option value="Model Card">Model Card / System Card</option>
                  <option value="DPIA">Data Protection Impact Assessment (DPIA)</option>
                  <option value="Audit Log">Operational Audit Log</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Tag Satisfied Unified Controls (Select Multiple)
                </label>
                <div className="max-h-40 overflow-y-auto space-y-1.5 p-2 rounded-lg bg-black/30 border border-white/10">
                  {controls.slice(0, 10).map(c => (
                    <label key={c.id} className="flex items-center gap-2 cursor-pointer text-[11px]">
                      <input
                        type="checkbox"
                        checked={newEvidence.selected_controls.includes(c.id)}
                        onChange={e => {
                          const next = e.target.checked
                            ? [...newEvidence.selected_controls, c.id]
                            : newEvidence.selected_controls.filter(id => id !== c.id);
                          setNewEvidence({ ...newEvidence, selected_controls: next });
                        }}
                      />
                      <span className="font-mono text-sky-300">{c.code}</span>
                      <span className="text-slate-300 truncate">{c.title}</span>
                    </label>
                  ))}
                </div>
                <div className="text-[10px] text-emerald-400 mt-1">
                  {newEvidence.selected_controls.length} controls selected. This artifact will satisfy all mapped requirements in the 17 frameworks!
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-white/10 flex justify-end gap-2">
              <button
                onClick={() => setEvidenceModalOpen(false)}
                className="px-3 py-1.5 rounded-lg bg-white/10 text-xs text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleUploadEvidence}
                className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs"
              >
                Upload & Compute SHA-256
              </button>
            </div>
          </div>
        </div>
      )}

      {registryModalOpen === "model" && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-lg w-full rounded-2xl glass-panel p-6 space-y-4 border border-white/15 animate-scaleUp">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <h2 className="text-sm font-bold text-white flex items-center gap-2"><Cpu className="w-4 h-4 text-sky-400" />Register Model</h2>
              <button onClick={() => setRegistryModalOpen(null)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Model Name</label>
                <input type="text" placeholder="e.g. Claude 3.5 Sonnet" value={newModelForm.name}
                  onChange={e => setNewModelForm({ ...newModelForm, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Provider</label>
                  <input type="text" value={newModelForm.provider} onChange={e => setNewModelForm({ ...newModelForm, provider: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs" />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Version</label>
                  <input type="text" value={newModelForm.version} onChange={e => setNewModelForm({ ...newModelForm, version: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs" />
                </div>
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Originating AI System</label>
                <select value={newModelForm.system_id} onChange={e => setNewModelForm({ ...newModelForm, system_id: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs">
                  <option value="">Select a system...</option>
                  {aiSystems.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
              <button onClick={() => setRegistryModalOpen(null)} className="px-4 py-1.5 rounded-lg bg-white/5 text-slate-300 text-xs">Cancel</button>
              <button onClick={handleCreateModel} className="px-4 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs">Register</button>
            </div>
          </div>
        </div>
      )}

      {registryModalOpen === "agent" && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-lg w-full rounded-2xl glass-panel p-6 space-y-4 border border-white/15 animate-scaleUp max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <h2 className="text-sm font-bold text-white flex items-center gap-2"><Terminal className="w-4 h-4 text-sky-400" />Register Agent</h2>
              <button onClick={() => setRegistryModalOpen(null)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Agent Name</label>
                <input type="text" placeholder="e.g. IT-Ops-Agent-Alpha" value={newAgentForm.name}
                  onChange={e => setNewAgentForm({ ...newAgentForm, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs" />
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Owning AI System</label>
                <select value={newAgentForm.system_id} onChange={e => setNewAgentForm({ ...newAgentForm, system_id: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs">
                  <option value="">Select a system...</option>
                  {aiSystems.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Autonomy Level</label>
                <select value={newAgentForm.autonomy_level} onChange={e => setNewAgentForm({ ...newAgentForm, autonomy_level: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs">
                  <option>Supervised</option>
                  <option>Semi-Autonomous</option>
                  <option>Fully Autonomous</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1">
                {([
                  ["has_code_execution", "Code Execution"],
                  ["has_database_access", "Database Access"],
                  ["has_payment_access", "Payment / Financial"],
                  ["has_git_access", "Git Read"],
                  ["has_git_write_access", "Git Write"],
                  ["accesses_pii", "Accesses PII"],
                ] as [string, string][]).map(([field, label]) => (
                  <label key={field} className="flex items-center gap-2 text-slate-300">
                    <input type="checkbox" checked={(newAgentForm as any)[field]}
                      onChange={e => setNewAgentForm({ ...newAgentForm, [field]: e.target.checked })} />
                    {label}
                  </label>
                ))}
              </div>
              <label className="flex items-center gap-2 text-slate-300 pt-1 border-t border-white/5">
                <input type="checkbox" checked={newAgentForm.human_approval_required}
                  onChange={e => setNewAgentForm({ ...newAgentForm, human_approval_required: e.target.checked })} />
                Human approval gate required
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
              <button onClick={() => setRegistryModalOpen(null)} className="px-4 py-1.5 rounded-lg bg-white/5 text-slate-300 text-xs">Cancel</button>
              <button onClick={handleCreateAgent} className="px-4 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs">Register</button>
            </div>
          </div>
        </div>
      )}

      {registryModalOpen === "vendor" && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-lg w-full rounded-2xl glass-panel p-6 space-y-4 border border-white/15 animate-scaleUp">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <h2 className="text-sm font-bold text-white flex items-center gap-2"><Building className="w-4 h-4 text-sky-400" />Register Vendor</h2>
              <button onClick={() => setRegistryModalOpen(null)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Vendor Name</label>
                <input type="text" placeholder="e.g. Anthropic PBC" value={newVendorForm.name}
                  onChange={e => setNewVendorForm({ ...newVendorForm, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs" />
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Service Type</label>
                <input type="text" value={newVendorForm.service_type} onChange={e => setNewVendorForm({ ...newVendorForm, service_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Data Processing Role</label>
                  <select value={newVendorForm.data_processing_role} onChange={e => setNewVendorForm({ ...newVendorForm, data_processing_role: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs">
                    <option>Controller</option>
                    <option>Processor</option>
                    <option>Sub-processor</option>
                    <option>Joint Controller</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Risk Rating</label>
                  <select value={newVendorForm.risk_rating} onChange={e => setNewVendorForm({ ...newVendorForm, risk_rating: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white text-xs">
                    <option>Low</option>
                    <option>Medium</option>
                    <option>High</option>
                    <option>Critical</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
              <button onClick={() => setRegistryModalOpen(null)} className="px-4 py-1.5 rounded-lg bg-white/5 text-slate-300 text-xs">Cancel</button>
              <button onClick={handleCreateVendor} className="px-4 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs">Register</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SparklesIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="currentColor" viewBox="0 0 24 24" {...props}>
      <path d="M12 2L14.4 7.6L20 10L14.4 12.4L12 18L9.6 12.4L4 10L9.6 7.6L12 2Z" />
    </svg>
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

  const handleSubmit = async (e: React.FormEvent) => {
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
    <div className="flex h-screen w-screen items-center justify-center bg-[#090D16] text-[#F8FAFC] px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/25">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div className="font-bold text-lg tracking-tight flex items-center gap-1.5">
            <span>Aegis</span>
            <span className="text-sky-400 font-extrabold text-xs px-1.5 py-0.5 rounded bg-sky-500/10 border border-sky-500/20">OS</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="glass-panel rounded-xl p-6 space-y-4">
          <h1 className="text-sm font-bold text-slate-200">
            {mode === "login" ? "Sign in to your organization" : "Create your organization"}
          </h1>

          {mode === "signup" && (
            <>
              <div className="space-y-1">
                <label className="text-[11px] font-medium text-slate-400">Full name</label>
                <input
                  required value={fullName} onChange={e => setFullName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs text-slate-200 focus:outline-none focus:border-sky-500/50"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] font-medium text-slate-400">Organization name</label>
                <input
                  required value={orgName} onChange={e => setOrgName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs text-slate-200 focus:outline-none focus:border-sky-500/50"
                />
              </div>
            </>
          )}

          <div className="space-y-1">
            <label className="text-[11px] font-medium text-slate-400">Email address</label>
            <input
              type="email" required value={email} onChange={e => setEmail(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs text-slate-200 focus:outline-none focus:border-sky-500/50"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-slate-400">Password</label>
            <input
              type="password" required value={password} onChange={e => setPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs text-slate-200 focus:outline-none focus:border-sky-500/50"
            />
          </div>

          {error && (
            <div className="text-[11px] text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit" disabled={submitting}
            className="w-full py-2 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:opacity-50 text-slate-950 font-bold text-xs transition-colors"
          >
            {submitting ? "Please wait..." : mode === "login" ? "Sign in" : "Create organization"}
          </button>

          <button
            type="button"
            onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(null); }}
            className="w-full text-[11px] text-slate-400 hover:text-sky-400 transition-colors"
          >
            {mode === "login" ? "New organization? Create one" : "Already have an account? Sign in"}
          </button>
        </form>

        <p className="text-[10px] text-slate-500 text-center mt-4">
          Governance Guidance • Not Legal Advice
        </p>
      </div>
    </div>
  );
}
