"""Parser for EU legislation supplied as EUR-Lex "Save as Word" (.docx).

These exports carry the operative numbered content (recitals, article
paragraphs, points, definitions, annex items) as 2-column tables
``[marker, text]`` interleaved with heading paragraphs. This parser walks the
document body in order and rebuilds the full legal hierarchy:

    Regulation/Directive
      -> Recital (n)
      -> Chapter -> Section -> Article -> Paragraph -> Point
      -> Article 3 Definitions
      -> Annex -> Annex point

Licence: © European Union - reuse permitted with acknowledgement
(Commission Decision 2011/833/EU). Full source text is reproduced.
"""

from __future__ import annotations

import io
import re
from typing import Any, Dict, List, Optional

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

from aegis_app.regulatory.parsers.base import ParsedFramework, ParsedNode, ParsedRequirement, ParsedDefinition

_NBSP = "\xa0"

_RE_CHAPTER = re.compile(r"^CHAPTER\s+([IVXLC]+)\s*$")
_RE_SECTION = re.compile(r"^SECTION\s+([0-9]+)\s*$")
_RE_ARTICLE = re.compile(r"^Article\s+([0-9]+)\s*$")
_RE_ANNEX = re.compile(r"^ANNEX\s+([IVXLC]+)\s*$")
_RE_PARA = re.compile(r"^([0-9]+)\.\s+(.*)$", re.S)
_RE_POINT_MARK = re.compile(r"^\(([a-z]{1,3}|[0-9]{1,3}|[ivxlc]{1,4})\)$")
_RE_NUM_MARK = re.compile(r"^\(([0-9]{1,3})\)$")

_PROHIB = ("shall be prohibited", "are prohibited", "is prohibited", "shall not be placed")
_REPORT = ("shall report", "shall notify", "shall inform", "shall submit", "shall communicate",
           "shall be reported", "notification", "shall draw up a report")
_RIGHT = ("shall have the right", "has the right", "right to lodge", "right to obtain",
          "right to erasure", "right to rectification", "right of access")
_OBLIG = ("shall ensure", "shall establish", "shall implement", "shall maintain", "shall keep",
          "shall draw up", "shall take", "shall be designed", "shall provide", "shall document",
          "shall put in place", "shall adopt", "shall comply", "shall carry out", "shall register",
          "shall designate", "shall cooperate", "must ", "shall be ", "shall have ")

_ROLES = {
    "provider": "provider", "deployer": "deployer", "importer": "importer",
    "distributor": "distributor", "authorised representative": "authorised_representative",
    "manufacturer": "manufacturer", "operator": "operator",
    "controller": "controller", "processor": "processor",
    "data fiduciary": "data_fiduciary", "financial entit": "financial_entity",
    "essential entit": "essential_entity", "important entit": "important_entity",
    "general-purpose ai model": "gpai_provider",
}

# EU AI Act phased application (Regulation (EU) 2024/1689, Article 113)
_AIACT_DATES = {
    "default": "2026-08-02",
    "prohibitions": "2025-02-02",   # Chapters I-II
    "gpai": "2025-08-02",           # Chapter V + parts of III/IX/XII
    "high_risk_annex_i": "2027-08-02",
}


def _clean(t: str) -> str:
    return re.sub(r"[ \t]+\n", "\n", (t or "").replace(_NBSP, " ")).strip()


def _iter_body(document) -> List[Any]:
    out = []
    for el in document.element.body.iterchildren():
        tag = el.tag.split("}")[-1]
        if tag == "p":
            out.append(Paragraph(el, document))
        elif tag == "tbl":
            out.append(Table(el, document))
    return out


def _obligation_type(text: str, in_recitals: bool, in_definitions: bool, in_annex: bool) -> str:
    low = text.lower()
    if in_recitals:
        return "RECITAL"
    if in_definitions:
        return "DEFINITION"
    if any(k in low for k in _PROHIB):
        return "PROHIBITION"
    if any(k in low for k in _REPORT):
        return "REPORTING_REQUIREMENT"
    if any(k in low for k in _RIGHT):
        return "RIGHT"
    if any(k in low for k in _OBLIG):
        return "OBLIGATION"
    if in_annex:
        return "DOCUMENTATION_REQUIREMENT"
    return "SCOPE"


def _roles(text: str) -> List[str]:
    low = text.lower()
    return sorted({v for k, v in _ROLES.items() if k in low})


def _aiact_effective(article_no: Optional[int], chapter_roman: Optional[str]) -> str:
    if chapter_roman in ("I", "II"):
        return _AIACT_DATES["prohibitions"]
    if chapter_roman == "V":
        return _AIACT_DATES["gpai"]
    if article_no and article_no in (5,):
        return _AIACT_DATES["prohibitions"]
    if article_no and article_no in (53, 54, 55, 56):
        return _AIACT_DATES["gpai"]
    return _AIACT_DATES["default"]


def parse(raw: bytes, manifest_entry: Dict[str, Any]) -> ParsedFramework:
    document = docx.Document(io.BytesIO(raw))
    fk = manifest_entry["framework_key"]
    is_ai_act = fk == "eu_ai_act"

    pf = ParsedFramework(
        framework_key=fk,
        version_label=manifest_entry["version_label"],
        framework_name=manifest_entry["framework_name"],
        framework_type=manifest_entry["framework_type"],
        publication_date=manifest_entry.get("publication_date"),
        effective_date=manifest_entry.get("effective_date"),
        application_dates=manifest_entry.get("application_dates", {}),
    )
    root_id = manifest_entry.get("canonical_identifier", fk)
    anchor = manifest_entry["documents"][0]["official_url"]
    pf.nodes.append(ParsedNode(official_id=root_id, node_type="framework",
                               label=manifest_entry["framework_name"], source_anchor_url=anchor))

    seen_ids: set = set([root_id])

    def add_node(nid, ntype, label, parent, text=None, ordinal=0, extra=None):
        if nid in seen_ids:
            return
        seen_ids.add(nid)
        pf.nodes.append(ParsedNode(official_id=nid, node_type=ntype, label=label,
                                   parent_official_id=parent, ordinal=ordinal,
                                   source_text=_clean(text) if text else None,
                                   source_anchor_url=anchor, extra=extra or {}))

    # state
    in_recitals = False

    chapter_id = chapter_roman = None
    chapter_title_pending = False
    section_id = None
    section_title_pending = False
    article_id = None
    article_no = None
    article_title_pending = False
    in_definitions = False
    annex_id = None
    annex_title_pending = False
    cur_para_id = None
    ordinal = 0
    recital_n = 0
    annex_point_n = 0
    req_keys: set = set()

    body = _iter_body(document)
    for item in body:
        if isinstance(item, Paragraph):
            txt = _clean(item.text)
            if not txt:
                continue

            if chapter_title_pending:
                node = next(n for n in pf.nodes if n.official_id == chapter_id)
                node.label = f"Chapter {chapter_roman} - {txt}"
                chapter_title_pending = False
                continue
            if section_title_pending:
                node = next(n for n in pf.nodes if n.official_id == section_id)
                node.label = txt
                section_title_pending = False
                continue
            if article_title_pending:
                node = next(n for n in pf.nodes if n.official_id == article_id)
                node.label = f"{article_id} - {txt.rstrip('`')}"
                article_title_pending = False
                in_definitions = txt.strip().rstrip("`").lower() == "definitions"
                continue
            if annex_title_pending:
                node = next(n for n in pf.nodes if n.official_id == annex_id)
                node.label = f"{annex_id} - {txt}"
                annex_title_pending = False
                continue

            m = _RE_CHAPTER.match(txt)
            if m:
                chapter_roman = m.group(1)
                chapter_id = f"Chapter {chapter_roman}"
                ordinal += 1
                add_node(chapter_id, "chapter", chapter_id, root_id, ordinal=ordinal)
                chapter_title_pending = True
                section_id = None
                article_id = None
                in_definitions = False
                continue
            m = _RE_SECTION.match(txt)
            if m and chapter_id:
                section_id = f"{chapter_id} Section {m.group(1)}"
                ordinal += 1
                add_node(section_id, "section", section_id, chapter_id, ordinal=ordinal)
                section_title_pending = True
                article_id = None
                continue
            m = _RE_ARTICLE.match(txt)
            if m:
                article_no = int(m.group(1))
                article_id = f"Article {article_no}"
                parent = section_id or chapter_id or root_id
                ordinal += 1
                add_node(article_id, "article", article_id, parent, ordinal=ordinal,
                         extra={"chapter": chapter_roman, "article_no": article_no})
                article_title_pending = True
                cur_para_id = None
                in_definitions = False
                continue
            m = _RE_ANNEX.match(txt)
            if m:
                annex_id = f"Annex {m.group(1)}"
                ordinal += 1
                add_node(annex_id, "annex", annex_id, root_id, ordinal=ordinal)
                annex_title_pending = True
                annex_point_n = 0
                article_id = None
                in_definitions = False
                continue
            if txt == "Whereas:":
                in_recitals = True
                continue
            if txt.startswith("HAVE ADOPTED THIS") or txt.startswith("HAS ADOPTED THIS"):
                in_recitals = False
    
                continue

            # numbered article paragraph in a plain paragraph, e.g. "1.   The ..."
            m = _RE_PARA.match(txt)
            if m and article_id and not in_recitals:
                pnum = m.group(1)
                cur_para_id = f"{article_id}({pnum})"
                ordinal += 1
                add_node(cur_para_id, "paragraph", cur_para_id, article_id, text=m.group(2), ordinal=ordinal)
                _maybe_requirement(pf, cur_para_id, article_id, article_no, chapter_roman,
                                   m.group(2), anchor, is_ai_act, in_definitions=False, in_annex=False,
                                   manifest_entry=manifest_entry, req_keys=req_keys)
                continue

            # free operative text directly under an article (no paragraph numbering)
            if article_id and not in_recitals and len(txt) > 40:
                node = next((n for n in pf.nodes if n.official_id == article_id), None)
                if node and not node.source_text:
                    node.source_text = _clean(txt)
                    _maybe_requirement(pf, article_id, article_id, article_no, chapter_roman,
                                       txt, anchor, is_ai_act, in_definitions, in_annex=bool(annex_id),
                                       manifest_entry=manifest_entry, req_keys=req_keys)
            continue

        # ---- Table: numbered content ----
        try:
            row = item.rows[0]
            cells = row.cells
        except Exception:
            continue
        if len(cells) < 2:
            continue
        marker = _clean(cells[0].text)
        text = _clean(cells[1].text)
        if not text:
            continue

        if in_recitals and _RE_NUM_MARK.match(marker):
            recital_n += 1
            rid = f"Recital ({_RE_NUM_MARK.match(marker).group(1)})"
            ordinal += 1
            add_node(rid, "recital", rid, root_id, text=text, ordinal=ordinal)
            continue

        if in_definitions and _RE_NUM_MARK.match(marker):
            num = _RE_NUM_MARK.match(marker).group(1)
            did = f"{article_id}({num})"
            ordinal += 1
            add_node(did, "definition", _term_of(text), article_id, text=text, ordinal=ordinal)
            pf.definitions.append(ParsedDefinition(
                term=_term_of(text), definition_text=text,
                source_reference=did, source_anchor_url=anchor,
                effective_from=manifest_entry.get("effective_date"),
            ))
            continue

        if annex_id:
            annex_point_n += 1
            mk = (_RE_POINT_MARK.match(marker) or _RE_NUM_MARK.match(marker))
            disp = f"{annex_id}({mk.group(1)})" if mk else f"{annex_id} point {annex_point_n}"
            nid = f"{annex_id} point {annex_point_n}"
            ordinal += 1
            add_node(nid, "annex_section", disp, annex_id, text=text, ordinal=ordinal,
                     extra={"marker": marker})
            _maybe_requirement(pf, nid, annex_id, article_no, chapter_roman, text, anchor,
                               is_ai_act, in_definitions=False, in_annex=True,
                               manifest_entry=manifest_entry, req_keys=req_keys)
            continue

        # lettered / numbered point under the current article paragraph
        if article_id:
            pt = _RE_POINT_MARK.match(marker)
            key = pt.group(1) if pt else marker.strip("().")
            parent = cur_para_id or article_id
            nid = f"{parent}({key})"
            if nid in seen_ids:
                s = 2
                while f"{nid}#{s}" in seen_ids:
                    s += 1
                nid = f"{nid}#{s}"
            ordinal += 1
            add_node(nid, "point", nid.replace("#", " · "), parent, text=text, ordinal=ordinal)
            _maybe_requirement(pf, nid, parent, article_no, chapter_roman, text, anchor,
                               is_ai_act, in_definitions=in_definitions, in_annex=False,
                               manifest_entry=manifest_entry, req_keys=req_keys)

    _counts(pf)
    pf.parser_notes.append(
        f"Parsed {fk} .docx: {sum(1 for n in pf.nodes if n.node_type=='recital')} recitals, "
        f"{sum(1 for n in pf.nodes if n.node_type=='chapter')} chapters, "
        f"{sum(1 for n in pf.nodes if n.node_type=='article')} articles, "
        f"{sum(1 for n in pf.nodes if n.node_type=='definition')} definitions, "
        f"{sum(1 for n in pf.nodes if n.node_type=='annex')} annexes, "
        f"{len(pf.requirements)} candidate requirements.")
    return pf


# ---- helpers -------------------------------------------------------------
def is_ai_act_definitions(article_id: Optional[str]) -> bool:
    return article_id == "Article 3"


def _term_of(text: str) -> str:
    m = re.match(r"^[‘’'\"“”]([^‘’'\"“”]{2,80})[‘’'\"“”]", text)
    if m:
        return m.group(1)
    return text.split(" means ")[0][:80] if " means " in text else text[:60]


def _maybe_requirement(pf: ParsedFramework, node_id: str, parent_ref: str, article_no, chapter_roman,
                       text: str, anchor: str, is_ai_act: bool, in_definitions: bool, in_annex: bool,
                       manifest_entry: Dict[str, Any], req_keys: set) -> None:
    otype = _obligation_type(text, in_recitals=False, in_definitions=in_definitions, in_annex=in_annex)
    if otype in ("RECITAL", "DEFINITION", "SCOPE"):
        return
    if len(text) < 30:
        return
    fk = manifest_entry["framework_key"]
    key = f"{_prefix(fk)}-{re.sub(r'[^A-Za-z0-9]+', '-', node_id).strip('-').upper()}"
    if key in req_keys:
        n = 2
        while f"{key}-{n}" in req_keys:
            n += 1
        key = f"{key}-{n}"
    req_keys.add(key)
    eff = _aiact_effective(article_no, chapter_roman) if is_ai_act else manifest_entry.get("effective_date")
    pf.requirements.append(ParsedRequirement(
        requirement_key=key,
        node_official_id=node_id,
        source_reference=node_id,
        source_text=text,
        normalized_requirement=_normalize(text, node_id, otype),
        obligation_type=otype,
        subject_roles=_roles(text),
        who_is_obligated=", ".join(_roles(text)) or None,
        mandatory=otype != "RIGHT",
        effective_from=eff,
        temporal_state="CURRENTLY_APPLICABLE",
        domain=f"Chapter {chapter_roman}" if chapter_roman else None,
        source_anchor_url=anchor,
        evidence_expectations=_evidence_hint(text, otype),
        test_method="Legal/compliance review against the cited provision; verify implementing measures and records.",
        extra={"article_no": article_no},
    ))


def _prefix(fk: str) -> str:
    return {"eu_ai_act": "EU-AIA", "gdpr": "GDPR", "eu_cra": "EU-CRA",
            "nis2": "NIS2", "dora": "DORA"}.get(fk, fk.upper())


def _normalize(text: str, ref: str, otype: str) -> str:
    verb = {"PROHIBITION": "Do not", "REPORTING_REQUIREMENT": "Report/notify as required by",
            "RIGHT": "Uphold the right established by", "OBLIGATION": "Comply with",
            "DOCUMENTATION_REQUIREMENT": "Produce the documentation required by"}.get(otype, "Address")
    snippet = text if len(text) < 400 else text[:397] + "..."
    return f"[{ref}] {verb} this provision: {snippet}"


def _evidence_hint(text: str, otype: str) -> List[Dict[str, str]]:
    low = text.lower()
    hints = []
    if "risk management" in low:
        hints.append({"type": "Risk Management Record", "description": "AI/ICT risk management system documentation."})
    if "technical documentation" in low or "annex iv" in low:
        hints.append({"type": "Technical Documentation", "description": "Annex IV / technical file."})
    if "log" in low:
        hints.append({"type": "Logs", "description": "Automatic event logs and retention policy."})
    if "human oversight" in low:
        hints.append({"type": "Human Oversight Procedure", "description": "Oversight design + operating procedure."})
    if "data" in low and "governance" in low:
        hints.append({"type": "Data Governance Spec", "description": "Dataset governance, provenance, bias evaluation."})
    if otype == "REPORTING_REQUIREMENT":
        hints.append({"type": "Notification Record", "description": "Evidence of the required report/notification and its timing."})
    if not hints:
        hints.append({"type": "Compliance Record", "description": "Documented measures demonstrating conformity with the provision."})
    return hints


def _counts(pf: ParsedFramework) -> None:
    by = {}
    for n in pf.nodes:
        by[n.node_type] = by.get(n.node_type, 0) + 1
    pf.expected_counts = {
        "recitals": by.get("recital", 0),
        "chapters": by.get("chapter", 0),
        "sections": by.get("section", 0),
        "articles": by.get("article", 0),
        "paragraphs": by.get("paragraph", 0),
        "points": by.get("point", 0),
        "definitions": by.get("definition", 0),
        "annexes": by.get("annex", 0),
        "annex_points": by.get("annex_section", 0),
        "hierarchy_nodes": len(pf.nodes),
        "requirements": len(pf.requirements),
    }
