"""Parser for the OWASP Top 10 for LLM Applications (GenAI Security Project).

Source format: a bundle of per-entry Markdown files from the official repository.
Licence: CC BY-SA 4.0 -> reproduction permitted with attribution + share-alike.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from aegis_app.regulatory.parsers.base import ParsedFramework, ParsedNode, ParsedRequirement

_TITLE_RE = re.compile(r"^##\s+(LLM\d{2}:\d{4})\s+(.*)$", re.MULTILINE)
_H3_RE = re.compile(r"^###\s+(.*)$", re.MULTILINE)
_H4_RE = re.compile(r"^####\s+(.*)$", re.MULTILINE)


def _sections(md: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    matches = list(_H3_RE.finditer(md))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        out[m.group(1).strip().lower()] = md[start:end].strip()
    return out


def _h4_items(block: str) -> List[str]:
    return [m.group(1).strip() for m in _H4_RE.finditer(block)]


def parse(raw: bytes, manifest_entry: Dict[str, Any]) -> ParsedFramework:
    bundle = json.loads(raw.decode("utf-8"))
    files: Dict[str, str] = bundle["files"]
    release_year = bundle.get("release_year") or manifest_entry["version_label"]

    pf = ParsedFramework(
        framework_key="owasp_llm",
        version_label=str(release_year),
        framework_name=manifest_entry["framework_name"],
        framework_type=manifest_entry["framework_type"],
        publication_date=manifest_entry.get("publication_date"),
        effective_date=manifest_entry.get("effective_date"),
    )

    root_id = f"OWASP-LLM-TOP10-{release_year}"
    pf.nodes.append(ParsedNode(
        official_id=root_id, node_type="release",
        label=f"OWASP Top 10 for LLM Applications ({release_year})",
        source_anchor_url="https://genai.owasp.org/llm-top-10/",
    ))

    n_risks = 0
    for fname in sorted(files):
        md = files[fname]
        tm = _TITLE_RE.search(md)
        if not tm:
            continue  # preface / appendix - context only, not a risk entry
        risk_id, title = tm.group(1), tm.group(2).strip()
        n_risks += 1
        secs = _sections(md)
        description = secs.get("description", "").strip()
        mitig_block = next((v for k, v in secs.items() if "prevention" in k or "mitigation" in k), "")
        scenario_block = next((v for k, v in secs.items() if "scenario" in k or "example attack" in k), "")
        mitigations = _h4_items(mitig_block)
        scenarios = _h4_items(scenario_block)
        slug = risk_id.split(":")[0].lower()

        pf.nodes.append(ParsedNode(
            official_id=risk_id, node_type="risk", label=title,
            parent_official_id=root_id, ordinal=n_risks,
            source_text=description,
            source_anchor_url=f"https://genai.owasp.org/llmrisk/{slug}/",
            extra={"mitigations": mitigations, "scenarios": scenarios},
        ))

        pf.requirements.append(ParsedRequirement(
            requirement_key=f"OWASP-LLM-{risk_id.replace(':', '-')}",
            node_official_id=risk_id,
            source_reference=f"{risk_id} {title}",
            source_text=description,
            normalized_requirement=(
                f"Evaluate this LLM application for the OWASP risk “{title}” ({risk_id}); "
                f"where applicable, implement the OWASP-recommended prevention and mitigation "
                f"strategies and evidence them via adversarial testing."
            ),
            obligation_type="SECURITY_REQUIREMENT",
            mandatory=False,
            domain="LLM Application Security",
            source_anchor_url=f"https://genai.owasp.org/llmrisk/{slug}/",
            evidence_expectations=[{"type": "Mitigation Control", "description": m} for m in mitigations]
            or [{"type": "Security Assessment", "description": f"Assessment against {risk_id}."}],
            test_method="Adversarial testing / red-teaming targeting this risk category; design review.",
            extra={"scenarios": scenarios},
        ))

    pf.expected_counts = {
        "risk_entries": n_risks,
        "hierarchy_nodes": len(pf.nodes),
        "requirements": len(pf.requirements),
    }
    pf.parser_notes.append(f"Parsed OWASP LLM Top 10 ({release_year}): {n_risks} risk entries from {len(files)} files.")
    return pf
