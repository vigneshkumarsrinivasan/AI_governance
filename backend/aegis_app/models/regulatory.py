"""
Regulatory content data model.

This is the authoritative, source-traceable representation of laws, regulations
and frameworks. It is deliberately separate from the hand-authored demo content
in ``aegis_app/data/frameworks/*.json`` (which is being retired framework by
framework as real packs are ingested).

Design principles (from the platform build spec):
  * Every published node/requirement traces to a retrieved ``SourceArtifact``
    with a SHA-256 hash and retrieval timestamp.
  * Official source text and platform interpretation are stored in separate
    columns and never merged.
  * Historical framework versions are immutable once published.
  * A framework only becomes ``PRODUCTION_READY`` when its validation gate passes.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from aegis_app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Controlled vocabularies (kept as module constants, validated in services)
# ---------------------------------------------------------------------------
LICENCE_STATUSES = (
    "VERIFIED_REUSABLE",
    "VERIFIED_WITH_ATTRIBUTION",
    "VERIFIED_SHARE_ALIKE",
    "SOURCE_ONLY_NO_REDISTRIBUTION",
    "CUSTOMER_LICENCE_REQUIRED",
    "UNKNOWN",
)

FRAMEWORK_READINESS = (
    "MISSING",
    "PLACEHOLDER",
    "PARTIAL",
    "UNVERIFIED",
    "VERIFIED",
    "VALIDATED",
    "PRODUCTION_READY",
)

REQUIREMENT_REVIEW_STATES = (
    "MACHINE_EXTRACTED",
    "AI_NORMALIZED",
    "HUMAN_REVIEW_REQUIRED",
    "VERIFIED",
    "APPROVED",
    "REJECTED",
)

NODE_TYPES = (
    "framework", "part", "title", "chapter", "section", "article", "paragraph",
    "point", "subpoint", "annex", "annex_section", "recital",
    "function", "category", "subcategory",
    "control_family", "control", "control_enhancement",
    "practice", "task", "example",
    "tactic", "technique", "subtechnique", "mitigation", "case_study",
    "release", "risk", "principle", "rule", "sub_rule", "schedule",
    "governance_principle", "process_check", "test",
)

OBLIGATION_TYPES = (
    "DEFINITION", "CONTEXT", "RECITAL", "SCOPE", "OBLIGATION", "PROHIBITION",
    "RIGHT", "EXCEPTION", "REPORTING_REQUIREMENT", "DOCUMENTATION_REQUIREMENT",
    "GOVERNANCE_REQUIREMENT", "SECURITY_REQUIREMENT", "GUIDANCE", "TECHNIQUE",
    "MITIGATION", "TEST",
)

MAPPING_TYPES = ("EXACT", "STRONG", "PARTIAL", "RELATED")
MAPPING_STATES = ("AI_SUGGESTED", "REVIEW_REQUIRED", "APPROVED", "REJECTED")

TEMPORAL_STATES = (
    "CURRENTLY_APPLICABLE", "FUTURE_APPLICABLE", "TRANSITION_PERIOD",
    "SUPERSEDED", "NOT_APPLICABLE",
)


# ---------------------------------------------------------------------------
# Source & licence layer
# ---------------------------------------------------------------------------
class RegulatorySource(Base):
    """One authoritative source document tracked by the platform.

    Backed by ``framework_manifest.yaml`` and reconciled on every ingestion run.
    """
    __tablename__ = "regulatory_sources"

    id = Column(String(36), primary_key=True, default=_uuid)
    framework_key = Column(String(64), nullable=False, index=True)      # e.g. "mitre_atlas"
    framework_family = Column(String(64), nullable=False)               # e.g. "MITRE ATLAS"
    document_key = Column(String(96), nullable=False)                   # e.g. "atlas_yaml"
    document_name = Column(String(255), nullable=False)
    authority = Column(String(255), nullable=False)                     # e.g. "MITRE Corporation"
    jurisdiction = Column(String(128), nullable=False)
    document_type = Column(String(96), nullable=False)                  # Regulation | Directive | Voluntary Framework | ...
    canonical_identifier = Column(String(128), nullable=True)           # CELEX, SP number, ATLAS version tag

    official_url = Column(String(1000), nullable=False)
    machine_readable_url = Column(String(1000), nullable=True)
    source_format = Column(String(32), nullable=False, default="unknown")  # oscal_json | formex_xml | akoma_ntoso | yaml | html | pdf

    # Licence gate (spec section 3)
    copyright_owner = Column(String(255), nullable=True)
    licence_name = Column(String(255), nullable=True)
    licence_url = Column(String(1000), nullable=True)
    commercial_reuse_allowed = Column(Boolean, nullable=True)
    redistribution_allowed = Column(Boolean, nullable=True)
    modification_allowed = Column(Boolean, nullable=True)
    attribution_required = Column(Boolean, nullable=True)
    share_alike_required = Column(Boolean, nullable=True)
    third_party_material_present = Column(Boolean, default=False)
    licence_status = Column(String(48), nullable=False, default="UNKNOWN")
    licence_verified_at = Column(DateTime, nullable=True)
    licence_evidence_url = Column(String(1000), nullable=True)
    attribution_statement = Column(Text, nullable=True)

    # Applicability / temporal metadata
    publication_date = Column(String(32), nullable=True)
    effective_date = Column(String(32), nullable=True)
    application_dates = Column(JSON, default=dict)  # {"prohibitions": "2025-02-02", ...}

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    __table_args__ = (
        UniqueConstraint("framework_key", "document_key", name="uq_source_framework_document"),
    )

    artifacts = relationship("SourceArtifact", back_populates="source", cascade="all, delete-orphan")


class SourceArtifact(Base):
    """A concrete file retrieved from an official source at a point in time.

    Original bytes are archived on disk (``storage_path``); we never overwrite an
    existing artifact - a new retrieval always creates a new row.
    """
    __tablename__ = "regulatory_source_artifacts"

    id = Column(String(36), primary_key=True, default=_uuid)
    source_id = Column(String(36), ForeignKey("regulatory_sources.id", ondelete="CASCADE"), nullable=False, index=True)

    retrieved_url = Column(String(1000), nullable=False)
    retrieved_at = Column(DateTime, nullable=False, default=_now)
    http_status = Column(Integer, nullable=True)
    http_headers = Column(JSON, default=dict)
    mime_type = Column(String(128), nullable=True)
    file_name = Column(String(255), nullable=True)
    byte_size = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=False, index=True)
    previous_sha256 = Column(String(64), nullable=True)
    storage_path = Column(String(1000), nullable=False)
    parser_version = Column(String(32), nullable=True)
    retrieval_status = Column(String(48), nullable=False, default="RETRIEVED")
    # RETRIEVED | SOURCE_RETRIEVAL_BLOCKED | HASH_UNCHANGED | HASH_CHANGED
    fixture_backed = Column(Boolean, default=False)  # true if a committed offline fixture, not a live pull

    created_at = Column(DateTime, default=_now)

    source = relationship("RegulatorySource", back_populates="artifacts")


# ---------------------------------------------------------------------------
# Framework version + hierarchy
# ---------------------------------------------------------------------------
class FrameworkVersion(Base):
    """An immutable-once-published version of a framework family."""
    __tablename__ = "regulatory_framework_versions"

    id = Column(String(36), primary_key=True, default=_uuid)
    framework_key = Column(String(64), nullable=False, index=True)
    framework_name = Column(String(255), nullable=False)
    framework_family = Column(String(64), nullable=False)
    authority = Column(String(255), nullable=False)
    jurisdiction = Column(String(128), nullable=False)
    framework_type = Column(String(96), nullable=False)  # LAW | REGULATION | DIRECTIVE | VOLUNTARY_FRAMEWORK | VOLUNTARY_CODE | THREAT_KNOWLEDGE_BASE

    version_label = Column(String(96), nullable=False)   # "Rev 5.2.0", "2024/1689", "5.6.0", "1.0"
    version_ordinal = Column(Integer, default=1)
    publication_date = Column(String(32), nullable=True)
    effective_date = Column(String(32), nullable=True)
    application_dates = Column(JSON, default=dict)

    parser_version = Column(String(32), nullable=False, default="0.1.0")
    schema_version = Column(String(32), nullable=False, default="1.0.0")
    validation_version = Column(String(32), nullable=False, default="1.0.0")

    # Derived (not hand-set) counts, filled by ingestion
    expected_counts = Column(JSON, default=dict)   # from authoritative source structure
    ingested_counts = Column(JSON, default=dict)
    published_counts = Column(JSON, default=dict)

    # coverage_* are 0..1 fractions computed by the validation engine
    coverage = Column(JSON, default=dict)  # {"source":1.0,"hierarchy":1.0,"requirement_extraction":0.9,...}

    validation_status = Column(String(32), nullable=False, default="UNVERIFIED")  # FRAMEWORK_READINESS
    review_status = Column(String(32), nullable=False, default="NOT_REVIEWED")
    published_status = Column(String(24), nullable=False, default="DRAFT")  # DRAFT | PUBLISHED | DEPRECATED
    is_current = Column(Boolean, default=False, index=True)

    blocking_reasons = Column(JSON, default=list)  # human-readable strings if not production-ready

    source_manifest = Column(JSON, default=dict)   # snapshot of manifest entry at publish time
    created_at = Column(DateTime, default=_now)
    published_at = Column(DateTime, nullable=True)
    deprecated_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("framework_key", "version_label", name="uq_framework_version"),
    )

    nodes = relationship("FrameworkNode", back_populates="framework_version", cascade="all, delete-orphan")
    requirements = relationship("RegulatoryRequirement", back_populates="framework_version", cascade="all, delete-orphan")
    definitions = relationship("RegulatoryDefinition", back_populates="framework_version", cascade="all, delete-orphan")
    validations = relationship("FrameworkValidation", back_populates="framework_version", cascade="all, delete-orphan")


class FrameworkNode(Base):
    """A node in the original document hierarchy. Numbering is preserved exactly."""
    __tablename__ = "regulatory_framework_nodes"

    id = Column(String(36), primary_key=True, default=_uuid)
    framework_version_id = Column(String(36), ForeignKey("regulatory_framework_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("regulatory_framework_nodes.id", ondelete="CASCADE"), nullable=True, index=True)

    node_type = Column(String(48), nullable=False)         # NODE_TYPES
    official_id = Column(String(128), nullable=False, index=True)  # "Article 9", "AC-2", "AC-2(1)", "AML.T0051", "GOVERN 1.1"
    label = Column(String(512), nullable=True)             # title / heading
    ordinal = Column(Integer, default=0)                   # sibling order
    depth = Column(Integer, default=0)
    path = Column(String(1000), nullable=True)             # "eu_ai_act/ch-III/sec-2/art-9"

    # Spec section 10: official text and platform interpretation are separate columns
    source_text = Column(Text, nullable=True)              # OFFICIAL SOURCE - verbatim, redistribution-permitting sources only
    source_text_available = Column(Boolean, default=True)  # false when licence is SOURCE_ONLY_NO_REDISTRIBUTION
    platform_summary = Column(Text, nullable=True)         # PLATFORM INTERPRETATION

    source_id = Column(String(36), ForeignKey("regulatory_sources.id", ondelete="SET NULL"), nullable=True)
    source_artifact_id = Column(String(36), ForeignKey("regulatory_source_artifacts.id", ondelete="SET NULL"), nullable=True)
    source_anchor_url = Column(String(1000), nullable=True)  # deep link to the exact provision
    source_hash = Column(String(64), nullable=True)          # sha256 of the extracted source_text

    cross_references = Column(JSON, default=list)          # ["Article 6", "Annex III"]
    extra = Column(JSON, default=dict)                     # framework-specific metadata

    created_at = Column(DateTime, default=_now)

    __table_args__ = (
        Index("ix_node_fw_official", "framework_version_id", "official_id"),
    )

    framework_version = relationship("FrameworkVersion", back_populates="nodes")
    parent = relationship("FrameworkNode", remote_side=[id])
    requirements = relationship("RegulatoryRequirement", back_populates="node")


class RegulatoryDefinition(Base):
    """A defined term. Definitions are per-framework - never merged across laws."""
    __tablename__ = "regulatory_definitions"

    id = Column(String(36), primary_key=True, default=_uuid)
    framework_version_id = Column(String(36), ForeignKey("regulatory_framework_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    term = Column(String(255), nullable=False, index=True)
    definition_text = Column(Text, nullable=True)
    definition_available = Column(Boolean, default=True)
    source_reference = Column(String(255), nullable=True)   # "Article 3(1)"
    source_anchor_url = Column(String(1000), nullable=True)
    context = Column(Text, nullable=True)
    effective_from = Column(String(32), nullable=True)
    effective_until = Column(String(32), nullable=True)
    source_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=_now)

    framework_version = relationship("FrameworkVersion", back_populates="definitions")


# ---------------------------------------------------------------------------
# Requirements
# ---------------------------------------------------------------------------
class RegulatoryRequirement(Base):
    """An atomic, assessable requirement normalized from an operative provision."""
    __tablename__ = "regulatory_requirements"

    id = Column(String(36), primary_key=True, default=_uuid)
    framework_version_id = Column(String(36), ForeignKey("regulatory_framework_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(String(36), ForeignKey("regulatory_framework_nodes.id", ondelete="SET NULL"), nullable=True, index=True)

    requirement_key = Column(String(128), nullable=False, index=True)  # stable: "EU-AIA-ART-09", "NIST-80053-AC-2", "ATLAS-AML.T0051"
    source_reference = Column(String(255), nullable=False)             # "Article 9(1)"
    source_parent_reference = Column(String(255), nullable=True)
    source_text = Column(Text, nullable=True)                          # OFFICIAL SOURCE
    source_text_available = Column(Boolean, default=True)
    normalized_requirement = Column(Text, nullable=False)              # PLATFORM INTERPRETATION
    interpretation_label = Column(String(24), default="PLATFORM_INTERPRETATION")  # or AI_SUGGESTED

    obligation_type = Column(String(48), nullable=False, default="OBLIGATION")   # OBLIGATION_TYPES
    subject_roles = Column(JSON, default=list)   # ["provider", "deployer"] - per-framework role vocabulary
    who_is_obligated = Column(String(255), nullable=True)
    trigger = Column(Text, nullable=True)
    exceptions = Column(Text, nullable=True)
    mandatory = Column(Boolean, default=True)

    jurisdiction = Column(String(128), nullable=True)
    effective_from = Column(String(32), nullable=True)
    effective_until = Column(String(32), nullable=True)
    temporal_state = Column(String(32), default="CURRENTLY_APPLICABLE")

    applicability_logic = Column(JSON, default=dict)   # structured, explainable
    evidence_expectations = Column(JSON, default=list) # [{type, description}]
    test_method = Column(Text, nullable=True)

    source_id = Column(String(36), ForeignKey("regulatory_sources.id", ondelete="SET NULL"), nullable=True)
    source_artifact_id = Column(String(36), ForeignKey("regulatory_source_artifacts.id", ondelete="SET NULL"), nullable=True)
    source_anchor_url = Column(String(1000), nullable=True)
    source_hash = Column(String(64), nullable=True)

    extraction_method = Column(String(32), default="MACHINE_EXTRACTED")  # MACHINE_EXTRACTED | AI_NORMALIZED | MANUAL
    review_status = Column(String(32), nullable=False, default="MACHINE_EXTRACTED")  # REQUIREMENT_REVIEW_STATES
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    domain = Column(String(96), nullable=True)
    extra = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("framework_version_id", "requirement_key", name="uq_requirement_key_per_version"),
    )

    framework_version = relationship("FrameworkVersion", back_populates="requirements")
    node = relationship("FrameworkNode", back_populates="requirements")
    control_mappings = relationship("RequirementControlMapping", back_populates="requirement", cascade="all, delete-orphan")


class RequirementControlMapping(Base):
    """Requirement <-> Unified Control Library link. Reviewed, not keyword-guessed."""
    __tablename__ = "regulatory_requirement_control_maps"

    id = Column(String(36), primary_key=True, default=_uuid)
    requirement_id = Column(String(36), ForeignKey("regulatory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    control_code = Column(String(64), nullable=False, index=True)   # "UC-AI-SEC-001"

    mapping_type = Column(String(16), nullable=False, default="RELATED")  # MAPPING_TYPES
    confidence = Column(Float, default=0.0)
    rationale = Column(Text, nullable=True)
    proposed_by = Column(String(32), default="AI")  # AI | HUMAN
    state = Column(String(24), nullable=False, default="AI_SUGGESTED")  # MAPPING_STATES
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)

    requirement = relationship("RegulatoryRequirement", back_populates="control_mappings")


class ApplicabilityRule(Base):
    """Explainable rule that decides whether a requirement/framework applies."""
    __tablename__ = "regulatory_applicability_rules"

    id = Column(String(36), primary_key=True, default=_uuid)
    rule_key = Column(String(96), nullable=False, index=True)
    framework_key = Column(String(64), nullable=False, index=True)
    framework_version_id = Column(String(36), ForeignKey("regulatory_framework_versions.id", ondelete="CASCADE"), nullable=True, index=True)
    requirement_key = Column(String(128), nullable=True, index=True)  # null => whole-framework applicability

    jurisdiction = Column(String(128), nullable=True)
    subject_role = Column(String(96), nullable=True)
    conditions = Column(JSON, default=list)   # [{fact, op, value}]
    exceptions = Column(JSON, default=list)
    result = Column(String(48), nullable=False, default="APPLICABLE")
    source_reference = Column(String(255), nullable=True)
    source_anchor_url = Column(String(1000), nullable=True)
    confidence = Column(String(24), default="Rule-Based")
    human_review_required = Column(Boolean, default=True)
    effective_from = Column(String(32), nullable=True)
    effective_until = Column(String(32), nullable=True)
    version = Column(String(32), default="1.0.0")
    review_status = Column(String(32), default="HUMAN_REVIEW_REQUIRED")
    created_at = Column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Validation & change monitoring
# ---------------------------------------------------------------------------
class FrameworkValidation(Base):
    """One validation check result for a framework version."""
    __tablename__ = "regulatory_framework_validations"

    id = Column(String(36), primary_key=True, default=_uuid)
    framework_version_id = Column(String(36), ForeignKey("regulatory_framework_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String(36), nullable=False, index=True)

    layer = Column(String(24), nullable=False)     # SOURCE | SEMANTIC | COMPLIANCE
    check_key = Column(String(96), nullable=False)
    severity = Column(String(16), nullable=False, default="INFO")  # CRITICAL | ERROR | WARNING | INFO
    status = Column(String(16), nullable=False, default="PASS")    # PASS | FAIL
    detail = Column(Text, nullable=True)
    evidence = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)

    framework_version = relationship("FrameworkVersion", back_populates="validations")


class SourceChangeEvent(Base):
    """Raised when a monitored source hash changes. Never auto-publishes."""
    __tablename__ = "regulatory_source_change_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    source_id = Column(String(36), ForeignKey("regulatory_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    detected_at = Column(DateTime, default=_now)
    previous_sha256 = Column(String(64), nullable=True)
    new_sha256 = Column(String(64), nullable=True)
    previous_artifact_id = Column(String(36), nullable=True)
    new_artifact_id = Column(String(36), nullable=True)
    change_kind = Column(String(32), default="REGULATORY_SOURCE_CHANGE_DETECTED")
    diff_summary = Column(JSON, default=dict)  # {added, removed, modified, renumbered, ...}
    status = Column(String(24), default="OPEN")  # OPEN | IN_REVIEW | PUBLISHED | DISMISSED
    reviewer_email = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)


class IngestionRun(Base):
    """Audit log of a fetch->parse->validate->publish pipeline execution."""
    __tablename__ = "regulatory_ingestion_runs"

    id = Column(String(36), primary_key=True, default=_uuid)
    framework_key = Column(String(64), nullable=False, index=True)
    started_at = Column(DateTime, default=_now)
    finished_at = Column(DateTime, nullable=True)
    mode = Column(String(24), default="fixture")  # fixture | live
    pipeline_stage = Column(String(24), default="fetch")
    status = Column(String(24), default="RUNNING")  # RUNNING | SUCCESS | FAILED | BLOCKED
    parser_version = Column(String(32), nullable=True)
    framework_version_id = Column(String(36), nullable=True)
    log = Column(JSON, default=list)  # [{stage, level, message, ts}]
    error = Column(Text, nullable=True)
