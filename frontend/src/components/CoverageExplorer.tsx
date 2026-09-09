"use client";

/**
 * Framework Coverage & Mapping Review (MOAT 1 / 2 / 3).
 *
 * "Govern once. Prove everywhere." - shows, per real regulatory requirement,
 * whether a reviewed Unified Control covers it in THIS tenant, and why. AI-
 * proposed mappings are shown as a review queue and never count until a human
 * promotes them.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ShieldCheck, ShieldAlert, ShieldX, HelpCircle, RefreshCw, ChevronRight,
  CheckCircle2, XCircle, Sparkles, Scale,
} from "lucide-react";
import * as api from "@/lib/api";

const STATUS_META: Record<string, { icon: any; cls: string; label: string }> = {
  COVERED: { icon: ShieldCheck, cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30", label: "Covered" },
  PARTIALLY_COVERED: { icon: ShieldAlert, cls: "text-amber-400 bg-amber-500/10 border-amber-500/30", label: "Partial" },
  NOT_COVERED: { icon: ShieldX, cls: "text-rose-400 bg-rose-500/10 border-rose-500/30", label: "Not covered" },
  NOT_MAPPED: { icon: HelpCircle, cls: "text-slate-400 bg-slate-500/10 border-slate-500/30", label: "Not mapped" },
};

function Bar({ pct, className = "" }: { pct: number; className?: string }) {
  return (
    <div className={`h-2 rounded-full bg-white/10 overflow-hidden ${className}`}>
      <div className="h-full bg-gradient-to-r from-sky-500 to-emerald-500" style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
    </div>
  );
}

export default function CoverageExplorer({ canReview }: { canReview: boolean }) {
  const [summary, setSummary] = useState<any>(null);
  const [framework, setFramework] = useState<string | null>(null);
  const [coverage, setCoverage] = useState<any>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [queue, setQueue] = useState<any[]>([]);
  const [stateCounts, setStateCounts] = useState<Record<string, number>>({});
  const [msg, setMsg] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    try {
      const s = await api.getCoverageSummary();
      setSummary(s);
      if (!framework && s.frameworks?.length) {
        const firstReal = s.frameworks.find((f: any) => f.total_requirements > 0) || s.frameworks[0];
        setFramework(firstReal?.framework_key ?? null);
      }
    } catch (e: any) { setMsg(e.message); }
  }, [framework]);

  const loadQueue = useCallback(async () => {
    try {
      const r = await api.listControlMappings({ state: "AI_SUGGESTED", limit: 100 });
      setQueue(r.mappings || []);
      setStateCounts(r.state_counts || {});
    } catch (e: any) { setMsg(e.message); }
  }, []);

  const loadCoverage = useCallback(async (fk: string) => {
    setLoading(true);
    try {
      setCoverage(await api.getFrameworkCoverage(fk, { limit: 500, status: statusFilter || undefined }));
    } catch (e: any) { setMsg(e.message); } finally { setLoading(false); }
  }, [statusFilter]);

  useEffect(() => { loadSummary(); loadQueue(); }, [loadSummary, loadQueue]);
  useEffect(() => { if (framework) loadCoverage(framework); }, [framework, loadCoverage]);

  const runProposer = async () => {
    setBusy(true); setMsg(null);
    try {
      const r = await api.proposeControlMappings();
      setMsg(
        `Expert-curated: ${r.expert_curated?.created ?? 0} loaded · crosswalk: ${r.crosswalk_seed?.created ?? 0} · ` +
        `AI candidates: ${r.ai_proposer?.created ?? 0} (AI_SUGGESTED - pending review).`
      );
      await Promise.all([loadSummary(), loadQueue(), framework ? loadCoverage(framework) : Promise.resolve()]);
    } catch (e: any) { setMsg(e.message); } finally { setBusy(false); }
  };

  const review = async (id: string, decision: string) => {
    setBusy(true);
    try {
      await api.reviewControlMapping(id, { decision, note: `${decision} via coverage console` });
      await Promise.all([loadQueue(), loadSummary(), framework ? loadCoverage(framework) : Promise.resolve()]);
    } catch (e: any) { setMsg(e.message); } finally { setBusy(false); }
  };

  const reqs = useMemo(() => coverage?.requirements ?? [], [coverage]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <Scale className="w-5 h-5 text-sky-400" /> Framework Coverage
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Per source-traceable requirement: is a <span className="text-slate-200">reviewed</span> Unified Control
            actually implemented, effective and freshly evidenced in this company? A mapping alone never counts.
          </p>
        </div>
        {canReview && (
          <button onClick={runProposer} disabled={busy}
            className="text-sm px-3 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white flex items-center gap-2 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${busy ? "animate-spin" : ""}`} /> Refresh mappings
          </button>
        )}
      </div>

      {msg && <div className="text-xs px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-slate-300">{msg}</div>}

      {/* Overall readiness */}
      {summary && (
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-slate-400">Overall governance readiness (applicable frameworks)</span>
            <span className="text-2xl font-semibold text-white">{summary.overall_readiness_pct}%</span>
          </div>
          <Bar pct={summary.overall_readiness_pct} className="mt-2" />
          {summary.explanation?.length > 0 && (
            <ul className="mt-3 text-xs text-slate-400 list-disc pl-4 space-y-0.5">
              {summary.explanation.map((e: string, i: number) => <li key={i}>{e}</li>)}
            </ul>
          )}
        </div>
      )}

      <div className="grid lg:grid-cols-[280px_1fr] gap-6">
        {/* Framework list */}
        <div className="space-y-1">
          {(summary?.frameworks ?? []).map((f: any) => (
            <button key={f.framework_key} onClick={() => setFramework(f.framework_key)}
              className={`w-full text-left px-3 py-2 rounded-lg border transition ${
                framework === f.framework_key ? "border-sky-500/50 bg-sky-500/10" : "border-white/10 hover:bg-white/5"}`}>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-200 truncate">{f.framework_key}</span>
                <span className="text-xs text-slate-400">{f.readiness_pct}%</span>
              </div>
              <Bar pct={f.readiness_pct} className="mt-1.5" />
              <div className="text-[11px] text-slate-500 mt-1">
                {f.covered}/{f.mapped_requirements} covered · {f.candidate_mappings_pending_review} candidates
              </div>
            </button>
          ))}
        </div>

        {/* Requirement detail */}
        <div className="min-w-0">
          {coverage && !coverage.available && (
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6 text-sm text-slate-400">
              {coverage.reason || "This framework is not ingested yet."}
            </div>
          )}
          {coverage?.available && (
            <>
              <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <div className="text-sm text-slate-300">
                  <span className="text-white font-medium">{coverage.framework_name}</span>
                  <span className="text-slate-500"> · {coverage.version_label} · {coverage.summary.total_requirements} requirements</span>
                </div>
                <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
                  className="text-xs bg-slate-800 border border-white/10 rounded-lg px-2 py-1.5 text-slate-200">
                  <option value="">All statuses</option>
                  {Object.keys(STATUS_META).map((s) => <option key={s} value={s}>{STATUS_META[s].label}</option>)}
                </select>
              </div>

              <div className="grid grid-cols-4 gap-2 mb-4 text-center">
                {(["COVERED", "PARTIALLY_COVERED", "NOT_COVERED", "NOT_MAPPED"] as const).map((s) => {
                  const k = s === "COVERED" ? "covered" : s === "PARTIALLY_COVERED" ? "partially_covered"
                    : s === "NOT_COVERED" ? "not_covered" : "not_mapped";
                  const M = STATUS_META[s];
                  return (
                    <div key={s} className={`rounded-lg border p-2 ${M.cls}`}>
                      <div className="text-lg font-semibold">{coverage.summary[k]}</div>
                      <div className="text-[10px] uppercase tracking-wide opacity-80">{M.label}</div>
                    </div>
                  );
                })}
              </div>

              {loading ? (
                <div className="text-sm text-slate-400">Loading…</div>
              ) : (
                <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
                  {reqs.map((r: any) => {
                    const M = STATUS_META[r.status] || STATUS_META.NOT_MAPPED;
                    const Icon = M.icon;
                    return (
                      <div key={r.requirement_key} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                        <div className="flex items-start gap-3">
                          <span className={`shrink-0 inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded border ${M.cls}`}>
                            <Icon className="w-3.5 h-3.5" /> {M.label}
                          </span>
                          <div className="min-w-0">
                            <div className="text-sm text-slate-200">
                              <span className="text-slate-400">{r.source_reference}</span> — {r.title}
                            </div>
                            <div className="text-xs text-slate-400 mt-1">{r.explanation}</div>
                            <div className="flex gap-3 mt-1 text-[11px] text-slate-500">
                              {r.via_controls?.length > 0 && <span>via {r.via_controls.join(", ")}</span>}
                              {r.candidate_controls?.length > 0 && (
                                <span className="text-sky-400/80 flex items-center gap-1">
                                  <Sparkles className="w-3 h-3" /> candidate: {r.candidate_controls.join(", ")}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Mapping review queue */}
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-sky-400" /> AI mapping review queue
          </h3>
          <div className="text-xs text-slate-400">
            {Object.entries(stateCounts).map(([k, v]) => <span key={k} className="ml-2">{k}: {v}</span>)}
          </div>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          AI-proposed candidates are <span className="text-slate-300">never authoritative</span>. Promote to
          <span className="text-slate-300"> Expert reviewed</span> only after checking the requirement text against the source.
        </p>
        {!canReview ? (
          <div className="text-xs text-slate-500">You do not have the mapping-review role.</div>
        ) : queue.length === 0 ? (
          <div className="text-xs text-slate-500">Nothing pending review.</div>
        ) : (
          <div className="space-y-2 max-h-[40vh] overflow-y-auto pr-1">
            {queue.map((m: any) => (
              <div key={m.id} className="rounded-lg border border-white/10 bg-white/[0.02] p-3 flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-slate-200">
                    {m.control_code} <ChevronRight className="w-3 h-3 inline text-slate-500" />{" "}
                    <span className="text-slate-400">{m.framework} · {m.requirement_key}</span>
                    <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-slate-300">{m.mapping_type} · {(m.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">{m.rationale}</div>
                </div>
                <div className="flex gap-1 shrink-0">
                  <button onClick={() => review(m.id, "EXPERT_REVIEWED")} disabled={busy}
                    className="text-[11px] px-2 py-1 rounded bg-emerald-600/80 hover:bg-emerald-500 text-white flex items-center gap-1 disabled:opacity-50">
                    <CheckCircle2 className="w-3 h-3" /> Approve
                  </button>
                  <button onClick={() => review(m.id, "REJECTED")} disabled={busy}
                    className="text-[11px] px-2 py-1 rounded bg-rose-600/70 hover:bg-rose-500 text-white flex items-center gap-1 disabled:opacity-50">
                    <XCircle className="w-3 h-3" /> Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
