"""Persist a ParsedFramework + its SourceArtifact into the regulatory tables."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from aegis_app.regulatory import PARSER_VERSION, SCHEMA_VERSION, VALIDATION_VERSION
from aegis_app.regulatory.manifest import store_source_text
from aegis_app.regulatory.parsers.base import ParsedFramework, sha256_text
from aegis_app.models.regulatory import (
    FrameworkVersion, FrameworkNode, RegulatoryRequirement, RegulatoryDefinition,
    RegulatorySource, SourceArtifact,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ImmutableVersionError(RuntimeError):
    """Raised when trying to re-ingest a PUBLISHED framework version (spec section 59)."""


def persist(session: Session, pf: ParsedFramework, *, source: RegulatorySource,
            artifact: SourceArtifact, manifest_entry: dict) -> FrameworkVersion:
    can_show_text = store_source_text(pf.framework_key)

    existing: Optional[FrameworkVersion] = session.execute(
        select(FrameworkVersion).where(
            FrameworkVersion.framework_key == pf.framework_key,
            FrameworkVersion.version_label == pf.version_label,
        )
    ).scalar_one_or_none()

    if existing and existing.published_status == "PUBLISHED":
        raise ImmutableVersionError(
            f"{pf.framework_key} {pf.version_label} is PUBLISHED and immutable; "
            f"ingest a new version_label or run the change-review workflow."
        )
    if existing:
        session.delete(existing)   # DRAFT re-ingest: replace in place
        session.flush()

    fv = FrameworkVersion(
        framework_key=pf.framework_key,
        framework_name=pf.framework_name,
        framework_family=manifest_entry["framework_family"],
        authority=manifest_entry["authority"],
        jurisdiction=manifest_entry["jurisdiction"],
        framework_type=pf.framework_type,
        version_label=pf.version_label,
        version_ordinal=1,
        publication_date=pf.publication_date,
        effective_date=pf.effective_date,
        application_dates=pf.application_dates or manifest_entry.get("application_dates", {}),
        parser_version=PARSER_VERSION,
        schema_version=SCHEMA_VERSION,
        validation_version=VALIDATION_VERSION,
        expected_counts=pf.expected_counts,
        ingested_counts={},
        published_counts={},
        coverage={},
        validation_status="UNVERIFIED",
        review_status="NOT_REVIEWED",
        published_status="DRAFT",
        is_current=False,
        source_manifest={
            "documents": manifest_entry.get("documents", []),
            "licence": manifest_entry.get("licence", {}),
            "ingestion_status": manifest_entry.get("ingestion_status"),
            "parser_notes": pf.parser_notes,
        },
    )
    session.add(fv)
    session.flush()

    # --- nodes (two passes so parent ids resolve) ---
    node_by_official: Dict[str, FrameworkNode] = {}
    for pn in pf.nodes:
        text = pn.source_text if can_show_text else None
        n = FrameworkNode(
            framework_version_id=fv.id,
            node_type=pn.node_type,
            official_id=pn.official_id,
            label=pn.label,
            ordinal=pn.ordinal,
            source_text=text,
            source_text_available=bool(pn.source_text) and can_show_text,
            platform_summary=pn.platform_summary,
            source_id=source.id,
            source_artifact_id=artifact.id,
            source_anchor_url=pn.source_anchor_url,
            source_hash=sha256_text(pn.source_text or ""),
            cross_references=pn.cross_references,
            extra=pn.extra,
        )
        session.add(n)
        node_by_official[pn.official_id] = n
    session.flush()

    for pn in pf.nodes:
        n = node_by_official[pn.official_id]
        if pn.parent_official_id and pn.parent_official_id in node_by_official:
            parent = node_by_official[pn.parent_official_id]
            n.parent_id = parent.id
            n.depth = (parent.depth or 0) + 1
            n.path = f"{parent.path or parent.official_id}/{pn.official_id}"
        else:
            n.path = pn.official_id
    session.flush()

    # --- definitions ---
    for pd in pf.definitions:
        session.add(RegulatoryDefinition(
            framework_version_id=fv.id,
            term=pd.term,
            definition_text=pd.definition_text if can_show_text else None,
            definition_available=bool(pd.definition_text) and can_show_text,
            source_reference=pd.source_reference,
            source_anchor_url=pd.source_anchor_url,
            context=pd.context,
            effective_from=pd.effective_from,
            effective_until=pd.effective_until,
            source_hash=sha256_text(pd.definition_text or ""),
        ))

    # --- requirements ---
    for pr in pf.requirements:
        node = node_by_official.get(pr.node_official_id) if pr.node_official_id else None
        session.add(RegulatoryRequirement(
            framework_version_id=fv.id,
            node_id=node.id if node else None,
            requirement_key=pr.requirement_key,
            source_reference=pr.source_reference,
            source_parent_reference=pr.node_official_id,
            source_text=pr.source_text if can_show_text else None,
            source_text_available=bool(pr.source_text) and can_show_text,
            normalized_requirement=pr.normalized_requirement,
            interpretation_label=pr.interpretation_label,
            obligation_type=pr.obligation_type,
            subject_roles=pr.subject_roles,
            who_is_obligated=pr.who_is_obligated,
            trigger=pr.trigger,
            exceptions=pr.exceptions,
            mandatory=pr.mandatory,
            jurisdiction=manifest_entry["jurisdiction"],
            effective_from=pr.effective_from,
            effective_until=pr.effective_until,
            temporal_state=pr.temporal_state,
            applicability_logic={},
            evidence_expectations=pr.evidence_expectations,
            test_method=pr.test_method,
            source_id=source.id,
            source_artifact_id=artifact.id,
            source_anchor_url=pr.source_anchor_url,
            source_hash=sha256_text(pr.source_text or pr.normalized_requirement),
            extraction_method=pr.extraction_method,
            review_status=pr.extraction_method if pr.extraction_method in
            ("MACHINE_EXTRACTED",) else "MACHINE_EXTRACTED",
            domain=pr.domain,
            extra=pr.extra,
        ))

    fv.ingested_counts = {
        "hierarchy_nodes": len(pf.nodes),
        "requirements": len(pf.requirements),
        "definitions": len(pf.definitions),
        "requirements_with_source_text": sum(1 for r in pf.requirements if r.source_text and can_show_text),
    }
    session.flush()
    return fv
