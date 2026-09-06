"""Parser for OWASP GenAI 'Top 10' PDFs (LLM Applications, Agentic Applications).

Extracts the 10 risk entries, their titles and body text. Licence: CC BY-SA 4.0.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from aegis_app.regulatory.parsers.base import ParsedFramework, ParsedNode, ParsedRequirement
from aegis_app.regulatory.parsers.pdf_common import page_texts, clean, strip_headers_footers

# id: [ "LLM01:2026", "ASI01" ...]
_HEADING_RE = re.compile(r"^\s*((?:LLM|ASI|AAI)\d{2})(?::20\d\d)?[:\s\-]+([A-Z][A-Za-z0-9 &,/()\-]{3,70})\s*$", re.M)
_SECTION_HINTS = ("description", "common examples", "prevention", "mitigation",
                  "example attack scenarios", "attack scenarios", "reference")


def parse(raw: bytes, me: Dict[str, Any]) -> ParsedFramework:
    fk = me["framework_key"]
    pages = page_texts(raw)
    body = strip_headers_footers(pages, ["OWASP Top 10", "genai.owasp.org", "Creative Commons",
                                         "Licensed under"])
    prefix = "ASI" if fk == "owasp_agentic_ai" else "LLM"
    version_label = me["version_label"]

    # Each risk id appears several times (cover, TOC, cross-references, author
    # credits, content). Pick the occurrence whose following text reads like the
    # risk write-up: contains "Description" and the most lowercase prose.
    def prose_score(seg: str) -> int:
        s = seg[:600]
        return (300 if re.search(r"\bDescription\b", s) else 0) + len(re.findall(r"\b[a-z]{4,}\b", s))

    cand: Dict[str, List[tuple]] = {}
    for m in _HEADING_RE.finditer(body):
        rid, title = m.group(1), m.group(2).strip()
        if not rid.startswith(prefix):
            continue
        # stitch a wrapped title continuation ("Tool Misuse and\nExploitation")
        tail = body[m.end():m.end() + 60].lstrip()
        cont = re.match(r"^([A-Z][A-Za-z()/&\- ]{2,40}?)(?:\n|\s{2,}|Description)", tail)
        if cont and title[-1] not in ".:":
            frag = cont.group(1).strip()
            if frag.lower() not in title.lower():
                title = f"{title} {frag}".strip()
        title = re.sub(r"\s*Description\s*$", "", title).strip()
        cand.setdefault(rid, []).append((title, m.start(), m.end()))

    hits: Dict[str, tuple] = {}
    for rid, occs in cand.items():
        scored = [(prose_score(body[o[2]:o[2] + 700]), o) for o in occs]
        scored = [x for x in scored if x[0] >= 150] or scored
        hits[rid] = max(scored, key=lambda x: x[0])[1]
    ordered = sorted(hits.items(), key=lambda kv: kv[1][1])

    pf = ParsedFramework(framework_key=fk, version_label=version_label,
                         framework_name=me["framework_name"], framework_type=me["framework_type"],
                         publication_date=me.get("publication_date"), effective_date=me.get("effective_date"))
    root_id = f"{me.get('canonical_identifier', fk)}"
    anchor = me["documents"][0]["official_url"]
    pf.nodes.append(ParsedNode(official_id=root_id, node_type="release",
                               label=me["framework_name"], source_anchor_url=anchor))

    for i, (rid, (title, s, e)) in enumerate(ordered):
        nxt = ordered[i + 1][1][1] if i + 1 < len(ordered) else len(body)
        raw_block = body[e:nxt]
        block = clean(raw_block)
        # drop a leading repeated title fragment + a leading "Description" label
        block = re.sub(r"^\s*(?:[A-Z][A-Za-z()/&\-]+\s+){0,4}Description\s+", "", block)
        # description = text up to the first known sub-heading
        low = block.lower()
        cut = min([low.find(h) for h in _SECTION_HINTS if low.find(h) > 40] or [len(block)])
        desc = (block[:cut].strip() or block[:800])[:2000]
        if len(desc) < 60:
            # content section not cleanly isolated - fall back to the widest window
            wide = clean(body[e:nxt + 1500])
            wide = re.sub(r"^\s*(?:[A-Z][A-Za-z()/&\-]+\s+){0,4}Description\s+", "", wide)
            desc = wide[:1200] or f"{title} - see source PDF (automatic extraction incomplete; review required)."
            pf.parser_notes.append(f"{rid}: description extraction incomplete - flagged for review.")
        mitig = _extract_after(raw_block, ("Prevention", "Mitigation"))
        scen = _extract_after(raw_block, ("Example Attack Scenarios", "Attack Scenarios", "Common Examples"))

        official = f"{rid}:{version_label}" if prefix == "LLM" else rid
        pf.nodes.append(ParsedNode(official_id=official, node_type="risk", label=title,
                                   parent_official_id=root_id, ordinal=i + 1,
                                   source_text=desc, source_anchor_url=anchor,
                                   extra={"mitigations_text": mitig[:4000], "scenarios_text": scen[:4000]}))
        pf.requirements.append(ParsedRequirement(
            requirement_key=f"{'OWASP-LLM' if prefix=='LLM' else 'OWASP-ASI'}-{rid}-{version_label}",
            node_official_id=official, source_reference=f"{official} {title}",
            source_text=desc,
            normalized_requirement=(
                f"Evaluate this {'agentic ' if prefix=='ASI' else 'LLM '}application for the OWASP risk "
                f"“{title}” ({official}); where applicable, implement the OWASP-recommended prevention "
                f"and mitigation strategies and evidence them via adversarial testing."),
            obligation_type="SECURITY_REQUIREMENT", mandatory=False,
            domain="Agentic AI Security" if prefix == "ASI" else "LLM Application Security",
            source_anchor_url=anchor,
            evidence_expectations=[{"type": "Mitigation Control",
                                   "description": (mitig[:500] or f"Documented controls addressing {official}.")}],
            test_method="Adversarial testing / red-teaming targeting this risk category; design review.",
            extra={"scenarios_excerpt": scen[:800]},
        ))

    pf.expected_counts = {"risk_entries": len(ordered), "hierarchy_nodes": len(pf.nodes),
                          "requirements": len(pf.requirements)}
    pf.parser_notes.append(f"Parsed {fk} {version_label} PDF: {len(ordered)} risk entries ({prefix}xx).")
    if len(ordered) < 10:
        pf.parser_notes.append(f"WARNING: only {len(ordered)} entries found (expected 10) - PDF layout review needed.")
    return pf


def _extract_after(text: str, headings: tuple) -> str:
    for h in headings:
        i = text.find(h)
        if i >= 0:
            return clean(text[i + len(h): i + len(h) + 6000])
    return ""
