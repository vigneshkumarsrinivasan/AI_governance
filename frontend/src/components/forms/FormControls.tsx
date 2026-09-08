"use client";

/**
 * Standardised form primitives (spec sections 4, 5, 17, 27-33).
 * Every field: visible label, required/optional indicator, optional help text,
 * inline error, real <label htmlFor> association. Selects are searchable,
 * keyboard-navigable, portal-free but overflow-safe (open upward when needed),
 * and support custom values where allowed.
 */

import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import { ChevronDown, X, Check, Search } from "lucide-react";

const labelCls = "block text-[12px] font-medium text-slate-200 mb-1.5";
const optionalCls = "ml-1.5 text-[10px] font-normal text-slate-500 uppercase tracking-wide";
const requiredCls = "ml-0.5 text-rose-400";
const helpCls = "mt-1 text-[11px] text-slate-500 leading-snug";
const errCls = "mt-1 text-[11px] text-rose-400";
const inputBase =
  "w-full px-3 py-2.5 rounded-lg bg-white/[0.04] border text-[13px] text-slate-100 placeholder-slate-500 " +
  "focus:outline-none focus:ring-2 focus:ring-sky-500/40 focus:border-sky-500/60 transition-colors";

export function Field({
  label, htmlFor, required, optional, help, error, children,
}: {
  label: string; htmlFor?: string; required?: boolean; optional?: boolean;
  help?: string; error?: string | null; children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className={labelCls}>
        {label}
        {required && <span className={requiredCls}>*</span>}
        {optional && <span className={optionalCls}>Optional</span>}
      </label>
      {children}
      {help && !error && <p className={helpCls}>{help}</p>}
      {error && <p className={errCls}>{error}</p>}
    </div>
  );
}

export function TextInput({
  value, onChange, error, ...rest
}: { value: string; onChange: (v: string) => void; error?: string | null } &
  Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange">) {
  return (
    <input
      {...rest}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`${inputBase} ${error ? "border-rose-500/60" : "border-white/10 hover:border-white/20"}`}
    />
  );
}

export interface Opt { value: string; label: string; }

export function SearchableSelect({
  id, value, onChange, options, placeholder = "Select…", error,
  allowCustom = false, customLabel = (q: string) => `Use "${q}"`,
  emptyText = "No matches",
}: {
  id?: string;
  value: string;
  onChange: (v: string) => void;
  options: Opt[];
  placeholder?: string;
  error?: string | null;
  allowCustom?: boolean;
  customLabel?: (q: string) => string;
  emptyText?: string;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [drop, setDrop] = useState<"down" | "up">("down");
  const [active, setActive] = useState(0);
  const btnRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const genId = useId();
  const inputId = id || genId;

  const selected = options.find((o) => o.value === value);
  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return options;
    return options.filter((o) => o.label.toLowerCase().includes(s) || o.value.toLowerCase().includes(s));
  }, [q, options]);
  const showCustom = allowCustom && q.trim().length > 0 &&
    !filtered.some((o) => o.label.toLowerCase() === q.trim().toLowerCase());

  useEffect(() => {
    if (!open) return;
    const r = btnRef.current?.getBoundingClientRect();
    if (r) setDrop(window.innerHeight - r.bottom < 280 && r.top > 280 ? "up" : "down");
    setActive(0);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!btnRef.current?.parentElement?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const choose = (v: string) => { onChange(v); setOpen(false); setQ(""); };
  const rows = showCustom ? [...filtered, { value: `__custom__${q.trim()}`, label: customLabel(q.trim()) }] : filtered;

  return (
    <div className="relative">
      <button
        ref={btnRef}
        id={inputId}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" || e.key === "Enter") { e.preventDefault(); setOpen(true); }
        }}
        className={`${inputBase} flex items-center justify-between text-left ${
          error ? "border-rose-500/60" : "border-white/10 hover:border-white/20"
        }`}
      >
        <span className={selected ? "text-slate-100" : "text-slate-500"}>
          {selected ? selected.label : (value && value.startsWith("__custom__") ? value.replace("__custom__", "") : placeholder)}
        </span>
        <ChevronDown className="w-4 h-4 text-slate-500 flex-shrink-0" />
      </button>

      {open && (
        <div
          className={`absolute left-0 right-0 z-[80] rounded-lg bg-[#0B0F1A] border border-white/15 shadow-2xl overflow-hidden ${
            drop === "up" ? "bottom-full mb-1" : "top-full mt-1"
          }`}
        >
          <div className="flex items-center gap-2 px-2.5 py-2 border-b border-white/10">
            <Search className="w-3.5 h-3.5 text-slate-500" />
            <input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, rows.length - 1)); }
                else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
                else if (e.key === "Enter") {
                  e.preventDefault();
                  const r = rows[active];
                  if (r) choose(r.value.startsWith("__custom__") ? r.value : r.value);
                } else if (e.key === "Escape") { setOpen(false); }
              }}
              placeholder="Type to search…"
              className="flex-1 bg-transparent text-[12px] text-slate-100 placeholder-slate-500 focus:outline-none"
            />
          </div>
          <div ref={listRef} className="max-h-56 overflow-y-auto py-1">
            {rows.length === 0 && <div className="px-3 py-2 text-[11px] text-slate-500">{emptyText}</div>}
            {rows.map((o, i) => (
              <button
                key={o.value}
                type="button"
                onMouseEnter={() => setActive(i)}
                onClick={() => choose(o.value)}
                className={`w-full flex items-center justify-between px-3 py-2 text-left text-[12px] ${
                  i === active ? "bg-sky-500/15 text-sky-100" : "text-slate-200 hover:bg-white/5"
                }`}
              >
                <span>{o.label}</span>
                {o.value === value && <Check className="w-3.5 h-3.5 text-sky-400" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/** Multi-select of countries with chips + search. Value is an array of ISO codes. */
export function MultiCountrySelect({
  id, value, onChange, options, error, placeholder = "Add a country…",
}: {
  id?: string;
  value: string[];
  onChange: (v: string[]) => void;
  options: { code: string; name: string }[];
  error?: string | null;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const wrapRef = useRef<HTMLDivElement>(null);
  const genId = useId();

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (!wrapRef.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    return options
      .filter((o) => !value.includes(o.code))
      .filter((o) => !s || o.name.toLowerCase().includes(s) || o.code.toLowerCase().includes(s))
      .slice(0, 60);
  }, [q, options, value]);

  const add = (code: string) => { onChange([...value, code]); setQ(""); };
  const remove = (code: string) => onChange(value.filter((c) => c !== code));

  return (
    <div className="relative" ref={wrapRef}>
      <div
        className={`${inputBase} min-h-[44px] flex flex-wrap items-center gap-1.5 ${error ? "border-rose-500/60" : "border-white/10 hover:border-white/20"}`}
        onClick={() => setOpen(true)}
      >
        {value.map((code) => {
          const c = options.find((o) => o.code === code);
          return (
            <span key={code} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-sky-500/15 border border-sky-500/30 text-[11px] text-sky-100">
              {c?.name || code}
              <button type="button" onClick={(e) => { e.stopPropagation(); remove(code); }} className="text-sky-300 hover:text-white">
                <X className="w-3 h-3" />
              </button>
            </span>
          );
        })}
        <input
          id={id || genId}
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Backspace" && !q && value.length) remove(value[value.length - 1]);
            if (e.key === "Enter" && filtered[0]) { e.preventDefault(); add(filtered[0].code); }
            if (e.key === "Escape") setOpen(false);
          }}
          placeholder={value.length === 0 ? placeholder : ""}
          className="flex-1 min-w-[120px] bg-transparent text-[12px] text-slate-100 placeholder-slate-500 focus:outline-none py-1"
        />
      </div>
      {open && filtered.length > 0 && (
        <div className="absolute left-0 right-0 z-[80] mt-1 rounded-lg bg-[#0B0F1A] border border-white/15 shadow-2xl max-h-56 overflow-y-auto py-1">
          {filtered.map((o) => (
            <button key={o.code} type="button" onClick={() => add(o.code)}
              className="w-full flex items-center justify-between px-3 py-1.5 text-left text-[12px] text-slate-200 hover:bg-sky-500/15">
              <span>{o.name}</span>
              <span className="text-[10px] text-slate-500">{o.code}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function Toggle({
  id, label, help, checked, onChange,
}: { id?: string; label: string; help?: string; checked: boolean; onChange: (v: boolean) => void }) {
  const genId = useId();
  return (
    <button
      id={id || genId}
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`w-full flex items-start gap-3 p-3 rounded-lg border text-left transition-colors focus:outline-none focus:ring-2 focus:ring-sky-500/40 ${
        checked ? "bg-sky-500/10 border-sky-500/40" : "bg-white/[0.03] border-white/10 hover:border-white/20"
      }`}
    >
      <span className={`mt-0.5 w-4 h-4 rounded flex items-center justify-center flex-shrink-0 border ${checked ? "bg-sky-500 border-sky-500" : "border-white/30"}`}>
        {checked && <Check className="w-3 h-3 text-slate-950" />}
      </span>
      <span>
        <span className="block text-[12px] font-medium text-slate-200">{label}</span>
        {help && <span className="block text-[11px] text-slate-500 mt-0.5">{help}</span>}
      </span>
    </button>
  );
}
