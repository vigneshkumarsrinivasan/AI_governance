"""Generic parser for NIST CPRT (Cybersecurity & Privacy Reference Tool) graph
bundles. Used for CSF 2.0 and SSDF SP 800-218. Source: official CPRT JSON API.
Licence: U.S. Government work / public domain.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from aegis_app.regulatory.parsers.base import ParsedFramework, ParsedNode, ParsedRequirement

# framework_key -> config
_CFG = {
    "nist_csf_2": {
        "version_label": "2.0",
        "root_id": "NIST-CSF-2.0",
        "root_label": "NIST Cybersecurity Framework (CSF) 2.0",
        "anchor": "https://csrc.nist.gov/pubs/cswp/29/final",
        "type_map": {"function": "function", "category": "category", "subcategory": "subcategory",
                     "implementation_example": "example"},
        "requirement_type": "subcategory",
        "req_prefix": "NIST-CSF2",
        "skip_types": {"party", "sort", "withdraw_reason", "ref_item", "ref_doc"},
        "count_keys": {"function": "functions", "category": "categories", "subcategory": "subcategories"},
        "obligation": "SECURITY_REQUIREMENT",
        "req_verb": "Achieve CSF 2.0 outcome",
    },
    "nist_sp_800_218": {
        "version_label": "1.1",
        "root_id": "NIST-SP-800-218",
        "root_label": "NIST SP 800-218 Secure Software Development Framework (SSDF) v1.1",
        "anchor": "https://csrc.nist.gov/pubs/sp/800/218/final",
        "type_map": {"group": "practice", "practice": "practice", "task": "task", "example": "example"},
        "requirement_type": "task",
        "req_prefix": "NIST-SSDF",
        "skip_types": {"ref_item", "ref_doc", "sort", "party"},
        "count_keys": {"group": "practice_groups", "practice": "practices", "task": "tasks"},
        "obligation": "SECURITY_REQUIREMENT",
        "req_verb": "Perform SSDF task",
    },
}


def parse(raw: bytes, manifest_entry: Dict[str, Any]) -> ParsedFramework:
    bundle = json.loads(raw.decode("utf-8"))
    fk = manifest_entry["framework_key"]
    cfg = _CFG[fk]
    tree: List[dict] = bundle["tree"]

    pf = ParsedFramework(
        framework_key=fk,
        version_label=cfg["version_label"],
        framework_name=manifest_entry["framework_name"],
        framework_type=manifest_entry["framework_type"],
        publication_date=manifest_entry.get("publication_date"),
        effective_date=manifest_entry.get("effective_date"),
    )
    root_id = cfg["root_id"]
    pf.nodes.append(ParsedNode(official_id=root_id, node_type="framework",
                               label=cfg["root_label"], source_anchor_url=cfg["anchor"]))

    counts: Dict[str, int] = {}
    seen: set = set()
    req_seen: set = set()
    known_types = set(cfg["type_map"]) | {"framework", "function"}

    def recurse(elements: List[dict], parent_id: str, depth: int) -> None:
        for i, el in enumerate(elements):
            etype = el.get("elementTypeIdentifier")
            ident = el.get("elementIdentifier")
            # CPRT deep-graph responses splice in withdrawn CSF 1.1 items and
            # "where did it go" cross-reference nodes - skip those whole subtrees.
            if etype in cfg["skip_types"] or (ident or "").startswith("WR-") or "withdraw" in (etype or ""):
                continue
            if etype not in known_types:
                continue
            # withdrawn CSF 1.1 categories/subcategories: empty text + a withdraw_reason child
            child_types = {c.get("elementTypeIdentifier") for c in (el.get("elements") or [])}
            if "withdraw_reason" in child_types or (
                etype in ("category", "subcategory") and not (el.get("text") or "").strip()
            ):
                continue
            if ident and ident in seen:
                continue  # this element (and its subtree) already ingested via its canonical parent
            node_type = cfg["type_map"].get(etype, etype)
            title = (el.get("title") or "").strip()
            text = (el.get("text") or "").strip()
            counts[etype] = counts.get(etype, 0) + 1

            if ident:
                seen.add(ident)
                pf.nodes.append(ParsedNode(
                    official_id=ident, node_type=node_type, label=title or ident,
                    parent_official_id=parent_id, ordinal=i,
                    source_text=text or None, source_anchor_url=cfg["anchor"],
                    extra={"cprt_type": etype},
                ))

            if etype == cfg["requirement_type"] and ident and ident not in req_seen:
                req_seen.add(ident)
                examples = [c.get("text", "").strip() for c in (el.get("elements") or [])
                            if c.get("elementTypeIdentifier") == "example"
                            or c.get("elementTypeIdentifier") == "implementation_example"]
                pf.requirements.append(ParsedRequirement(
                    requirement_key=f"{cfg['req_prefix']}-{ident}",
                    node_official_id=ident,
                    source_reference=f"{ident} {title}".strip(),
                    source_text=text or None,
                    normalized_requirement=f"{cfg['req_verb']} {ident} ({title}): {text}" if text
                    else f"{cfg['req_verb']} {ident} ({title}).",
                    obligation_type=cfg["obligation"],
                    mandatory=False,
                    domain=parent_id,
                    source_anchor_url=cfg["anchor"],
                    evidence_expectations=(
                        [{"type": "Implementation Example", "description": e} for e in examples if e]
                        or [{"type": "Outcome Evidence", "description": f"Evidence {ident} is satisfied."}]
                    ),
                    test_method="Assess whether the stated outcome/task is implemented and effective.",
                    extra={"implementation_examples": [e for e in examples if e]},
                ))

            if el.get("elements"):
                recurse(el["elements"], ident or parent_id, depth + 1)

    recurse(tree, root_id, 0)

    expected = {v: counts.get(k, 0) for k, v in cfg["count_keys"].items()}
    expected["hierarchy_nodes"] = len(pf.nodes)
    expected["requirements"] = len(pf.requirements)
    pf.expected_counts = expected
    pf.parser_notes.append(f"Parsed {fk} from CPRT {bundle.get('framework_version_identifier')}: " + ", ".join(
        f"{v}={expected[v]}" for v in cfg["count_keys"].values()))
    return pf
