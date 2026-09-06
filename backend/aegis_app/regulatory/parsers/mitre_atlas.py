"""Parser for the official MITRE ATLAS structured dataset.

Handles the current ATLAS schema (format-version 6.x: object maps + a
``relationships`` block) and falls back to the legacy ``matrices`` schema.
Source: the latest published release of github.com/mitre-atlas/atlas-data.
Licence: Apache-2.0 (atlas-data repo) - reproduction permitted with attribution.
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List

import yaml

from aegis_app.regulatory.parsers.base import ParsedFramework, ParsedNode, ParsedRequirement

_TECH_URL = "https://atlas.mitre.org/techniques/{id}"
_TACTIC_URL = "https://atlas.mitre.org/tactics/{id}"
_MIT_URL = "https://atlas.mitre.org/mitigations/{id}"
_CS_URL = "https://atlas.mitre.org/studies/{id}"


def _s(v: Any) -> str:
    return (str(v) if v is not None else "").strip()


def _maybe_list(v: Any) -> List[Any]:
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.startswith("["):
        try:
            return ast.literal_eval(v)
        except Exception:
            return []
    return []


def _rel_index(relationships: Any) -> Dict[str, List[dict]]:
    """Return {relationship_type: [{source, target}]}."""
    out: Dict[str, List[dict]] = {}
    if isinstance(relationships, dict):
        for _src, block in relationships.items():
            for rtype, items in (block or {}).items():
                for it in _maybe_list(items) or (items if isinstance(items, list) else []):
                    if isinstance(it, dict):
                        out.setdefault(it.get("relationship-type", rtype), []).append(it)
    elif isinstance(relationships, list):
        for it in relationships:
            if isinstance(it, dict):
                out.setdefault(it.get("relationship-type", "related"), []).append(it)
    return out


def parse(raw: bytes, manifest_entry: Dict[str, Any]) -> ParsedFramework:
    data = yaml.safe_load(raw.decode("utf-8"))
    if "matrices" in data:
        return _parse_legacy(data, manifest_entry)
    return _parse_v6(data, manifest_entry)


# --------------------------------------------------------------------------
def _parse_v6(data: dict, me: Dict[str, Any]) -> ParsedFramework:
    coll = data.get("collection", {})
    version_label = _s(coll.get("version")) or me["version_label"]
    tactics: Dict[str, dict] = data.get("tactics", {})
    techniques: Dict[str, dict] = data.get("techniques", {})
    mitigations: Dict[str, dict] = data.get("mitigations", {})
    case_studies: Dict[str, dict] = data.get("case-studies", {})
    rels = _rel_index(data.get("relationships", {}))

    tech_tactics: Dict[str, List[str]] = {}
    for r in rels.get("achieves", []):
        tech_tactics.setdefault(r["source"], []).append(r["target"])
    sub_parent: Dict[str, str] = {r["source"]: r["target"] for r in rels.get("specializes", [])}
    mit_for_tech: Dict[str, List[str]] = {}
    for r in rels.get("mitigates", []):
        mit_for_tech.setdefault(r["target"], []).append(r["source"])
    cs_for_tech: Dict[str, List[str]] = {}
    for r in rels.get("employs", []):
        cs_for_tech.setdefault(r["target"], []).append(r["source"])

    pf = ParsedFramework(
        framework_key="mitre_atlas", version_label=version_label,
        framework_name=me["framework_name"], framework_type=me["framework_type"],
        publication_date=_s(coll.get("created-date")) or me.get("publication_date"),
        effective_date=_s(coll.get("modified-date")) or me.get("effective_date"),
    )
    root_id = f"ATLAS-{version_label}"
    pf.nodes.append(ParsedNode(official_id=root_id, node_type="framework",
                               label=f"MITRE ATLAS Matrix ({version_label})",
                               source_anchor_url="https://atlas.mitre.org/matrices/ATLAS",
                               platform_summary=_s(coll.get("description"))))

    tactic_name = {tid: _s(t.get("name")) for tid, t in tactics.items()}
    for i, (tid, t) in enumerate(tactics.items()):
        pf.nodes.append(ParsedNode(official_id=tid, node_type="tactic", label=_s(t.get("name")),
                                   parent_official_id=root_id, ordinal=i,
                                   source_text=_s(t.get("description")),
                                   source_anchor_url=_TACTIC_URL.format(id=tid)))

    n_sub = 0
    n_top = 0
    for i, (tid, tech) in enumerate(techniques.items()):
        parent_tech = sub_parent.get(tid) or (tid.rsplit(".", 1)[0] if "." in tid[6:] else None)
        is_sub = bool(parent_tech)
        tac_ids = tech_tactics.get(tid, [])
        if is_sub:
            n_sub += 1
            parent_id = parent_tech
        else:
            n_top += 1
            parent_id = next((x for x in tac_ids if x in tactics), root_id)
        node_tactics = [tactic_name.get(x, x) for x in tac_ids]
        pf.nodes.append(ParsedNode(
            official_id=tid, node_type="subtechnique" if is_sub else "technique",
            label=_s(tech.get("name")), parent_official_id=parent_id, ordinal=i,
            source_text=_s(tech.get("description")), source_anchor_url=_TECH_URL.format(id=tid),
            cross_references=tac_ids,
            extra={"tactics": node_tactics, "maturity": tech.get("maturity"),
                   "platforms": _maybe_list(tech.get("platforms")),
                   "attack_reference": tech.get("attack-reference"),
                   "case_studies": cs_for_tech.get(tid, [])},
        ))
        linked_mits = mit_for_tech.get(tid, [])
        evidence = [{"type": "ATLAS Mitigation",
                     "description": f"{mid} {_s(mitigations.get(mid, {}).get('name'))}"} for mid in linked_mits] \
            or [{"type": "Threat Assessment", "description": f"Documented assessment of exposure to {tid}."}]
        tstr = ", ".join(node_tactics) if node_tactics else "AI/ML lifecycle"
        pf.requirements.append(ParsedRequirement(
            requirement_key=f"ATLAS-{tid}", node_official_id=tid, source_reference=tid,
            source_text=_s(tech.get("description")),
            normalized_requirement=(
                f"Assess whether this AI system is exposed to the adversary technique "
                f"“{_s(tech.get('name'))}” ({tid}; tactic: {tstr}) and, where exposure exists, apply the "
                f"applicable ATLAS mitigations and document residual risk."),
            obligation_type="MITIGATION" if linked_mits else "TECHNIQUE",
            mandatory=False, domain=tstr, source_anchor_url=_TECH_URL.format(id=tid),
            evidence_expectations=evidence,
            test_method="Adversarial/red-team evaluation targeting this technique; review of deployed mitigations.",
            extra={"linked_mitigations": linked_mits, "case_studies": cs_for_tech.get(tid, [])},
        ))

    for i, (mid, m) in enumerate(mitigations.items()):
        pf.nodes.append(ParsedNode(
            official_id=mid, node_type="mitigation", label=_s(m.get("name")),
            parent_official_id=root_id, ordinal=1000 + i, source_text=_s(m.get("description")),
            source_anchor_url=_MIT_URL.format(id=mid),
            cross_references=[r["target"] for r in rels.get("mitigates", []) if r["source"] == mid],
            extra={"categories": _maybe_list(m.get("categories")),
                   "lifecycle_phases": _maybe_list(m.get("lifecycle-phases"))},
        ))

    for i, (cid, cs) in enumerate(case_studies.items()):
        pf.nodes.append(ParsedNode(
            official_id=cid, node_type="case_study", label=_s(cs.get("name")),
            parent_official_id=root_id, ordinal=2000 + i, source_text=_s(cs.get("description")),
            source_anchor_url=_CS_URL.format(id=cid),
            cross_references=[r["target"] for r in rels.get("employs", []) if r["source"] == cid],
            extra={"type": cs.get("type"), "actor": _s(cs.get("actor")), "target": _s(cs.get("target")),
                   "incident_date": _s(cs.get("date"))},
        ))

    pf.expected_counts = {
        "tactics": len(tactics), "techniques": n_top, "subtechniques": n_sub,
        "mitigations": len(mitigations), "case_studies": len(case_studies),
        "relationships": sum(len(v) for v in rels.values()),
        "hierarchy_nodes": len(pf.nodes), "requirements": len(pf.requirements),
    }
    pf.parser_notes.append(
        f"Parsed ATLAS v{version_label} (schema {data.get('format-version')}): {len(tactics)} tactics, "
        f"{n_top} techniques, {n_sub} subtechniques, {len(mitigations)} mitigations, "
        f"{len(case_studies)} case studies, {pf.expected_counts['relationships']} relationships.")
    return pf


# --------------------------------------------------------------------------
def _parse_legacy(data: dict, me: Dict[str, Any]) -> ParsedFramework:
    matrix = data["matrices"][0]
    tactics = matrix.get("tactics", [])
    techniques = matrix.get("techniques", [])
    mitigations = matrix.get("mitigations", [])
    case_studies = data.get("case-studies", [])
    version_label = _s(data.get("version")) or me["version_label"]

    pf = ParsedFramework(framework_key="mitre_atlas", version_label=version_label,
                         framework_name=me["framework_name"], framework_type=me["framework_type"],
                         publication_date=me.get("publication_date"), effective_date=me.get("effective_date"))
    root_id = f"ATLAS-{version_label}"
    pf.nodes.append(ParsedNode(official_id=root_id, node_type="framework",
                               label=f"MITRE ATLAS Matrix ({version_label})",
                               source_anchor_url="https://atlas.mitre.org/matrices/ATLAS"))
    tactic_name = {t["id"]: t["name"] for t in tactics}
    for i, t in enumerate(tactics):
        pf.nodes.append(ParsedNode(official_id=t["id"], node_type="tactic", label=t["name"],
                                   parent_official_id=root_id, ordinal=i, source_text=_s(t.get("description")),
                                   source_anchor_url=_TACTIC_URL.format(id=t["id"])))
    known_tac = set(tactic_name)
    mit_for_tech: Dict[str, List[dict]] = {}
    for m in mitigations:
        for link in m.get("techniques", []) or []:
            mit_for_tech.setdefault(link["id"], []).append({"mitigation_id": m["id"], "mitigation_name": m["name"]})
    n_sub = 0
    for i, tech in enumerate(techniques):
        tid = tech["id"]
        parent_tech = tech.get("specializes") or tech.get("subtechnique-of")
        is_sub = bool(parent_tech)
        if is_sub:
            n_sub += 1
        tac_ids = tech.get("tactics", []) or []
        parent_id = parent_tech if is_sub else next((x for x in tac_ids if x in known_tac), root_id)
        pf.nodes.append(ParsedNode(official_id=tid, node_type="subtechnique" if is_sub else "technique",
                                   label=tech["name"], parent_official_id=parent_id, ordinal=i,
                                   source_text=_s(tech.get("description")),
                                   source_anchor_url=_TECH_URL.format(id=tid), cross_references=tac_ids))
        linked = mit_for_tech.get(tid, [])
        pf.requirements.append(ParsedRequirement(
            requirement_key=f"ATLAS-{tid}", node_official_id=tid, source_reference=tid,
            source_text=_s(tech.get("description")),
            normalized_requirement=f"Assess exposure to ATLAS technique {tech['name']} ({tid}) and apply mitigations.",
            obligation_type="MITIGATION" if linked else "TECHNIQUE", mandatory=False,
            source_anchor_url=_TECH_URL.format(id=tid),
            evidence_expectations=[{"type": "ATLAS Mitigation", "description": f"{m['mitigation_id']} {m['mitigation_name']}"} for m in linked]
            or [{"type": "Threat Assessment", "description": f"Assessment of exposure to {tid}."}],
            test_method="Adversarial/red-team evaluation targeting this technique."))
    for i, m in enumerate(mitigations):
        pf.nodes.append(ParsedNode(official_id=m["id"], node_type="mitigation", label=m["name"],
                                   parent_official_id=root_id, ordinal=1000 + i, source_text=_s(m.get("description")),
                                   source_anchor_url=_MIT_URL.format(id=m["id"])))
    for i, cs in enumerate(case_studies):
        pf.nodes.append(ParsedNode(official_id=cs["id"], node_type="case_study", label=cs["name"],
                                   parent_official_id=root_id, ordinal=2000 + i, source_text=_s(cs.get("summary")),
                                   source_anchor_url=_CS_URL.format(id=cs["id"])))
    top = [t for t in techniques if not (t.get("specializes") or t.get("subtechnique-of"))]
    pf.expected_counts = {"tactics": len(tactics), "techniques": len(top), "subtechniques": n_sub,
                          "mitigations": len(mitigations), "case_studies": len(case_studies),
                          "hierarchy_nodes": len(pf.nodes), "requirements": len(pf.requirements)}
    pf.parser_notes.append(f"Parsed ATLAS v{version_label} (legacy schema).")
    return pf
