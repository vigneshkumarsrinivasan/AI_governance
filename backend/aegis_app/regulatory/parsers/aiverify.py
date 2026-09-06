"""Parser for the AI Verify Testing Framework process-checklist configuration
(stock-plugins/aiverify.stock.process-checklist/inputs/config_*.ts).

Each config file is `export const config = { ...valid JSON... };`. We bundle the
12 principle configs and rebuild:

    AI Verify Testing Framework
      -> Governance principle (Fairness, Robustness, Transparency, ...)
        -> Testable criteria
          -> Process check (pid 7.1.1, process, metric, threshold, processChecks)

Licence: Apache-2.0 (aiverify-foundation/aiverify).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from aegis_app.regulatory.parsers.base import ParsedFramework, ParsedNode, ParsedRequirement

_ANCHOR = "https://aiverifyfoundation.sg/what-is-ai-verify/"
_CONFIG_RE = re.compile(r"export\s+const\s+config\s*=\s*(\{.*\})\s*;?\s*$", re.S)


def _load_config(ts_source: str) -> dict:
    m = _CONFIG_RE.search(ts_source.strip())
    payload = m.group(1) if m else ts_source
    try:
        return json.loads(re.sub(r",(\s*[}\]])", r"\1", payload))
    except json.JSONDecodeError:
        import json5  # JS object literal: unquoted keys, trailing commas
        return json5.loads(payload)


def parse(raw: bytes, manifest_entry: Dict[str, Any]) -> ParsedFramework:
    bundle = json.loads(raw.decode("utf-8"))
    files: Dict[str, str] = bundle["files"]
    repo = bundle.get("repo", "aiverify-foundation/aiverify")
    ref = bundle.get("ref", "main")

    pf = ParsedFramework(
        framework_key="singapore_ai_verify",
        version_label=bundle.get("version", manifest_entry["version_label"]),
        framework_name=manifest_entry["framework_name"],
        framework_type=manifest_entry["framework_type"],
        publication_date=manifest_entry.get("publication_date"),
        effective_date=manifest_entry.get("effective_date"),
    )
    root_id = "AI-VERIFY-TF"
    pf.nodes.append(ParsedNode(official_id=root_id, node_type="framework",
                               label="AI Verify Testing Framework (governance process checklist)",
                               source_anchor_url=_ANCHOR,
                               platform_summary=f"Source: {repo}@{ref}, stock process-checklist plugin."))

    n_prin = n_crit = n_proc = 0
    seen: set = set()
    for fname in sorted(files):
        try:
            cfg = _load_config(files[fname])
        except Exception as e:  # noqa: BLE001
            pf.parser_notes.append(f"WARNING: could not parse {fname}: {e}")
            continue
        principle = (cfg.get("principle") or fname).strip()
        pid_node = f"Principle: {principle}"
        if pid_node in seen:
            continue
        seen.add(pid_node)
        n_prin += 1
        pf.nodes.append(ParsedNode(official_id=pid_node, node_type="governance_principle",
                                   label=principle, parent_official_id=root_id, ordinal=n_prin,
                                   source_text=(cfg.get("description") or "").strip(),
                                   source_anchor_url=_ANCHOR))
        for section in cfg.get("sections", []):
            for crit in section.get("checklist", []):
                crit_text = (crit.get("testableCriteria") or "").strip()
                if not crit_text:
                    continue
                n_crit += 1
                crit_id = f"{principle} / TC{n_crit}"
                pf.nodes.append(ParsedNode(official_id=crit_id, node_type="process_check",
                                           label=crit_text[:140], parent_official_id=pid_node,
                                           ordinal=n_crit, source_text=crit_text,
                                           source_anchor_url=_ANCHOR))
                for proc in crit.get("processes", []):
                    pid = (proc.get("pid") or "").strip() or f"{crit_id}-{len(pf.nodes)}"
                    if pid in seen:
                        continue
                    seen.add(pid)
                    n_proc += 1
                    process_text = (proc.get("process") or "").strip()
                    checks = re.sub(r"<br\s*/?>", " ", proc.get("processChecks", "") or "").strip()
                    metric = (proc.get("metric") or "").strip()
                    threshold = (proc.get("threshold") or "").strip()
                    pf.nodes.append(ParsedNode(official_id=pid, node_type="test",
                                               label=f"{pid} {process_text[:100]}",
                                               parent_official_id=crit_id, ordinal=n_proc,
                                               source_text=process_text, source_anchor_url=_ANCHOR,
                                               extra={"metric": metric, "threshold": threshold,
                                                      "process_checks": checks}))
                    pf.requirements.append(ParsedRequirement(
                        requirement_key=f"SG-AIV-{pid}",
                        node_official_id=pid, source_reference=f"{principle} process check {pid}",
                        source_text=f"{process_text}\n\nTestable criteria: {crit_text}",
                        normalized_requirement=(
                            f"[{principle} {pid}] {process_text} "
                            f"(testable criteria: {crit_text})."),
                        obligation_type="GOVERNANCE_REQUIREMENT", mandatory=False,
                        domain=principle, source_anchor_url=_ANCHOR,
                        evidence_expectations=[{"type": metric or "Process Check Evidence",
                                               "description": checks or f"Evidence for {pid}."}],
                        test_method=(f"AI Verify process check ({metric}; threshold: {threshold or 'N.A.'}). "
                                     f"Technical tests available via the AI Verify toolkit for testable principles."),
                        extra={"threshold": threshold, "metric": metric},
                    ))

    pf.expected_counts = {
        "principles": n_prin, "testable_criteria": n_crit, "process_checks": n_proc,
        "hierarchy_nodes": len(pf.nodes), "requirements": len(pf.requirements),
    }
    pf.parser_notes.append(
        f"Parsed AI Verify Testing Framework from {repo}@{ref}: {n_prin} governance principles, "
        f"{n_crit} testable criteria, {n_proc} process checks.")
    return pf
