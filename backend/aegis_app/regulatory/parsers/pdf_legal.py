"""PDF parsers for the UK AI Cyber Security Code of Practice (implementation
guide) and the India DPDP Rules 2025.
"""

from __future__ import annotations

import re
from typing import Any, Dict

import pymupdf

from aegis_app.regulatory.parsers.base import ParsedFramework, ParsedNode, ParsedRequirement
from aegis_app.regulatory.parsers.pdf_common import clean

_UK_PRINCIPLE_RE = re.compile(r"^\s*Principle\s+(\d{1,2})\s*[:.]\s*(.+?)\s*$")
_UK_PROVISION_RE = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\s+(.*)$", re.S)


def parse_uk_code(raw: bytes, me: Dict[str, Any]) -> ParsedFramework:
    doc = pymupdf.open(stream=raw, filetype="pdf")
    anchor = me["documents"][0]["official_url"]
    pf = ParsedFramework(framework_key="uk_ai_cyber_code", version_label=me["version_label"],
                         framework_name=me["framework_name"], framework_type=me["framework_type"],
                         publication_date=me.get("publication_date"), effective_date=me.get("effective_date"))
    root_id = "UK-AI-CYBER-COP"
    pf.nodes.append(ParsedNode(official_id=root_id, node_type="framework",
                               label="UK Code of Practice for the Cyber Security of AI",
                               source_anchor_url=anchor))

    principles: Dict[str, str] = {}

    seen_prov: set = set()

    for pno in range(doc.page_count):
        page = doc[pno]
        text = page.get_text()
        for line in text.splitlines():
            m = _UK_PRINCIPLE_RE.match(line)
            if m and 1 <= int(m.group(1)) <= 13:
                pid = f"Principle {m.group(1)}"
                if pid not in principles:
                    principles[pid] = clean(m.group(2))
                    pf.nodes.append(ParsedNode(official_id=pid, node_type="principle",
                                               label=f"{pid}: {clean(m.group(2))}",
                                               parent_official_id=root_id, ordinal=int(m.group(1)),
                                               source_text=clean(m.group(2)), source_anchor_url=anchor))


        # provisions live in 4-column tables: [Provisions, Threats, Example Controls, Reference]
        try:
            tables = page.find_tables()
        except Exception:
            tables = None
        for tbl in (tables.tables if tables else []):
            rows = tbl.extract()
            for row in rows:
                if not row or not row[0]:
                    continue
                cell = clean(row[0])
                pm = _UK_PROVISION_RE.match(cell)
                if not pm:
                    continue
                pnum = f"{pm.group(1)}.{pm.group(2)}"
                if pnum in seen_prov:
                    continue
                seen_prov.add(pnum)
                principle_id = f"Principle {pm.group(1)}"
                prov_text = clean(pm.group(3))
                threats = clean(row[1]) if len(row) > 1 else ""
                controls = clean(row[2]) if len(row) > 2 else ""
                refs = clean(row[3]) if len(row) > 3 else ""
                nid = f"Provision {pnum}"
                pf.nodes.append(ParsedNode(official_id=nid, node_type="rule", label=nid,
                                           parent_official_id=principle_id if principle_id in principles else root_id,
                                           source_text=prov_text, source_anchor_url=anchor,
                                           extra={"related_threats": threats, "example_controls": controls,
                                                  "references": refs}))
                otype = "SECURITY_REQUIREMENT"
                low = prov_text.lower()
                if "should" in low and "shall" not in low:
                    otype = "GUIDANCE"
                pf.requirements.append(ParsedRequirement(
                    requirement_key=f"UK-AICODE-{pnum}", node_official_id=nid, source_reference=nid,
                    source_text=prov_text,
                    normalized_requirement=f"[{nid}] {prov_text}",
                    obligation_type=otype, mandatory="shall" in low,
                    subject_roles=["developer"] if "develop" in low else (["system operator"] if "operat" in low else []),
                    domain=principles.get(principle_id, ""), source_anchor_url=anchor,
                    evidence_expectations=[{"type": "Example Measure/Control",
                                           "description": controls[:600] or f"Documented controls implementing {nid}."}],
                    test_method="Review implementation against the provision and the guide's example measures.",
                    extra={"related_threats": threats[:600], "references": refs[:600]},
                ))

    pf.expected_counts = {
        "principles": len(principles), "provisions": len(seen_prov),
        "hierarchy_nodes": len(pf.nodes), "requirements": len(pf.requirements),
    }
    pf.parser_notes.append(
        f"Parsed UK AI Cyber Security Code from the implementation guide: {len(principles)} principles, "
        f"{len(seen_prov)} provisions (with example measures + threat mappings).")
    if len(principles) < 13:
        pf.parser_notes.append(f"WARNING: {len(principles)}/13 principles detected - review PDF layout.")
    return pf


# --------------------------------------------------------------------------
_DPDP_RULE_RE = re.compile(r"^\s*(\d{1,2})\.\s+([A-Z][^\n]{3,90}?)\.\s*(?:—|-)\s*(.*)$", re.S)
_DPDP_SUB_RE = re.compile(r"^\s*\((\d{1,2})\)\s+(.*)$", re.S)
_DPDP_PT_RE = re.compile(r"^\s*\(([a-z]{1,3})\)\s+(.*)$", re.S)
_DPDP_SCHED_RE = re.compile(r"^\s*(THE\s+[A-Z]+\s+SCHEDULE|(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH)\s+SCHEDULE)\s*$")


def parse_dpdp_rules(raw: bytes, me: Dict[str, Any]) -> ParsedFramework:
    doc = pymupdf.open(stream=raw, filetype="pdf")
    anchor = me["documents"][0]["official_url"]
    pf = ParsedFramework(framework_key="india_dpdp", version_label=me["version_label"],
                         framework_name=me["framework_name"], framework_type=me["framework_type"],
                         publication_date=me.get("publication_date"), effective_date=me.get("effective_date"))
    root_id = "DPDP-RULES-2025"
    pf.nodes.append(ParsedNode(official_id=root_id, node_type="framework",
                               label="Digital Personal Data Protection Rules, 2025", source_anchor_url=anchor))

    full = "\n".join(doc[p].get_text() for p in range(doc.page_count))
    full = re.sub(r"\n\s*\d+\s*\n\s*THE GAZETTE OF INDIA[^\n]*\n\s*\[PART[^\]]*\]\s*\n", "\n", full)
    lines = full.splitlines()

    node_ids: set = set()
    req_keys: set = set()

    def add(node) -> bool:
        if node.official_id in node_ids:
            return False
        node_ids.add(node.official_id)
        pf.nodes.append(node)
        return True

    cur_rule = None
    cur_sub = None
    ordv = 0
    schedule = None

    for line in (ln.rstrip() for ln in lines):
        sm = _DPDP_SCHED_RE.match(line.strip())
        if sm:
            schedule = sm.group(1).title()
            ordv += 1
            sid = f"Schedule: {schedule}"
            add(ParsedNode(official_id=sid, node_type="schedule", label=sid,
                           parent_official_id=root_id, ordinal=ordv, source_anchor_url=anchor))
            cur_rule, cur_sub = sid, None
            continue

        rm = _DPDP_RULE_RE.match(line)
        if rm and not schedule and 1 <= int(rm.group(1)) <= 40:
            rid = f"Rule {rm.group(1)}"
            ordv += 1
            add(ParsedNode(official_id=rid, node_type="rule",
                           label=f"{rid} - {clean(rm.group(2))}", parent_official_id=root_id,
                           ordinal=ordv, source_text=clean(rm.group(3))[:400] or None,
                           source_anchor_url=anchor))
            cur_rule, cur_sub = rid, None
            tail = clean(rm.group(3))
            if len(tail) > 40:
                _dpdp_req(pf, rid, rid, tail, anchor, req_keys)
            continue

        subm = _DPDP_SUB_RE.match(line)
        if subm and cur_rule:
            ordv += 1
            sid = f"{cur_rule}({subm.group(1)})"
            txt = clean(subm.group(2))
            if add(ParsedNode(official_id=sid, node_type="sub_rule", label=sid,
                              parent_official_id=cur_rule, ordinal=ordv, source_text=txt,
                              source_anchor_url=anchor)):
                cur_sub = sid
                if len(txt) > 40:
                    _dpdp_req(pf, sid, cur_rule, txt, anchor, req_keys)
            continue

        ptm = _DPDP_PT_RE.match(line)
        if ptm and (cur_sub or cur_rule):
            ordv += 1
            parent = cur_sub or cur_rule
            pid = f"{parent}({ptm.group(1)})"
            txt = clean(ptm.group(2))
            if add(ParsedNode(official_id=pid, node_type="point", label=pid, parent_official_id=parent,
                              ordinal=ordv, source_text=txt, source_anchor_url=anchor)):
                if len(txt) > 40:
                    _dpdp_req(pf, pid, parent, txt, anchor, req_keys)

    pf.expected_counts = {
        "rules": sum(1 for n in pf.nodes if n.node_type == "rule"),
        "sub_rules": sum(1 for n in pf.nodes if n.node_type == "sub_rule"),
        "schedules": sum(1 for n in pf.nodes if n.node_type == "schedule"),
        "hierarchy_nodes": len(pf.nodes), "requirements": len(pf.requirements),
    }
    pf.parser_notes.append(
        f"Parsed DPDP Rules 2025 from PDF: {pf.expected_counts['rules']} rules, "
        f"{pf.expected_counts['sub_rules']} sub-rules, {pf.expected_counts['schedules']} schedules. "
        f"Licence review of Gazette of India reproduction terms still required.")
    return pf


def _dpdp_req(pf: ParsedFramework, nid: str, parent_ref: str, text: str, anchor: str, req_keys: set) -> None:
    low = text.lower()
    if not any(k in low for k in ("shall", "must", "is required", "may not")):
        return
    key = f"DPDP-R-{re.sub(r'[^A-Za-z0-9]+', '-', nid).strip('-').upper()}"
    if key in req_keys:
        return
    req_keys.add(key)
    otype = "OBLIGATION"
    if "shall not" in low or "may not" in low:
        otype = "PROHIBITION"
    elif any(k in low for k in ("intimate", "inform", "notify", "report")):
        otype = "REPORTING_REQUIREMENT"
    roles = []
    if "data fiduciary" in low:
        roles.append("data_fiduciary")
    if "data processor" in low:
        roles.append("data_processor")
    if "consent manager" in low:
        roles.append("consent_manager")
    pf.requirements.append(ParsedRequirement(
        requirement_key=key,
        node_official_id=nid, source_reference=nid, source_text=text,
        normalized_requirement=f"[{nid}] {text[:400]}", obligation_type=otype,
        subject_roles=roles, who_is_obligated=", ".join(roles) or None, mandatory=True,
        domain="India DPDP", source_anchor_url=anchor,
        evidence_expectations=[{"type": "Compliance Record",
                               "description": f"Records demonstrating compliance with {nid}."}],
        test_method="Legal/compliance review against the cited rule; verify implementing measures and records.",
    ))
