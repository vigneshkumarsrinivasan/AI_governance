"""Normalized parser output types shared by every framework parser."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


@dataclass
class ParsedNode:
    official_id: str                       # verbatim numbering: "Article 9", "AC-2(1)", "AML.T0051"
    node_type: str                         # NODE_TYPES
    label: Optional[str] = None
    parent_official_id: Optional[str] = None
    ordinal: int = 0
    source_text: Optional[str] = None      # OFFICIAL SOURCE (only if licence permits reproduction)
    platform_summary: Optional[str] = None  # PLATFORM INTERPRETATION
    source_anchor_url: Optional[str] = None
    cross_references: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedRequirement:
    requirement_key: str
    node_official_id: Optional[str]
    source_reference: str
    normalized_requirement: str
    source_text: Optional[str] = None
    obligation_type: str = "OBLIGATION"
    subject_roles: List[str] = field(default_factory=list)
    who_is_obligated: Optional[str] = None
    trigger: Optional[str] = None
    exceptions: Optional[str] = None
    mandatory: bool = True
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    temporal_state: str = "CURRENTLY_APPLICABLE"
    evidence_expectations: List[Dict[str, str]] = field(default_factory=list)
    test_method: Optional[str] = None
    domain: Optional[str] = None
    source_anchor_url: Optional[str] = None
    extraction_method: str = "MACHINE_EXTRACTED"
    interpretation_label: str = "PLATFORM_INTERPRETATION"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDefinition:
    term: str
    definition_text: Optional[str]
    source_reference: Optional[str] = None
    source_anchor_url: Optional[str] = None
    context: Optional[str] = None
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None


@dataclass
class ParsedFramework:
    framework_key: str
    version_label: str
    framework_name: str
    framework_type: str
    publication_date: Optional[str] = None
    effective_date: Optional[str] = None
    application_dates: Dict[str, str] = field(default_factory=dict)
    nodes: List[ParsedNode] = field(default_factory=list)
    requirements: List[ParsedRequirement] = field(default_factory=list)
    definitions: List[ParsedDefinition] = field(default_factory=list)
    # expected_counts are DERIVED FROM THE SOURCE (spec section 5, section 39) - never hard-coded guesses
    expected_counts: Dict[str, int] = field(default_factory=dict)
    parser_notes: List[str] = field(default_factory=list)

    def sanity_check(self) -> List[str]:
        """Cheap structural checks the parser itself can assert before hand-off."""
        problems: List[str] = []
        ids = [n.official_id for n in self.nodes]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            problems.append(f"duplicate node official_id(s): {sorted(dupes)[:10]}")
        idset = set(ids)
        for n in self.nodes:
            if n.parent_official_id and n.parent_official_id not in idset:
                problems.append(f"node {n.official_id!r} has orphan parent {n.parent_official_id!r}")
        rkeys = [r.requirement_key for r in self.requirements]
        rdupes = {i for i in rkeys if rkeys.count(i) > 1}
        if rdupes:
            problems.append(f"duplicate requirement_key(s): {sorted(rdupes)[:10]}")
        for r in self.requirements:
            if r.node_official_id and r.node_official_id not in idset:
                problems.append(f"requirement {r.requirement_key!r} references missing node {r.node_official_id!r}")
            if not (r.normalized_requirement or "").strip():
                problems.append(f"requirement {r.requirement_key!r} has empty normalized_requirement")
        return problems
