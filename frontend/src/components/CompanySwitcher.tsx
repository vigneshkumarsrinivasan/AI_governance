"use client";

/**
 * Global company selector + Add/Edit company (spec sections 2, 3, 19, 20, 21, 81, 82).
 * Rendered in the header of both the advanced and simple experiences. Switching
 * calls the backend, swaps the auth token, then triggers a full data reload.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Building, ChevronDown, Plus, Check, RefreshCw, Pencil, Search } from "lucide-react";
import * as api from "@/lib/api";
import CompanyWizard, { CompanyFormValue } from "@/components/company/CompanyWizard";

export default function CompanySwitcher({
  activeName,
  onSwitched,
}: {
  activeName?: string | null;
  onSwitched: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [companies, setCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [wizard, setWizard] = useState<null | { mode: "create" | "edit"; initial?: Partial<CompanyFormValue> }>(null);
  const [q, setQ] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.getMyCompanies();
      setCompanies(r.companies || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load, activeName]);

  const doSwitch = async (orgId: string) => {
    setBusy(orgId);
    try {
      await api.switchCompany(orgId);
      await api.refreshCurrentUser();
      setOpen(false);
      onSwitched();
    } catch (e: any) {
      alert("Could not switch company: " + (e?.message || e));
    } finally { setBusy(null); }
  };

  const openEdit = async () => {
    setOpen(false);
    try {
      const c = await api.getCurrentCompany();
      setWizard({
        mode: "edit",
        initial: {
          name: c.name || "", legal_name: c.legal_name || "", website: c.website || "",
          company_type: c.company_type || "", industry: c.industry || "",
          employee_range: c.employee_range || "", headquarters_country: c.headquarters_country || "",
          operating_countries: c.countries_operating || [], ai_deployment_countries: c.ai_deployment_countries || [],
          customer_countries: c.customer_countries || [],
          is_financial_institution: !!c.is_financial_institution, is_critical_infrastructure: !!c.is_critical_infrastructure,
          is_software_vendor: !!c.is_software_vendor, eu_market_exposure: !!c.eu_market_exposure,
          processes_personal_data: c.processes_personal_data ?? true,
          governance_lead: c.governance_contacts?.governance_lead || "",
          compliance_lead: c.governance_contacts?.compliance_lead || "",
          security_lead: c.governance_contacts?.security_lead || "",
          privacy_dpo: c.governance_contacts?.privacy_dpo || "",
          legal_contact: c.governance_contacts?.legal_contact || "",
        },
      });
    } catch { setWizard({ mode: "edit" }); }
  };

  const active = companies.find(c => c.is_active);
  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    return s ? companies.filter(c => c.name.toLowerCase().includes(s)) : companies;
  }, [q, companies]);
  const manyCompanies = companies.length > 6;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:border-sky-500/40 text-xs font-semibold text-slate-200 transition-colors max-w-[280px] focus:outline-none focus:ring-2 focus:ring-sky-500/40"
        title="Switch company"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <Building className="w-3.5 h-3.5 text-sky-400 flex-shrink-0" />
        <span className="truncate">{activeName || active?.name || "Select company"}</span>
        {(active?.is_demo ?? (activeName && /acme/i.test(activeName))) && (
          <span className="text-[9px] px-1 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 flex-shrink-0">DEMO</span>
        )}
        <ChevronDown className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute left-0 mt-1.5 w-72 rounded-xl bg-[#0B0F1A] border border-white/10 shadow-2xl z-50 p-1.5">
            <div className="px-2 py-1 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Your companies</div>
            {manyCompanies && (
              <div className="flex items-center gap-2 px-2 py-1.5 mb-1 border-b border-white/10">
                <Search className="w-3 h-3 text-slate-500" />
                <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search…"
                  className="flex-1 bg-transparent text-[11px] text-slate-200 focus:outline-none placeholder-slate-500" />
              </div>
            )}
            {loading && <div className="px-2 py-2 text-[11px] text-slate-500 flex items-center gap-2"><RefreshCw className="w-3 h-3 animate-spin" /> Loading…</div>}
            <div className="max-h-64 overflow-y-auto">
              {!loading && filtered.map(c => (
                <button
                  key={c.organization_id}
                  onClick={() => !c.is_active && doSwitch(c.organization_id)}
                  disabled={busy === c.organization_id}
                  className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left text-xs transition-colors ${
                    c.is_active ? "bg-sky-500/10 text-sky-200" : "hover:bg-white/5 text-slate-200"
                  }`}
                >
                  {c.is_active ? <Check className="w-3.5 h-3.5 text-sky-400 flex-shrink-0" /> : <span className="w-3.5 flex-shrink-0" />}
                  <span className="flex-1 min-w-0">
                    <span className="block truncate font-medium">{c.name}</span>
                    <span className="block text-[10px] text-slate-500">{c.role}{c.is_demo ? " · demo tenant" : ""}</span>
                  </span>
                  {busy === c.organization_id && <RefreshCw className="w-3 h-3 animate-spin text-slate-400" />}
                </button>
              ))}
            </div>
            <div className="border-t border-white/10 my-1" />
            <button
              onClick={() => { setOpen(false); setWizard({ mode: "create" }); }}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left text-xs text-emerald-300 hover:bg-emerald-500/10 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" /> Add company
            </button>
            {active && !active.is_demo && (
              <button
                onClick={openEdit}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left text-xs text-slate-300 hover:bg-white/5 transition-colors"
              >
                <Pencil className="w-3.5 h-3.5" /> Edit {active.name}
              </button>
            )}
          </div>
        </>
      )}

      {wizard && typeof document !== "undefined" && createPortal(
        <CompanyWizard
          mode={wizard.mode}
          initial={wizard.initial}
          onClose={() => setWizard(null)}
          onDone={async () => {
            setWizard(null);
            await api.refreshCurrentUser();
            await load();
            onSwitched();
          }}
        />,
        document.body
      )}
    </div>
  );
}
