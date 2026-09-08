"use client";

/**
 * Full-screen company create / edit experience (spec sections 2, 3, 13-18, 22).
 * A viewport-aware overlay - never a clipped modal. Sticky header (progress) +
 * sticky footer (Back / Continue), the middle scrolls. Every field has a visible
 * label; nothing relies on placeholder text. No incorrect default location.
 */

import React, { useMemo, useState } from "react";
import { X, ChevronLeft, ChevronRight, Check, RefreshCw, Building2 } from "lucide-react";
import * as api from "@/lib/api";
import {
  COUNTRIES, INDUSTRIES, COMPANY_TYPES, EMPLOYEE_RANGES, EU_EEA_CODES,
  countryName, industryLabel, employeeRangeLabel,
} from "@/lib/referenceData";
import { Field, TextInput, SearchableSelect, MultiCountrySelect, Toggle } from "@/components/forms/FormControls";

export interface CompanyFormValue {
  name: string;
  legal_name: string;
  website: string;
  company_type: string;
  industry: string;
  custom_industry: string;
  employee_range: string;
  headquarters_country: string;
  operating_countries: string[];
  ai_deployment_countries: string[];
  customer_countries: string[];
  uses_ai: boolean;
  uses_genai: boolean;
  uses_agents: boolean;
  is_financial_institution: boolean;
  is_critical_infrastructure: boolean;
  is_software_vendor: boolean;
  eu_market_exposure: boolean;
  processes_personal_data: boolean;
  governance_lead: string;
  compliance_lead: string;
  security_lead: string;
  privacy_dpo: string;
  legal_contact: string;
}

const BLANK: CompanyFormValue = {
  name: "", legal_name: "", website: "", company_type: "", industry: "", custom_industry: "",
  employee_range: "", headquarters_country: "", operating_countries: [], ai_deployment_countries: [],
  customer_countries: [], uses_ai: true, uses_genai: false, uses_agents: false,
  is_financial_institution: false, is_critical_infrastructure: false, is_software_vendor: false,
  eu_market_exposure: false, processes_personal_data: true,
  governance_lead: "", compliance_lead: "", security_lead: "", privacy_dpo: "", legal_contact: "",
};

const STEPS = ["Company details", "Operating footprint", "AI & regulatory profile", "Governance contacts", "Review"];

export default function CompanyWizard({
  mode, initial, onClose, onDone,
}: {
  mode: "create" | "edit";
  initial?: Partial<CompanyFormValue>;
  onClose: () => void;
  onDone: (createdName: string) => void;
}) {
  const [step, setStep] = useState(0);
  const [f, setF] = useState<CompanyFormValue>({ ...BLANK, ...initial });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const set = (p: Partial<CompanyFormValue>) => setF((v) => ({ ...v, ...p }));

  const industryOptions = INDUSTRIES;
  const resolvedIndustry = f.industry.startsWith("__custom__")
    ? f.industry.replace("__custom__", "")
    : (f.industry === "other" && f.custom_industry ? f.custom_industry : f.industry);

  const euExposed = useMemo(
    () => f.eu_market_exposure ||
      [...f.operating_countries, ...f.ai_deployment_countries, ...f.customer_countries].some((c) => EU_EEA_CODES.has(c)),
    [f.eu_market_exposure, f.operating_countries, f.ai_deployment_countries, f.customer_countries]
  );

  const validateStep = (s: number): boolean => {
    const e: Record<string, string> = {};
    if (s === 0) {
      if (!f.name.trim()) e.name = "Company name is required.";
      else if (f.name.length > 200) e.name = "Company name must be 200 characters or fewer.";
      if (f.legal_name && f.legal_name.length > 255) e.legal_name = "Legal name must be 255 characters or fewer.";
      if (f.website && !/^https?:\/\/.+\..+/.test(f.website.trim())) e.website = "Enter a valid URL, e.g. https://example.com";
      if (!f.industry) e.industry = "Select a primary industry.";
      if (f.industry === "other" && !f.custom_industry.trim() && !f.industry.startsWith("__custom__")) e.custom_industry = "Specify your industry.";
      if (!f.employee_range) e.employee_range = "Select an employee range.";
      if (!f.headquarters_country) e.headquarters_country = "Select the headquarters country.";
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const next = () => { if (validateStep(step)) setStep((s) => Math.min(s + 1, STEPS.length - 1)); };
  const back = () => setStep((s) => Math.max(s - 1, 0));

  const submit = async () => {
    if (!validateStep(0)) { setStep(0); return; }
    setBusy(true); setApiError(null);
    const payload = {
      name: f.name.trim(),
      legal_name: f.legal_name.trim() || undefined,
      website: f.website.trim() || undefined,
      company_type: f.company_type || undefined,
      industry: resolvedIndustry || undefined,
      employee_range: f.employee_range || undefined,
      headquarters_country: f.headquarters_country,
      operating_countries: f.operating_countries,
      ai_deployment_countries: f.ai_deployment_countries,
      customer_countries: f.customer_countries,
      uses_ai: f.uses_ai, uses_genai: f.uses_genai, uses_agents: f.uses_agents,
      is_financial_institution: f.is_financial_institution,
      is_critical_infrastructure: f.is_critical_infrastructure,
      is_software_vendor: f.is_software_vendor,
      eu_market_exposure: euExposed,
      processes_personal_data: f.processes_personal_data,
      governance_contacts: {
        governance_lead: f.governance_lead, compliance_lead: f.compliance_lead,
        security_lead: f.security_lead, privacy_dpo: f.privacy_dpo, legal_contact: f.legal_contact,
      },
    };
    try {
      if (mode === "create") {
        await api.createCompany(payload as any);
      } else {
        await api.updateCurrentCompany(payload as any);
      }
      onDone(f.name.trim());
    } catch (e: any) {
      setApiError(e?.message?.replace(/^API .*?: /, "") || "Could not save the company. Please check the fields and try again.");
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] bg-[#070A11] flex flex-col">
      {/* sticky header */}
      <header className="flex-shrink-0 border-b border-white/10 px-6 py-4 flex items-center gap-4">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center">
          <Building2 className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1">
          <h1 className="text-sm font-bold text-white">
            {mode === "create" ? "Create your company" : "Edit company"}
          </h1>
          <p className="text-[11px] text-slate-400">Step {step + 1} of {STEPS.length} · {STEPS[step]}</p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white" aria-label="Close">
          <X className="w-5 h-5" />
        </button>
      </header>

      <div className="flex-shrink-0 px-6 pt-3">
        <div className="flex gap-1.5">
          {STEPS.map((s, i) => (
            <div key={s} className={`h-1 flex-1 rounded-full transition-colors ${i <= step ? "bg-sky-500" : "bg-white/10"}`} />
          ))}
        </div>
      </div>

      {/* scrollable body */}
      <main className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-xl mx-auto space-y-5">
          {step === 0 && (
            <>
              <Field label="Company name" htmlFor="c-name" required error={errors.name}
                help="The name shown across the app and on reports.">
                <TextInput id="c-name" value={f.name} onChange={(v) => set({ name: v })} error={errors.name}
                  placeholder="Nova Financial Technologies Ltd" maxLength={200} autoFocus />
              </Field>

              <Field label="Legal name" htmlFor="c-legal" optional error={errors.legal_name}
                help="Registered legal entity name, if different from the company display name.">
                <TextInput id="c-legal" value={f.legal_name} onChange={(v) => set({ legal_name: v })} error={errors.legal_name}
                  placeholder="Nova Financial Technologies Private Limited" maxLength={255} />
              </Field>

              <Field label="Website" htmlFor="c-web" optional error={errors.website}>
                <TextInput id="c-web" value={f.website} onChange={(v) => set({ website: v })} error={errors.website}
                  placeholder="https://nova.example" inputMode="url" />
              </Field>

              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Company type" htmlFor="c-type" optional
                  help="Not the same as industry.">
                  <SearchableSelect id="c-type" value={f.company_type} onChange={(v) => set({ company_type: v })}
                    options={COMPANY_TYPES} placeholder="Select type" />
                </Field>
                <Field label="Employee range" htmlFor="c-emp" required error={errors.employee_range}>
                  <SearchableSelect id="c-emp" value={f.employee_range} onChange={(v) => set({ employee_range: v })}
                    options={EMPLOYEE_RANGES.map((r) => ({ value: r.value, label: r.label }))}
                    placeholder="Select range" error={errors.employee_range} />
                </Field>
              </div>

              <Field label="Primary industry" htmlFor="c-ind" required error={errors.industry}
                help="Closest primary business sector. Choose “Other” to enter your own.">
                <SearchableSelect id="c-ind" value={f.industry} onChange={(v) => set({ industry: v })}
                  options={industryOptions} placeholder="Search industries…" error={errors.industry}
                  allowCustom customLabel={(q) => `Use "${q}" as a custom industry`} />
              </Field>
              {(f.industry === "other") && (
                <Field label="Specify industry" htmlFor="c-cind" required error={errors.custom_industry}>
                  <TextInput id="c-cind" value={f.custom_industry} onChange={(v) => set({ custom_industry: v })} error={errors.custom_industry}
                    placeholder="e.g. Maritime logistics" />
                </Field>
              )}

              <Field label="Headquarters country" htmlFor="c-hq" required error={errors.headquarters_country}
                help="Country where the primary legal entity is headquartered.">
                <SearchableSelect id="c-hq" value={f.headquarters_country} onChange={(v) => set({ headquarters_country: v })}
                  options={COUNTRIES.map((c) => ({ value: c.code, label: `${c.name} (${c.code})` }))}
                  placeholder="Search countries…" error={errors.headquarters_country} />
              </Field>
            </>
          )}

          {step === 1 && (
            <>
              <Field label="Countries of operation" htmlFor="c-ops" optional
                help="Everywhere the company has a legal presence, staff, or active business.">
                <MultiCountrySelect id="c-ops" value={f.operating_countries} onChange={(v) => set({ operating_countries: v })}
                  options={COUNTRIES} />
              </Field>
              <Field label="Countries where AI is deployed" htmlFor="c-dep" optional
                help="Where your AI systems actually run or are made available.">
                <MultiCountrySelect id="c-dep" value={f.ai_deployment_countries} onChange={(v) => set({ ai_deployment_countries: v })}
                  options={COUNTRIES} />
              </Field>
              <Field label="Countries where customers / users are located" htmlFor="c-cust" optional
                help="Used to work out which privacy and AI regimes apply.">
                <MultiCountrySelect id="c-cust" value={f.customer_countries} onChange={(v) => set({ customer_countries: v })}
                  options={COUNTRIES} />
              </Field>
              {euExposed && (
                <div className="text-[11px] text-sky-200 bg-sky-500/10 border border-sky-500/20 rounded-lg px-3 py-2">
                  EU / EEA exposure detected — EU AI Act and GDPR are likely to be in scope. The applicability engine will confirm per system.
                </div>
              )}
            </>
          )}

          {step === 2 && (
            <div className="space-y-2">
              <p className="text-[11px] text-slate-500 mb-1">
                These help recommend frameworks automatically — you don’t need to know DORA, NIS2 or CRA by name.
              </p>
              <Toggle label="We build or use AI" checked={f.uses_ai} onChange={(v) => set({ uses_ai: v })} />
              <Toggle label="We use generative AI / LLMs" checked={f.uses_genai} onChange={(v) => set({ uses_genai: v })} />
              <Toggle label="We build AI agents (tool-using / autonomous)" checked={f.uses_agents} onChange={(v) => set({ uses_agents: v })} />
              <Toggle label="We process personal data" checked={f.processes_personal_data} onChange={(v) => set({ processes_personal_data: v })} />
              <Toggle label="We are a financial institution" help="Bank, insurer, payment/e-money institution, investment firm, crypto-asset service provider." checked={f.is_financial_institution} onChange={(v) => set({ is_financial_institution: v })} />
              <Toggle label="We operate critical infrastructure" checked={f.is_critical_infrastructure} onChange={(v) => set({ is_critical_infrastructure: v })} />
              <Toggle label="We sell software or a digital / connected product" checked={f.is_software_vendor} onChange={(v) => set({ is_software_vendor: v })} />
              <Toggle label="Our products / services are offered in the EU" checked={f.eu_market_exposure} onChange={(v) => set({ eu_market_exposure: v })} />
            </div>
          )}

          {step === 3 && (
            <>
              <p className="text-[11px] text-slate-500">All optional — you can assign these later. Enter a name or email.</p>
              {([
                ["governance_lead", "AI Governance Lead"],
                ["compliance_lead", "Compliance Lead"],
                ["security_lead", "Security / CISO"],
                ["privacy_dpo", "Privacy / DPO"],
                ["legal_contact", "Legal contact"],
              ] as [keyof CompanyFormValue, string][]).map(([k, label]) => (
                <Field key={k} label={label} htmlFor={`c-${k}`} optional>
                  <TextInput id={`c-${k}`} value={f[k] as string} onChange={(v) => set({ [k]: v } as any)} placeholder="Name or email" />
                </Field>
              ))}
            </>
          )}

          {step === 4 && (
            <div className="space-y-3 text-[12px]">
              <h2 className="text-sm font-bold text-white">Review</h2>
              {[
                ["Company name", f.name],
                ["Legal name", f.legal_name || "—"],
                ["Website", f.website || "—"],
                ["Company type", COMPANY_TYPES.find((t) => t.value === f.company_type)?.label || "—"],
                ["Industry", industryLabel(resolvedIndustry) || resolvedIndustry || "—"],
                ["Employees", employeeRangeLabel(f.employee_range)],
                ["Headquarters", countryName(f.headquarters_country) || "—"],
                ["Operating in", f.operating_countries.map(countryName).join(", ") || "—"],
                ["AI deployed in", f.ai_deployment_countries.map(countryName).join(", ") || "—"],
                ["Customers in", f.customer_countries.map(countryName).join(", ") || "—"],
                ["EU exposure", euExposed ? "Yes" : "No"],
              ].map(([k, v]) => (
                <div key={k as string} className="flex justify-between gap-4 border-b border-white/5 pb-1.5">
                  <span className="text-slate-500">{k}</span>
                  <span className="text-slate-200 text-right">{v as string}</span>
                </div>
              ))}
              {apiError && (
                <div className="text-[11px] text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">{apiError}</div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* sticky footer */}
      <footer className="flex-shrink-0 border-t border-white/10 px-6 py-4 flex items-center justify-between">
        <button
          onClick={step === 0 ? onClose : back}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] text-slate-400 hover:text-slate-200"
        >
          <ChevronLeft className="w-4 h-4" /> {step === 0 ? "Cancel" : "Back"}
        </button>
        {step < STEPS.length - 1 ? (
          <button onClick={next}
            className="flex items-center gap-1.5 px-5 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 text-[12px] font-bold">
            Continue <ChevronRight className="w-4 h-4" />
          </button>
        ) : (
          <button onClick={submit} disabled={busy}
            className="flex items-center gap-1.5 px-5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-[12px] font-bold disabled:opacity-50">
            {busy ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
            {mode === "create" ? "Create company" : "Save changes"}
          </button>
        )}
      </footer>
    </div>
  );
}
