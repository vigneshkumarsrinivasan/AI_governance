"""Parser for NIST AI RMF 1.0.

There is no official machine-readable release of AI RMF 1.0. This parser consumes
a committed fixture (fixtures/nist_ai_rmf_1_0.json) whose function/category
identifiers and category outcome statements were transcribed verbatim from
NIST AI 100-1 Appendix A and verified against the publication. Subcategory-level
normative text is intentionally not reproduced yet, which the validation engine
reflects by capping this pack below PRODUCTION_READY.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from aegis_app.regulatory.parsers.base import ParsedFramework, ParsedNode, ParsedRequirement

_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "nist_ai_rmf_1_0.json"
_ANCHOR = "https://airc.nist.gov/AI_RMF_Knowledge_Base/AI_RMF"


def parse(raw: bytes, manifest_entry: Dict[str, Any]) -> ParsedFramework:
    # ``raw`` is the archived fixture bytes (pipeline archives the fixture too).
    data = json.loads(raw.decode("utf-8")) if raw else json.loads(_FIXTURE.read_text("utf-8"))

    pf = ParsedFramework(
        framework_key="nist_ai_rmf",
        version_label=data["version_label"],
        framework_name=manifest_entry["framework_name"],
        framework_type=manifest_entry["framework_type"],
        publication_date=data.get("publication_date"),
        effective_date=manifest_entry.get("effective_date"),
    )
    root_id = "NIST-AI-RMF-1.0"
    pf.nodes.append(ParsedNode(official_id=root_id, node_type="framework",
                               label="NIST AI Risk Management Framework (AI RMF 1.0)",
                               source_anchor_url=_ANCHOR,
                               platform_summary=data.get("_transcription_note")))

    n_func = n_cat = n_sub = 0
    for fi, func in enumerate(data["functions"]):
        n_func += 1
        pf.nodes.append(ParsedNode(official_id=func["id"], node_type="function",
                                   label=func["title"], parent_official_id=root_id, ordinal=fi,
                                   source_text=func.get("text"), source_anchor_url=_ANCHOR))
        for ci, cat in enumerate(func["categories"]):
            n_cat += 1
            pf.nodes.append(ParsedNode(official_id=cat["id"], node_type="category",
                                       label=cat["title"], parent_official_id=func["id"], ordinal=ci,
                                       source_text=cat["title"], source_anchor_url=_ANCHOR))
            for si, sub_id in enumerate(cat.get("subcategories", [])):
                n_sub += 1
                pf.nodes.append(ParsedNode(
                    official_id=sub_id, node_type="subcategory", label=sub_id,
                    parent_official_id=cat["id"], ordinal=si,
                    source_text=None,
                    platform_summary="Subcategory normative text pending verified source (see pack note).",
                    source_anchor_url=_ANCHOR,
                    extra={"source_text_available": False},
                ))
            pf.requirements.append(ParsedRequirement(
                requirement_key=f"NIST-AIRMF-{cat['id'].replace(' ', '-')}",
                node_official_id=cat["id"],
                source_reference=cat["id"],
                source_text=cat["title"],
                normalized_requirement=(
                    f"Establish the AI RMF outcome for {cat['id']}: {cat['title']} "
                    f"(covering subcategories {', '.join(cat.get('subcategories', []))})."
                ),
                obligation_type="GOVERNANCE_REQUIREMENT",
                mandatory=False,
                domain=func["id"],
                source_anchor_url=_ANCHOR,
                evidence_expectations=[{"type": "AI RMF Profile Evidence",
                                       "description": f"Documented outcomes/artefacts for {cat['id']} subcategories."}],
                test_method="Assess implementation of each subcategory (AI RMF Playbook suggested actions).",
                extra={"subcategories": cat.get("subcategories", [])},
            ))

    pf.expected_counts = {
        "functions": 4,
        "categories": 19,
        "subcategories": n_sub,
        "hierarchy_nodes": len(pf.nodes),
        "requirements": len(pf.requirements),
        "_note": "counts self-derived from committed fixture (no official machine-readable AI RMF source)",
    }
    pf.parser_notes.append(
        f"AI RMF 1.0 fixture: {n_func} functions, {n_cat} categories, {n_sub} subcategory identifiers. "
        "Subcategory normative text NOT reproduced - pack capped below PRODUCTION_READY."
    )
    return pf
