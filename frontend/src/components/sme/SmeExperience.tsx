"use client";

/**
 * SME / "Simple" experience (spec sections 4-7, 16, 22, 23, 28).
 *
 * Rendered instead of the full enterprise console when currentUser.ui_mode ===
 * "simple". It talks to the SAME backend - the new /onboarding and /sme
 * endpoints - and a "Switch to advanced view" control flips ui_mode so the
 * existing enterprise UI (unchanged) takes over. No enterprise capability is
 * removed; this is an additional, simpler lens on the same data.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Shield, ArrowRight, ArrowLeft, CheckCircle2, AlertTriangle, Sparkles,
  Building, Cpu, Database, Package, ClipboardCheck, RefreshCw, ChevronRight,
  Scale, BookOpen, ListChecks, Gauge, ExternalLink, Info,
} from "lucide-react";
import * as api from "@/lib/api";

const EU = ["DE", "FR", "ES", "IT", "NL", "IE", "PL", "SE", "BE", "AT", "DK", "FI", "PT", "GR", "RO"];
const COUNTRY_OPTS = [
  ["US", "United States"], ["GB", "United Kingdom"], ["IN", "India"], ["SG", "Singapore"],
  ["DE", "Germany"], ["FR", "France"], ["NL", "Netherlands"], ["IE", "Ireland"],
  ["CA", "Canada"], ["AU", "Australia"], ["AE", "UAE"], ["BR", "Brazil"],
];
const INDUSTRIES = [
  ["b2b_saas", "B2B SaaS / Software"], ["fintech", "FinTech / InsurTech / RegTech"],
  ["healthtech", "HealthTech"], ["hrtech", "HRTech / Recruitment"],
  ["cybersecurity", "Cybersecurity software"], ["iot", "IoT / Connected products / Robotics"],
  ["it_services", "IT / AI services"], ["ecommerce", "E-commerce / Consumer"], ["other", "Other"],
];
const PROVIDERS = [
  ["openai", "OpenAI"], ["anthropic", "Anthropic"], ["google", "Google Gemini"],
  ["azure_openai", "Azure OpenAI"], ["aws_bedrock", "AWS Bedrock"], ["meta", "Meta / Llama"],
  ["mistral", "Mistral"], ["cohere", "Cohere"], ["huggingface", "Hugging Face"],
  ["self_hosted", "Self-hosted / open-source"],
];
const DATA_TYPES = [
  ["personal", "Personal data"], ["employee", "Employee data"], ["health", "Health data"],
  ["financial", "Financial data"], ["biometric", "Biometric data"], ["children", "Children's data"],
  ["payment", "Payment / card data"], ["source_code", "Source code"],
  ["customer_confidential", "Customer proprietary / confidential data"],
];
const DECISION_DOMAINS = [
  ["employment", "Employment / recruitment"], ["credit", "Credit / lending"],
  ["education", "Education / admissions"], ["insurance", "Insurance"],
  ["healthcare", "Healthcare / clinical"], ["biometrics", "Biometric identification"],
  ["essential_services", "Access to essential services"],
];

const EXPOSURE_STYLE: Record<string, string> = {
  DIRECTLY_APPLICABLE: "text-rose-300 bg-rose-500/10 border-rose-500/30",
  POTENTIALLY_APPLICABLE: "text-amber-300 bg-amber-500/10 border-amber-500/30",
  CONTRACTUALLY_REQUIRED: "text-fuchsia-300 bg-fuchsia-500/10 border-fuchsia-500/30",
  SUPPLY_CHAIN_INDIRECT: "text-sky-300 bg-sky-500/10 border-sky-500/30",
  RECOMMENDED_BEST_PRACTICE: "text-emerald-300 bg-emerald-500/10 border-emerald-500/30",
  NOT_APPLICABLE: "text-slate-400 bg-slate-500/10 border-slate-500/30",
  INSUFFICIENT_INFORMATION: "text-slate-300 bg-slate-500/10 border-slate-500/30",
};
const REGTYPE_LABEL: Record<string, string> = {
  LEGAL_REGULATORY: "Law / regulation",
  CERTIFICATION: "Certification",
  VOLUNTARY_FRAMEWORK: "Voluntary framework",
  SECURITY_BEST_PRACTICE: "Security best practice",
  CONTRACTUAL: "Customer / contract",
};
const RISK_STYLE: Record<string, string> = {
  CRITICAL: "text-rose-300 bg-rose-500/10 border-rose-500/30",
  HIGH: "text-amber-300 bg-amber-500/10 border-amber-500/30",
  MEDIUM: "text-sky-300 bg-sky-500/10 border-sky-500/30",
  LOW: "text-slate-300 bg-slate-500/10 border-slate-500/30",
};

const inputCls =
  "w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs text-slate-200 focus:outline-none focus:border-sky-500/50";

function Toggle({ label, hint, checked, onChange }: { label: string; hint?: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`flex items-start gap-3 w-full text-left p-3 rounded-lg border transition-colors ${
        checked ? "bg-sky-500/10 border-sky-500/40" : "bg-white/5 border-white/10 hover:border-white/20"
      }`}
    >
      <div className={`mt-0.5 w-4 h-4 rounded flex items-center justify-center flex-shrink-0 border ${checked ? "bg-sky-500 border-sky-500" : "border-white/30"}`}>
        {checked && <CheckCircle2 className="w-3 h-3 text-slate-950" />}
      </div>
      <div>
        <div className="text-xs font-medium text-slate-200">{label}</div>
        {hint && <div className="text-[10px] text-slate-500 mt-0.5">{hint}</div>}
      </div>
    </button>
  );
}

function MultiChip({ options, value, onChange }: { options: string[][]; value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map(([k, label]) => {
        const on = value.includes(k);
        return (
          <button
            key={k}
            type="button"
            onClick={() => onChange(on ? value.filter((x) => x !== k) : [...value, k])}
            className={`px-2.5 py-1 rounded-full text-[11px] border transition-colors ${
              on ? "bg-sky-500/15 border-sky-500/40 text-sky-200" : "bg-white/5 border-white/10 text-slate-400 hover:border-white/20"
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Onboarding wizard                                                    */
/* ------------------------------------------------------------------ */
const BLANK = {
  company_name: "",
  headquarters_country: "US",
  operating_countries: ["US"] as string[],
  employee_count: 25,
  industry: "b2b_saas",
  sells_to_enterprises: true,
  sells_to_government: false,
  sells_to_financial_institutions: false,
  sells_to_healthcare: false,
  develops_ai_products: true,
  deploys_ai_internally: true,
  uses_generative_ai: true,
  builds_ai_agents: false,
  uses_rag: false,
  uses_third_party_models: true,
  makes_decisions_about_people: false,
  decision_domains: [] as string[],
  uses_biometrics: false,
  ai_providers: [] as string[],
  data_types: [] as string[],
  sells_software: true,
  is_saas: true,
  sells_connected_hardware: false,
  is_iot: false,
  has_embedded_software: false,
  is_cybersecurity_product: false,
  product_marketed_in_eu: false,
  soc2_required: false,
  iso27001_required: false,
  gets_security_questionnaires: true,
  has_compliance_staff: false,
  has_security_staff: false,
};

const STEPS = [
  { key: "company", label: "Company", icon: Building },
  { key: "ai", label: "AI use", icon: Cpu },
  { key: "providers", label: "Providers", icon: Sparkles },
  { key: "data", label: "Data", icon: Database },
  { key: "product", label: "Product & reviews", icon: Package },
];

function OnboardingWizard({ orgName, onComplete }: { orgName: string; onComplete: () => void }) {
  const [form, setForm] = useState<any>({ ...BLANK, company_name: orgName });
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (patch: any) => setForm((f: any) => ({ ...f, ...patch }));

  const euExposed = useMemo(
    () => form.operating_countries.some((c: string) => EU.includes(c)) || form.product_marketed_in_eu,
    [form.operating_countries, form.product_marketed_in_eu]
  );

  const finish = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.saveOnboardingProfile({ ...form, product_marketed_in_eu: form.product_marketed_in_eu || euExposed, completed: true, answers: form });
      onComplete();
    } catch (e: any) {
      setError(e.message || "Could not save your profile");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-10 px-4">
      <div className="flex items-center gap-2 mb-1 text-sky-400">
        <Sparkles className="w-4 h-4" />
        <span className="text-[11px] font-semibold uppercase tracking-wider">5-minute setup</span>
      </div>
      <h1 className="text-xl font-bold text-slate-100 mb-1">Tell us about your company</h1>
      <p className="text-xs text-slate-400 mb-6">
        We use this to work out which regulations and frameworks actually apply to you — and what to do first.
        You are not picking frameworks; we determine them. You can change any answer later.
      </p>

      <div className="flex items-center gap-1 mb-6">
        {STEPS.map((s, i) => (
          <React.Fragment key={s.key}>
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] ${i === step ? "bg-sky-500/15 text-sky-200" : i < step ? "text-emerald-300" : "text-slate-500"}`}>
              <s.icon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{s.label}</span>
            </div>
            {i < STEPS.length - 1 && <div className="flex-1 h-px bg-white/10" />}
          </React.Fragment>
        ))}
      </div>

      <div className="glass-panel rounded-xl p-5 space-y-4 min-h-[320px]">
        {step === 0 && (
          <>
            <Field label="Company name">
              <input className={inputCls} value={form.company_name} onChange={(e) => set({ company_name: e.target.value })} />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Headquarters">
                <select className={inputCls} value={form.headquarters_country} onChange={(e) => set({ headquarters_country: e.target.value })}>
                  {COUNTRY_OPTS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                </select>
              </Field>
              <Field label="Employees">
                <input type="number" min={1} className={inputCls} value={form.employee_count} onChange={(e) => set({ employee_count: parseInt(e.target.value || "0", 10) })} />
              </Field>
            </div>
            <Field label="Countries you operate in / sell to">
              <MultiChip options={COUNTRY_OPTS} value={form.operating_countries} onChange={(v) => set({ operating_countries: v })} />
            </Field>
            <Field label="Industry">
              <select className={inputCls} value={form.industry} onChange={(e) => set({ industry: e.target.value })}>
                {INDUSTRIES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
              </select>
            </Field>
            <div className="grid sm:grid-cols-2 gap-2">
              <Toggle label="We sell to enterprises" checked={form.sells_to_enterprises} onChange={(v) => set({ sells_to_enterprises: v })} />
              <Toggle label="We sell to government" checked={form.sells_to_government} onChange={(v) => set({ sells_to_government: v })} />
              <Toggle label="We sell to financial institutions" checked={form.sells_to_financial_institutions} onChange={(v) => set({ sells_to_financial_institutions: v })} />
              <Toggle label="We sell to healthcare" checked={form.sells_to_healthcare} onChange={(v) => set({ sells_to_healthcare: v })} />
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <div className="grid sm:grid-cols-2 gap-2">
              <Toggle label="We build AI into our product" checked={form.develops_ai_products} onChange={(v) => set({ develops_ai_products: v })} />
              <Toggle label="We use AI internally" checked={form.deploys_ai_internally} onChange={(v) => set({ deploys_ai_internally: v })} />
              <Toggle label="We use generative AI / LLMs" checked={form.uses_generative_ai} onChange={(v) => set({ uses_generative_ai: v })} />
              <Toggle label="We build RAG applications" checked={form.uses_rag} onChange={(v) => set({ uses_rag: v })} />
              <Toggle label="We build AI agents" hint="Autonomous systems that use tools / take actions" checked={form.builds_ai_agents} onChange={(v) => set({ builds_ai_agents: v })} />
              <Toggle label="We use third-party / foundation models" checked={form.uses_third_party_models} onChange={(v) => set({ uses_third_party_models: v })} />
            </div>
            <Toggle label="Our AI makes or supports decisions about people" checked={form.makes_decisions_about_people} onChange={(v) => set({ makes_decisions_about_people: v })} />
            {form.makes_decisions_about_people && (
              <Field label="In which areas?">
                <MultiChip options={DECISION_DOMAINS} value={form.decision_domains} onChange={(v) => set({ decision_domains: v })} />
              </Field>
            )}
            <Toggle label="We use biometric systems (face / voice / fingerprint)" checked={form.uses_biometrics} onChange={(v) => set({ uses_biometrics: v })} />
          </>
        )}

        {step === 2 && (
          <Field label="Which AI providers / model hosts do you use?">
            <MultiChip options={PROVIDERS} value={form.ai_providers} onChange={(v) => set({ ai_providers: v })} />
            <p className="text-[10px] text-slate-500 mt-2">
              Each provider you select becomes a vendor to register and risk-assess. That is the #1 gap enterprises flag.
            </p>
          </Field>
        )}

        {step === 3 && (
          <Field label="What kinds of data does your company handle?">
            <MultiChip options={DATA_TYPES} value={form.data_types} onChange={(v) => set({ data_types: v })} />
          </Field>
        )}

        {step === 4 && (
          <>
            <div className="grid sm:grid-cols-2 gap-2">
              <Toggle label="We sell software" checked={form.sells_software} onChange={(v) => set({ sells_software: v })} />
              <Toggle label="Delivered as SaaS" checked={form.is_saas} onChange={(v) => set({ is_saas: v })} />
              <Toggle label="We sell connected hardware" checked={form.sells_connected_hardware} onChange={(v) => set({ sells_connected_hardware: v })} />
              <Toggle label="Our product has embedded software" checked={form.has_embedded_software} onChange={(v) => set({ has_embedded_software: v })} />
              <Toggle label="It's an IoT / connected product" checked={form.is_iot} onChange={(v) => set({ is_iot: v })} />
              <Toggle label="It's a cybersecurity product" checked={form.is_cybersecurity_product} onChange={(v) => set({ is_cybersecurity_product: v })} />
              <Toggle label="Product is marketed in the EU" checked={form.product_marketed_in_eu} onChange={(v) => set({ product_marketed_in_eu: v })} />
            </div>
            <div className="grid sm:grid-cols-2 gap-2">
              <Toggle label="Customers ask us for SOC 2" checked={form.soc2_required} onChange={(v) => set({ soc2_required: v })} />
              <Toggle label="Customers ask us for ISO 27001" checked={form.iso27001_required} onChange={(v) => set({ iso27001_required: v })} />
              <Toggle label="We get security questionnaires" checked={form.gets_security_questionnaires} onChange={(v) => set({ gets_security_questionnaires: v })} />
              <Toggle label="We have a dedicated compliance person" checked={form.has_compliance_staff} onChange={(v) => set({ has_compliance_staff: v })} />
            </div>
          </>
        )}

        {error && <div className="text-[11px] text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">{error}</div>}
      </div>

      <div className="flex items-center justify-between mt-4">
        <button
          type="button"
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs text-slate-400 hover:text-slate-200 disabled:opacity-30"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back
        </button>
        {step < STEPS.length - 1 ? (
          <button
            type="button"
            onClick={() => setStep((s) => s + 1)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold"
          >
            Next <ArrowRight className="w-3.5 h-3.5" />
          </button>
        ) : (
          <button
            type="button"
            onClick={finish}
            disabled={submitting}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold disabled:opacity-50"
          >
            {submitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
            See my compliance profile
          </button>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[11px] font-medium text-slate-400">{label}</label>
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Compliance profile dashboard                                         */
/* ------------------------------------------------------------------ */
function ScoreRing({ score }: { score: number }) {
  const r = 44;
  const c = 2 * Math.PI * r;
  const off = c - (Math.max(0, Math.min(100, score)) / 100) * c;
  const color = score >= 75 ? "#34d399" : score >= 50 ? "#38bdf8" : score >= 25 ? "#fbbf24" : "#fb7185";
  return (
    <svg viewBox="0 0 100 100" className="w-28 h-28">
      <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="8" />
      <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={off} transform="rotate(-90 50 50)" />
      <text x="50" y="48" textAnchor="middle" className="fill-slate-100" style={{ fontSize: 20, fontWeight: 700 }}>{score.toFixed(0)}</text>
      <text x="50" y="63" textAnchor="middle" className="fill-slate-500" style={{ fontSize: 9 }}>/ 100</text>
    </svg>
  );
}

function SmeDashboard({ onReRunOnboarding }: { onReRunOnboarding: () => void }) {
  const [tab, setTab] = useState<"home" | "compliance" | "actions" | "frameworks">("home");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [trust, setTrust] = useState<any>(null);
  const [appl, setAppl] = useState<any>(null);
  const [actions, setActions] = useState<any>(null);
  const [catalog, setCatalog] = useState<any>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [t, a, n, c] = await Promise.all([
        api.getTrustScore(),
        api.getCompanyApplicability().catch(() => null),
        api.getNextActions(),
        api.getFrameworksCatalog().catch(() => null),
      ]);
      setTrust(t); setAppl(a); setActions(n); setCatalog(c);
    } catch (e: any) {
      setErr(e.message || "Could not load your profile");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return <div className="flex items-center justify-center py-32"><RefreshCw className="w-5 h-5 text-sky-400 animate-spin" /></div>;
  }
  if (err) {
    return <div className="max-w-lg mx-auto mt-20 text-xs text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-lg p-4">{err}</div>;
  }

  const TABS = [
    { key: "home", label: "Home", icon: Gauge },
    { key: "compliance", label: "What applies to us", icon: Scale },
    { key: "actions", label: "What to do next", icon: ListChecks },
    { key: "frameworks", label: "Frameworks", icon: BookOpen },
  ] as const;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center gap-1 mb-6 border-b border-white/10">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium border-b-2 -mb-px transition-colors ${
              tab === t.key ? "border-sky-400 text-sky-300" : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
        <button onClick={load} className="ml-auto flex items-center gap-1.5 px-2 py-1 text-[11px] text-slate-400 hover:text-sky-300">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      {tab === "home" && <HomeTab trust={trust} actions={actions} appl={appl} />}
      {tab === "compliance" && <ComplianceTab appl={appl} onReRunOnboarding={onReRunOnboarding} />}
      {tab === "actions" && <ActionsTab actions={actions} />}
      {tab === "frameworks" && <FrameworksTab catalog={catalog} appl={appl} />}
    </div>
  );
}

function HomeTab({ trust, actions, appl }: any) {
  const top = (actions?.actions || []).slice(0, 5);
  return (
    <div className="space-y-5">
      <div className="glass-panel rounded-xl p-5 flex flex-col sm:flex-row gap-6 items-center">
        <div className="flex items-center gap-4">
          <ScoreRing score={trust?.ai_trust_score ?? 0} />
          <div>
            <div className="text-sm font-bold text-slate-100">AI Trust Score</div>
            <div className="text-[11px] text-slate-400 max-w-[220px] mt-1">
              {trust?.has_data
                ? "Derived from your real control, evidence and finding state."
                : "You have not started tracking controls yet — the score updates as you do."}
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 flex-1 w-full">
          {(trust?.dimensions || []).map((d: any) => (
            <div key={d.key} className="bg-white/5 rounded-lg p-2.5">
              <div className="text-[10px] text-slate-400">{d.label}</div>
              <div className="text-base font-bold text-slate-100">{d.score.toFixed(0)}%</div>
              <div className="text-[9px] text-slate-500 truncate" title={d.basis}>{d.basis}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid sm:grid-cols-4 gap-3">
        {[
          ["AI systems", trust?.inventory?.ai_systems],
          ["Models", trust?.inventory?.models],
          ["Agents", trust?.inventory?.agents],
          ["Vendors", trust?.inventory?.vendors],
        ].map(([l, v]) => (
          <div key={l as string} className="glass-panel rounded-lg p-3">
            <div className="text-[10px] text-slate-400">{l as string}</div>
            <div className="text-xl font-bold text-slate-100">{v ?? 0}</div>
          </div>
        ))}
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-bold text-slate-200">Top actions this week</h3>
          <span className="text-[10px] text-slate-500">
            {actions?.counts?.TODAY ?? 0} today · {actions?.counts?.THIS_WEEK ?? 0} this week
          </span>
        </div>
        <div className="space-y-2">
          {top.length === 0 && <div className="text-[11px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">No open actions — nice.</div>}
          {top.map((a: any) => <ActionCard key={a.id} a={a} />)}
        </div>
      </div>

      {appl?.legal_review_recommended && (
        <div className="text-[11px] text-amber-200 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 flex gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>Some framework applicability depends on legal interpretation ({appl.legal_review_frameworks.join(", ")}). We recommend a short legal review to confirm.</span>
        </div>
      )}
    </div>
  );
}

function ComplianceTab({ appl, onReRunOnboarding }: any) {
  if (!appl) {
    return (
      <div className="text-xs text-slate-400">
        Complete onboarding to see your framework exposure.{" "}
        <button onClick={onReRunOnboarding} className="text-sky-300 underline">Start onboarding</button>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-[11px] text-slate-400 max-w-xl">{appl.disclaimer}</p>
        <button onClick={onReRunOnboarding} className="text-[11px] text-sky-300 hover:underline flex-shrink-0 ml-3">Update answers</button>
      </div>
      <div className="text-[10px] text-slate-500">Ruleset {appl.ruleset_version} · {appl.exposures.length} frameworks assessed</div>
      <div className="space-y-2">
        {appl.exposures.map((e: any) => (
          <details key={e.rule_id} className="glass-panel rounded-lg p-3 group">
            <summary className="flex items-center gap-2 cursor-pointer list-none">
              <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-open:rotate-90 transition-transform" />
              <span className="text-xs font-semibold text-slate-100 flex-1">{e.framework_name}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full border ${EXPOSURE_STYLE[e.exposure] || ""}`}>{e.exposure_label}</span>
            </summary>
            <div className="mt-2.5 pl-5 space-y-2 text-[11px]">
              <div className="flex flex-wrap gap-2">
                <span className="text-slate-500">{REGTYPE_LABEL[e.regulation_type] || e.regulation_type}</span>
                <span className="text-slate-600">·</span>
                <span className="text-slate-500">{e.jurisdiction}</span>
                <span className="text-slate-600">·</span>
                <span className={e.confidence === "LEGAL_REVIEW_REQUIRED" ? "text-amber-300" : "text-slate-500"}>
                  Confidence: {e.confidence.replace(/_/g, " ").toLowerCase()}
                </span>
              </div>
              <p className="text-slate-300">{e.reasoning}</p>
              <p className="text-slate-500"><span className="text-slate-400">Why we flagged it:</span> {e.triggering_facts.join("; ")}</p>
              <p className="text-slate-500"><span className="text-slate-400">Source:</span> {e.source_reference}</p>
              {e.open_questions?.length > 0 && (
                <p className="text-slate-500"><span className="text-slate-400">Still to confirm:</span> {e.open_questions.map((q: string) => q.replace(/_/g, " ")).join("; ")}</p>
              )}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

function ActionsTab({ actions }: any) {
  const buckets: [string, string][] = [["TODAY", "Today"], ["THIS_WEEK", "This week"], ["NEXT", "Next"]];
  return (
    <div className="space-y-5">
      {buckets.map(([k, label]) => {
        const items = (actions?.actions || []).filter((a: any) => a.bucket === k);
        if (items.length === 0) return null;
        return (
          <div key={k}>
            <h3 className="text-xs font-bold text-slate-200 mb-2">{label} <span className="text-slate-500 font-normal">· {items.length}</span></h3>
            <div className="space-y-2">{items.map((a: any) => <ActionCard key={a.id} a={a} expanded />)}</div>
          </div>
        );
      })}
      {(actions?.actions || []).length === 0 && (
        <div className="text-[11px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">No open actions.</div>
      )}
    </div>
  );
}

function ActionCard({ a, expanded }: { a: any; expanded?: boolean }) {
  const [open, setOpen] = useState(!!expanded);
  return (
    <div className="glass-panel rounded-lg p-3">
      <button onClick={() => setOpen(!open)} className="flex items-start gap-2.5 w-full text-left">
        <span className={`text-[9px] px-1.5 py-0.5 rounded border flex-shrink-0 mt-0.5 ${RISK_STYLE[a.risk] || ""}`}>{a.risk}</span>
        <span className="flex-1">
          <span className="text-xs font-medium text-slate-100">{a.title}</span>
          <span className="block text-[10px] text-slate-500 mt-0.5">~{a.estimated_minutes} min · {a.affected_areas.slice(0, 4).join(", ")}</span>
        </span>
        <ChevronRight className={`w-3.5 h-3.5 text-slate-500 flex-shrink-0 transition-transform ${open ? "rotate-90" : ""}`} />
      </button>
      {open && (
        <div className="mt-2.5 pl-8 space-y-2 text-[11px]">
          <p className="text-slate-300"><span className="text-slate-400">Why this matters:</span> {a.why_it_matters}</p>
          {a.steps?.length > 0 && (
            <ol className="list-decimal list-inside text-slate-400 space-y-0.5">
              {a.steps.map((s: string, i: number) => <li key={i}>{s}</li>)}
            </ol>
          )}
          <div className="flex flex-wrap gap-1.5 pt-1">
            {a.actions.map((label: string) => (
              <span key={label} className="text-[10px] px-2 py-0.5 rounded bg-white/5 border border-white/10 text-slate-400">{label}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function FrameworksTab({ catalog, appl }: any) {
  const exposures: Record<string, any> = {};
  (appl?.exposures || []).forEach((e: any) => (exposures[e.framework_key] = e));
  return (
    <div className="space-y-4">
      <p className="text-[11px] text-slate-400">
        Your applicable regulations and voluntary frameworks are on the <span className="text-slate-300">“What applies to us”</span> tab.
        Below are the certification standards (SOC 2, ISO) — we hold the structure and control mappings, not the copyrighted text.
      </p>
      {(catalog?.commercial_frameworks || []).map((f: any) => (
        <div key={f.framework_key} className="glass-panel rounded-lg p-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-100">{f.framework_name}</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-500/10 border border-slate-500/30 text-slate-400">Metadata only</span>
            {exposures[f.framework_key] && (
              <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${EXPOSURE_STYLE[exposures[f.framework_key].exposure] || ""}`}>
                {exposures[f.framework_key].exposure_label}
              </span>
            )}
          </div>
          <p className="text-[10px] text-slate-500 mt-1">{f.jurisdiction}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {Object.values(f.public_structure || {}).flat().slice(0, 10).map((s: any, i: number) => (
              <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-slate-400">{String(s)}</span>
            ))}
          </div>
          <p className="text-[10px] text-slate-500 mt-2">
            {f.unified_control_mappings?.length || 0} mappings to your unified controls · load your licensed copy to unlock full assessment.
          </p>
        </div>
      ))}
      <a href={catalog?.regulatory_catalog_endpoint || "#"} className="hidden" aria-hidden />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Shell                                                                */
/* ------------------------------------------------------------------ */
export default function SmeExperience({
  user,
  onUserChange,
  onLogout,
}: {
  user: api.CurrentUser;
  onUserChange: (u: api.CurrentUser) => void;
  onLogout: () => void;
}) {
  const [onboarded, setOnboarded] = useState<boolean>(!!user.onboarding_completed);
  const [wizardOpen, setWizardOpen] = useState<boolean>(!user.onboarding_completed);
  const [switching, setSwitching] = useState(false);

  const switchToAdvanced = async () => {
    setSwitching(true);
    try {
      const updated = await api.setUiMode("advanced");
      onUserChange(updated);
    } catch {
      setSwitching(false);
    }
  };

  const completeOnboarding = async () => {
    try {
      const me = await api.refreshCurrentUser();
      onUserChange(me);
    } catch { /* ignore - fall through */ }
    setOnboarded(true);
    setWizardOpen(false);
  };

  return (
    <div className="min-h-screen w-screen bg-[#090D16] text-[#F8FAFC] overflow-y-auto">
      <header className="sticky top-0 z-10 backdrop-blur bg-[#090D16]/80 border-b border-white/10">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <div className="font-bold text-sm">
            AI Trust <span className="text-slate-500 font-medium">&amp; Compliance</span>
          </div>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/10 border border-sky-500/20 text-sky-300">Simple</span>
          <div className="ml-auto flex items-center gap-3">
            <span className="text-[11px] text-slate-400 hidden sm:block">{user.organization_name}</span>
            <button
              onClick={switchToAdvanced}
              disabled={switching}
              className="text-[11px] px-2.5 py-1 rounded-lg border border-white/10 text-slate-300 hover:border-sky-500/40 hover:text-sky-300 transition-colors"
            >
              {switching ? "Switching…" : "Switch to advanced view"}
            </button>
            <button onClick={onLogout} className="text-[11px] text-slate-500 hover:text-slate-300">Sign out</button>
          </div>
        </div>
      </header>

      {wizardOpen || !onboarded ? (
        <OnboardingWizard orgName={user.organization_name || ""} onComplete={completeOnboarding} />
      ) : (
        <SmeDashboard onReRunOnboarding={() => setWizardOpen(true)} />
      )}

      <footer className="max-w-5xl mx-auto px-4 py-6 text-[10px] text-slate-600">
        Governance guidance, not legal advice. The same data is available in the advanced view.
      </footer>
    </div>
  );
}
