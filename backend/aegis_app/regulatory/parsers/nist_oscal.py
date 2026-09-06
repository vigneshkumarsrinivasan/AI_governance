"""Parser for NIST OSCAL control catalogs (SP 800-53 Rev 5, and 800-161 profiles).

Source format: OSCAL JSON (official usnistgov/oscal-content). Licence: U.S.
Government work / public domain -> full reproduction permitted.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from aegis_app.regulatory.parsers.base import ParsedFramework, ParsedNode, ParsedRequirement

_CONTROL_URL = "https://csrc.nist.gov/projects/cprt/catalog#/cprt/framework/version/SP_800_53_5_2_0/home?element={id}"
_INSERT_RE = re.compile(r"\{\{\s*insert:\s*param,\s*([A-Za-z0-9._-]+)\s*\}\}")


def _param_index(control: dict) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in control.get("params", []) or []:
        label = p.get("label")
        if not label and p.get("select"):
            choices = p["select"].get("choice", [])
            how = p["select"].get("how-many")
            joiner = " or " if how == "one" else " and/or "
            label = f"[{joiner.join(choices)}]" if choices else "[Assignment]"
        if not label and p.get("values"):
            label = ", ".join(p["values"])
        out[p["id"]] = label or f"[{p['id']}]"
    return out


def _subst(text: str, params: Dict[str, str]) -> str:
    return _INSERT_RE.sub(lambda m: params.get(m.group(1), f"[{m.group(1)}]"), text or "")


def _render_part(part: dict, params: Dict[str, str], depth: int = 0) -> str:
    lines: List[str] = []
    prose = part.get("prose")
    prefix = ""
    for prop in part.get("props", []) or []:
        if prop.get("name") == "label":
            prefix = prop["value"] + " "
    if prose:
        lines.append(("  " * depth) + prefix + _subst(prose, params))
    for sub in part.get("parts", []) or []:
        lines.append(_render_part(sub, params, depth + 1))
    return "\n".join(x for x in lines if x)


def _statement_text(control: dict, params: Dict[str, str]) -> str:
    for part in control.get("parts", []) or []:
        if part.get("name") == "statement":
            return _render_part(part, params).strip()
    return ""


def _guidance_text(control: dict, params: Dict[str, str]) -> str:
    for part in control.get("parts", []) or []:
        if part.get("name") == "guidance":
            return _subst(part.get("prose", ""), params).strip()
    return ""


def _related(control: dict) -> List[str]:
    out = []
    for link in control.get("links", []) or []:
        if link.get("rel") == "related":
            out.append(link["href"].lstrip("#").upper())
    return out


def _walk_controls(controls: List[dict], parent_id: str, family_id: str, pf: ParsedFramework,
                   ordinal_start: int) -> int:
    ordinal = ordinal_start
    for control in controls:
        cid = control["id"]                      # "ac-2" or "ac-2.1"
        official = cid.upper().replace(".", "(") + (")" if "." in cid else "")
        is_enh = "." in cid
        params = _param_index(control)
        statement = _statement_text(control, params)
        guidance = _guidance_text(control, params)
        related = _related(control)
        withdrawn = any(p.get("name") == "status" and p.get("value") == "withdrawn"
                        for p in control.get("props", []) or [])

        pf.nodes.append(ParsedNode(
            official_id=official,
            node_type="control_enhancement" if is_enh else "control",
            label=control.get("title"),
            parent_official_id=parent_id,
            ordinal=ordinal,
            source_text="\n\n".join(x for x in [statement, ("Discussion: " + guidance) if guidance else ""] if x),
            source_anchor_url=_CONTROL_URL.format(id=cid),
            cross_references=related,
            extra={"withdrawn": withdrawn, "family": family_id},
        ))
        ordinal += 1

        if not withdrawn and statement:
            pf.requirements.append(ParsedRequirement(
                requirement_key=f"NIST-80053-{official}",
                node_official_id=official,
                source_reference=f"{official} {control.get('title')}",
                source_text=statement,
                normalized_requirement=(
                    f"Implement NIST SP 800-53 control {official} ({control.get('title')}): {statement}"
                    if len(statement) < 600 else
                    f"Implement NIST SP 800-53 control {official} ({control.get('title')}) as stated in the control text."
                ),
                obligation_type="SECURITY_REQUIREMENT",
                mandatory=not is_enh,
                domain=family_id.upper(),
                source_anchor_url=_CONTROL_URL.format(id=cid),
                evidence_expectations=[
                    {"type": "Control Implementation Statement", "description": f"How {official} is implemented for this system."},
                    {"type": "Assessment Evidence", "description": f"Assessor evidence per SP 800-53A objectives for {official}."},
                ],
                test_method="SP 800-53A assessment objectives (examine / interview / test).",
                extra={"withdrawn": False, "control_enhancement": is_enh, "related_controls": related},
            ))

        child = control.get("controls", []) or []
        if child:
            ordinal = _walk_controls(child, official, family_id, pf, ordinal)
    return ordinal


def parse(raw: bytes, manifest_entry: Dict[str, Any]) -> ParsedFramework:
    catalog = json.loads(raw.decode("utf-8"))["catalog"]
    version_label = f"Rev 5 ({catalog['metadata']['version']})"

    pf = ParsedFramework(
        framework_key=manifest_entry["framework_key"],
        version_label=version_label,
        framework_name=manifest_entry["framework_name"],
        framework_type=manifest_entry["framework_type"],
        publication_date=manifest_entry.get("publication_date"),
        effective_date=manifest_entry.get("effective_date"),
    )

    root_id = "NIST-SP-800-53"
    pf.nodes.append(ParsedNode(
        official_id=root_id, node_type="framework",
        label=catalog["metadata"]["title"],
        source_anchor_url="https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final",
    ))

    families = catalog.get("groups", [])
    n_base = n_enh = 0
    for i, group in enumerate(families):
        fam_official = group["id"].upper()
        pf.nodes.append(ParsedNode(
            official_id=fam_official, node_type="control_family",
            label=group["title"], parent_official_id=root_id, ordinal=i,
            source_anchor_url=_CONTROL_URL.format(id=group["id"]),
        ))
        _walk_controls(group.get("controls", []), fam_official, group["id"], pf, 0)

    for n in pf.nodes:
        if n.node_type == "control":
            n_base += 1
        elif n.node_type == "control_enhancement":
            n_enh += 1

    pf.expected_counts = {
        "control_families": len(families),
        "base_controls": n_base,
        "control_enhancements": n_enh,
        "controls_total": n_base + n_enh,
        "hierarchy_nodes": len(pf.nodes),
        "requirements": len(pf.requirements),
    }
    pf.parser_notes.append(
        f"Parsed OSCAL catalog {catalog['metadata']['version']}: {len(families)} families, "
        f"{n_base} base controls, {n_enh} enhancements."
    )
    return pf
