"""Parsers for NIST publications supplied as PDF.

  * parse_ai_rmf     - NIST AI 100-1 Appendix A (full Function/Category/Subcategory text)
  * parse_ai_600_1   - NIST AI 600-1 Generative AI Profile (12 GAI risks + ~200 suggested actions)

Licence: U.S. Government work / public domain.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from aegis_app.regulatory.parsers.base import ParsedFramework, ParsedNode, ParsedRequirement
from aegis_app.regulatory.parsers.pdf_common import page_texts, clean, strip_headers_footers

_FUNCS = ("GOVERN", "MAP", "MEASURE", "MANAGE")
_AIRMF_ANCHOR = "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf"
_AI6001_ANCHOR = "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf"

_CAT_RE = re.compile(rf"\b({'|'.join(_FUNCS)})\s+(\d+):\s*(.*?)(?=\b(?:{'|'.join(_FUNCS)})\s+\d+(?:\.\d+)?:|Categories|Subcategories|Continued on next page|\Z)", re.S)
_SUB_RE = re.compile(rf"\b({'|'.join(_FUNCS)})\s+(\d+)\.(\d+):\s*(.*?)(?=\b(?:{'|'.join(_FUNCS)})\s+\d+(?:\.\d+)?:|Categories|Subcategories|Continued on next page|Table\s+\d+:|\Z)", re.S)
_ACTION_RE = re.compile(r"\b([A-Z]{2}-\d+\.\d+-\d{3})\b\s+(.*?)(?=\b[A-Z]{2}-\d+\.\d+-\d{3}\b|AI Actor Tasks:|\Z)", re.S)
_SUBHDR_RE = re.compile(rf"\b(({'|'.join(_FUNCS)})\s+\d+\.\d+):\s*([^\n]+?\.)\s*\n?\s*Action ID", re.S)

_GAI_RISKS = [
    "CBRN Information or Capabilities", "Confabulation", "Dangerous, Violent, or Hateful Content",
    "Data Privacy", "Environmental Impacts", "Harmful Bias and Homogenization",
    "Human-AI Configuration", "Information Integrity", "Information Security",
    "Intellectual Property", "Obscene, Degrading, and/or Abusive Content",
    "Value Chain and Component Integration",
]


def _appendix_a(raw: bytes) -> str:
    pages = page_texts(raw)
    start = next((i for i, p in enumerate(pages)
                  if "Categories and subcategories for the GOVERN" in p), None)
    if start is None:
        start = next((i for i, p in enumerate(pages) if "Appendix A" in p and "GOVERN" in p), 20)
    body = strip_headers_footers(pages[start:], ["NIST AI 100-1", "AI RMF 1.0", "Continued on next page"])
    return body


def parse_ai_rmf(raw: bytes, me: Dict[str, Any]) -> ParsedFramework:
    body = _appendix_a(raw)
    pf = ParsedFramework(framework_key="nist_ai_rmf", version_label="1.0",
                         framework_name=me["framework_name"], framework_type=me["framework_type"],
                         publication_date=me.get("publication_date"), effective_date=me.get("effective_date"))
    root_id = "NIST-AI-RMF-1.0"
    pf.nodes.append(ParsedNode(official_id=root_id, node_type="framework",
                               label="NIST AI Risk Management Framework (AI RMF 1.0)",
                               source_anchor_url=_AIRMF_ANCHOR))

    func_desc = {
        "GOVERN": "A culture of risk management is cultivated and present.",
        "MAP": "Context is recognized and risks related to context are identified.",
        "MEASURE": "Identified risks are assessed, analyzed, or tracked.",
        "MANAGE": "Risks are prioritized and acted upon based on a projected impact.",
    }
    for i, fn in enumerate(_FUNCS):
        pf.nodes.append(ParsedNode(official_id=fn, node_type="function", label=fn,
                                   parent_official_id=root_id, ordinal=i,
                                   source_text=func_desc[fn], source_anchor_url=_AIRMF_ANCHOR))

    cats: Dict[str, str] = {}
    for m in _CAT_RE.finditer(body):
        cid = f"{m.group(1)} {m.group(2)}"
        cats.setdefault(cid, clean(m.group(3)))
    for i, (cid, ctext) in enumerate(cats.items()):
        fn = cid.split()[0]
        pf.nodes.append(ParsedNode(official_id=cid, node_type="category", label=ctext[:120] or cid,
                                   parent_official_id=fn, ordinal=i, source_text=ctext,
                                   source_anchor_url=_AIRMF_ANCHOR))

    subs: Dict[str, str] = {}
    for m in _SUB_RE.finditer(body):
        sid = f"{m.group(1)} {m.group(2)}.{m.group(3)}"
        txt = clean(m.group(4))
        if 5 < len(txt) < 800:
            subs.setdefault(sid, txt)

    for i, (sid, stext) in enumerate(subs.items()):
        cid = f"{sid.split()[0]} {sid.split()[1].split('.')[0]}"
        parent = cid if cid in cats else sid.split()[0]
        pf.nodes.append(ParsedNode(official_id=sid, node_type="subcategory", label=sid,
                                   parent_official_id=parent, ordinal=i, source_text=stext,
                                   source_anchor_url=_AIRMF_ANCHOR))
        pf.requirements.append(ParsedRequirement(
            requirement_key=f"NIST-AIRMF-{sid.replace(' ', '-')}",
            node_official_id=sid, source_reference=sid, source_text=stext,
            normalized_requirement=f"Establish the AI RMF outcome {sid}: {stext}",
            obligation_type="GOVERNANCE_REQUIREMENT", mandatory=False,
            domain=sid.split()[0], source_anchor_url=_AIRMF_ANCHOR,
            evidence_expectations=[{"type": "AI RMF Evidence",
                                   "description": f"Documented outcomes/artefacts for {sid} (see AI RMF Playbook)."}],
            test_method="Assess implementation of this subcategory outcome (AI RMF Playbook suggested actions).",
        ))

    pf.expected_counts = {
        "functions": 4, "categories": len(cats), "subcategories": len(subs),
        "hierarchy_nodes": len(pf.nodes), "requirements": len(pf.requirements),
    }
    pf.parser_notes.append(
        f"Parsed AI RMF 1.0 Appendix A from PDF: {len(cats)} categories, {len(subs)} subcategories "
        f"with full outcome text.")
    if len(subs) < 60:
        pf.parser_notes.append(f"WARNING: only {len(subs)} subcategories extracted (expected ~72) - PDF layout review needed.")
    return pf


def parse_ai_600_1(raw: bytes, me: Dict[str, Any]) -> ParsedFramework:
    pages = page_texts(raw)
    full = strip_headers_footers(pages, ["NIST AI 600-1", "AI RMF: Generative AI Profile"])
    pf = ParsedFramework(framework_key="nist_ai_600_1", version_label=me["version_label"],
                         framework_name=me["framework_name"], framework_type=me["framework_type"],
                         publication_date=me.get("publication_date"), effective_date=me.get("effective_date"))
    root_id = "NIST-AI-600-1"
    pf.nodes.append(ParsedNode(official_id=root_id, node_type="framework",
                               label="NIST AI 600-1 Generative AI Profile", source_anchor_url=_AI6001_ANCHOR))

    # 12 GAI risk categories (fixed, from section 2)
    for i, r in enumerate(_GAI_RISKS):
        pf.nodes.append(ParsedNode(official_id=f"GAI-RISK: {r}", node_type="risk", label=r,
                                   parent_official_id=root_id, ordinal=i, source_text=r,
                                   source_anchor_url=_AI6001_ANCHOR))

    # subcategory headers that introduce each suggested-actions table
    sub_headers: Dict[str, str] = {}
    for m in _SUBHDR_RE.finditer(full):
        sub_headers[m.group(1)] = clean(m.group(3))
    for sid, stext in sub_headers.items():
        pf.nodes.append(ParsedNode(official_id=f"AIRMF-REF {sid}", node_type="category",
                                   label=f"{sid} (AI RMF)", parent_official_id=root_id,
                                   source_text=stext, source_anchor_url=_AI6001_ANCHOR))

    n_act = 0
    seen = set()
    for m in _ACTION_RE.finditer(full):
        aid = m.group(1)
        if aid in seen:
            continue
        seen.add(aid)
        text = clean(m.group(2))
        # trim trailing GAI-risk column tokens
        for r in _GAI_RISKS:
            text = re.split(rf"\s*{re.escape(r)}\s*;?\s*$", text)[0]
        text = re.sub(r"\s*(?:;\s*)?(?:" + "|".join(re.escape(r) for r in _GAI_RISKS) + r")\s*;?\s*$", "", text).strip()
        if len(text) < 15:
            continue
        n_act += 1
        sid = aid.rsplit("-", 1)[0].replace("-", " ", 0)
        subref = "AIRMF-REF " + _airmf_sid(aid)
        parent = subref if subref in {n.official_id for n in pf.nodes} else root_id
        pf.nodes.append(ParsedNode(official_id=aid, node_type="task", label=aid,
                                   parent_official_id=parent, ordinal=n_act, source_text=text,
                                   source_anchor_url=_AI6001_ANCHOR))
        pf.requirements.append(ParsedRequirement(
            requirement_key=f"NIST-AI6001-{aid}", node_official_id=aid, source_reference=aid,
            source_text=text,
            normalized_requirement=f"Suggested action {aid} (NIST GenAI Profile): {text}",
            obligation_type="GUIDANCE", mandatory=False, domain=_airmf_sid(aid),
            source_anchor_url=_AI6001_ANCHOR,
            evidence_expectations=[{"type": "GenAI Control Evidence",
                                   "description": f"Evidence the suggested action {aid} is implemented for this GenAI system."}],
            test_method="Assess whether the suggested action is implemented; map result to the related AI RMF subcategory.",
            extra={"maps_to_airmf": _airmf_sid(aid)},
        ))

    pf.expected_counts = {
        "gai_risks": len(_GAI_RISKS), "airmf_subcategory_refs": len(sub_headers),
        "suggested_actions": n_act, "hierarchy_nodes": len(pf.nodes), "requirements": len(pf.requirements),
    }
    pf.parser_notes.append(
        f"Parsed AI 600-1 from PDF: {len(_GAI_RISKS)} GAI risk categories, {len(sub_headers)} AI RMF "
        f"subcategory references, {n_act} suggested actions. GAI-risk column bleed trimmed heuristically - review recommended.")
    return pf


def _airmf_sid(action_id: str) -> str:
    m = re.match(r"([A-Z]{2})-(\d+)\.(\d+)-\d+", action_id)
    if not m:
        return ""
    fmap = {"GV": "GOVERN", "MP": "MAP", "MS": "MEASURE", "MG": "MANAGE"}
    return f"{fmap.get(m.group(1), m.group(1))} {m.group(2)}.{m.group(3)}"
