"""
SQLAlchemy database models for AegisAI Governance Platform.
All business data models are tenant-scoped for strict multi-tenant isolation.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from aegis_app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# ---------------------------------------------------------
# Tenant & Organization Models
# ---------------------------------------------------------
class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utc_now)
    
    organizations = relationship("Organization", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), default="Technology")
    headquarters_country = Column(String(100), default="United States")
    countries_operating = Column(JSON, default=list)  # ["US", "DE", "FR", "GB", "IN", "SG"]
    employee_count = Column(Integer, default=500)
    is_financial_institution = Column(Boolean, default=False)
    is_critical_infrastructure = Column(Boolean, default=False)
    eu_market_exposure = Column(Boolean, default=True)
    # True only for the seeded sales-demo tenant (demo_data.py) - lets the UI
    # show a "DEMO" badge instead of guessing from the organization name.
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    
    tenant = relationship("Tenant", back_populates="organizations")
    ai_systems = relationship("AISystem", back_populates="organization", cascade="all, delete-orphan")


class BusinessUnit(Base):
    """Organizational hierarchy node: Organization -> Business Unit -> AI Product -> AI System."""
    __tablename__ = "business_units"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner = Column(String(255), nullable=True)
    parent_business_unit_id = Column(String(36), ForeignKey("business_units.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now)


class AIProduct(Base):
    """A product/initiative that groups one or more AI Systems, optionally under a Business Unit."""
    __tablename__ = "ai_products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    business_unit_id = Column(String(36), ForeignKey("business_units.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

# ---------------------------------------------------------
# User & RBAC Models
# ---------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    # Role: Super Admin, Tenant Admin, AI Governance Lead, Compliance Manager, Risk Manager,
    # CISO/Security, Privacy/DPO, AI Engineer, Model Owner, Auditor, Viewer
    role = Column(String(50), default="AI Governance Lead", nullable=False)
    is_active = Column(Boolean, default=True)
    # UI experience mode: "simple" (SME/founder view - progressive disclosure) or
    # "advanced" (full enterprise framework/control depth). Defaults to "advanced"
    # so every pre-existing user keeps exactly the experience they have today;
    # new SME signups are set to "simple" by the signup flow.
    ui_mode = Column(String(20), default="advanced", nullable=False)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="users")

# ---------------------------------------------------------
# AI System & Inventory Models
# ---------------------------------------------------------
class AISystem(Base):
    __tablename__ = "ai_systems"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    business_purpose = Column(Text, nullable=True)
    owner = Column(String(255), default="AI Lead")
    # Free-text field kept for backward compatibility with existing records and
    # the original demo dataset. business_unit_id is the real FK going forward;
    # both are populated together by the API layer so neither silently goes stale.
    business_unit = Column(String(100), default="Engineering")
    business_unit_id = Column(String(36), ForeignKey("business_units.id", ondelete="SET NULL"), nullable=True, index=True)
    product_id = Column(String(36), ForeignKey("ai_products.id", ondelete="SET NULL"), nullable=True, index=True)
    countries_deployed = Column(JSON, default=list)
    user_countries = Column(JSON, default=list)      # countries where end users are located
    customer_countries = Column(JSON, default=list)  # countries where the paying/contracting customer is located
    users_affected_count = Column(Integer, default=1000)
    internal_or_external = Column(String(50), default="External")  # Internal, External, Both
    
    # AI Technology Stack
    ai_technology = Column(String(100), default="Generative AI")  # GenAI, RAG, Traditional ML, Vision, Agentic
    model_provider = Column(String(100), default="Anthropic")
    model_name = Column(String(100), default="Claude 3.5 Sonnet")
    model_version = Column(String(50), default="20241022")
    has_foundation_model = Column(Boolean, default=True)
    is_fine_tuned = Column(Boolean, default=False)
    uses_rag = Column(Boolean, default=True)
    uses_traditional_ml = Column(Boolean, default=False)
    uses_computer_vision = Column(Boolean, default=False)
    uses_nlp = Column(Boolean, default=True)
    is_generative_ai = Column(Boolean, default=True)
    is_agentic_ai = Column(Boolean, default=False)
    makes_autonomous_decisions = Column(Boolean, default=False)
    human_in_the_loop = Column(Boolean, default=True)
    
    # Data & Privacy
    processes_personal_data = Column(Boolean, default=False)
    processes_sensitive_data = Column(Boolean, default=False)
    processes_children_data = Column(Boolean, default=False)
    processes_biometric_data = Column(Boolean, default=False)
    training_data_sources = Column(Text, nullable=True)

    # Decision-impact domains (drives EU AI Act Annex III / high-risk analysis)
    employment_impact = Column(Boolean, default=False)
    credit_impact = Column(Boolean, default=False)
    health_impact = Column(Boolean, default=False)
    insurance_impact = Column(Boolean, default=False)
    education_impact = Column(Boolean, default=False)
    critical_infrastructure_impact = Column(Boolean, default=False)
    law_enforcement_relevance = Column(Boolean, default=False)
    decision_impact = Column(String(100), nullable=True)  # None, Advisory, Significant, Determinative
    human_oversight = Column(String(100), default="Human-in-the-loop")  # None, Human-in-the-loop, Human-on-the-loop, Human-in-command
    autonomy_level = Column(String(50), default="Supervised")  # Supervised, Semi-Autonomous, Fully Autonomous

    uses_external_api = Column(Boolean, default=False)

    # Infrastructure & Deployment
    deployment_environment = Column(String(100), default="Cloud")  # Cloud, On-Premise, Hybrid
    cloud_provider = Column(String(100), default="AWS")
    apis_exposed = Column(JSON, default=list)
    production_status = Column(String(50), default="In Production")  # legacy short-hand, kept for backward compat
    # Full lifecycle per spec: DISCOVERED, PROPOSED, EXPERIMENT, DEVELOPMENT, VALIDATION,
    # APPROVED, APPROVED_WITH_CONDITIONS, PRODUCTION, RESTRICTED, SUSPENDED, PROHIBITED, RETIRED
    lifecycle_status = Column(String(50), default="PRODUCTION", index=True)
    criticality = Column(String(50), default="High")  # Critical, High, Medium, Low

    # Classification & Regulatory
    risk_classification = Column(String(50), default="High Risk")  # Unacceptable/Prohibited, High Risk, Specific Transparency, Minimal Risk
    eu_ai_act_classification = Column(String(50), default="High-Risk (Annex III)")
    classification_reasoning = Column(Text, nullable=True)
    applicable_frameworks = Column(JSON, default=list)  # ["eu_ai_act", "nist_ai_rmf", "owasp_llm", ...]

    # Architecture & operational context
    architecture_description = Column(Text, nullable=True)
    data_flows_description = Column(Text, nullable=True)
    known_limitations = Column(Text, nullable=True)
    monitoring_configuration = Column(JSON, default=dict)

    # Governance & Safety Controls
    kill_switch_implemented = Column(Boolean, default=True)
    model_card_url = Column(String(500), nullable=True)
    system_card_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    approved_at = Column(DateTime, nullable=True)
    retired_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="ai_systems")
    models = relationship("AIModel", back_populates="ai_system", cascade="all, delete-orphan")
    agents = relationship("AIAgent", back_populates="ai_system", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="ai_system", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="ai_system", cascade="all, delete-orphan")

class AIModel(Base):
    """
    Model Registry entry. A model is a tenant-level catalog asset that CAN be
    used by more than one AI System - system_id is kept as the "originating/
    primary" system for backward compatibility with the original one-model-
    per-system data, but the real many-to-many relationship is
    AISystemModelLink below (see Model -> AI Systems dependency view in
    api/model_registry.py).
    """
    __tablename__ = "ai_models"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    system_id = Column(String(36), ForeignKey("ai_systems.id", ondelete="SET NULL"), nullable=True, index=True)
    vendor_id = Column(String(36), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    provider = Column(String(100), default="OpenAI")
    version = Column(String(50), default="1.0")
    model_type = Column(String(100), default="LLM")  # LLM, Embedding, Classification, Vision, Multimodal
    context_window = Column(Integer, default=128000)
    license = Column(String(100), default="Proprietary Commercial API")
    hosted_location = Column(String(100), default="US-East")
    is_proprietary = Column(Boolean, default=False)

    is_foundation_model = Column(Boolean, default=True)
    is_fine_tuned = Column(Boolean, default=False)
    hosting_type = Column(String(50), default="Vendor API")  # Vendor API, Self-Hosted, On-Premise, Private Cloud
    endpoint = Column(String(500), nullable=True)
    release_date = Column(DateTime, nullable=True)
    purpose = Column(Text, nullable=True)
    capabilities = Column(JSON, default=list)
    limitations = Column(Text, nullable=True)
    training_data_info = Column(Text, nullable=True)
    known_risks = Column(JSON, default=list)
    approved_uses = Column(JSON, default=list)
    prohibited_uses = Column(JSON, default=list)
    customer_data_handling = Column(Text, nullable=True)
    data_retention_policy = Column(Text, nullable=True)
    deployment_locations = Column(JSON, default=list)
    status = Column(String(50), default="Active")  # Active, Deprecated, Retired

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    ai_system = relationship("AISystem", back_populates="models")
    vendor = relationship("Vendor", back_populates="models")
    version_history = relationship("ModelVersionHistory", back_populates="model", cascade="all, delete-orphan")


class AISystemModelLink(Base):
    """Many-to-many link: which AI Systems actually use which Model (spec: Model -> AI Systems)."""
    __tablename__ = "ai_system_model_links"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    system_id = Column(String(36), ForeignKey("ai_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(String(36), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="Primary")  # Primary, Secondary, Fallback
    created_at = Column(DateTime, default=utc_now)


class ModelVersionHistory(Base):
    """Tracks model version changes over time (spec: "model version history")."""
    __tablename__ = "model_version_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    model_id = Column(String(36), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    change_description = Column(Text, nullable=True)
    released_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    model = relationship("AIModel", back_populates="version_history")

class AIAgent(Base):
    __tablename__ = "ai_agents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    system_id = Column(String(36), ForeignKey("ai_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(String(36), ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_agent_id = Column(String(36), ForeignKey("ai_agents.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    purpose = Column(Text, nullable=True)
    owner = Column(String(255), nullable=True)
    orchestrator = Column(String(100), nullable=True)  # e.g. LangGraph, CrewAI, AutoGen, custom
    identity = Column(String(255), nullable=True)  # service account / workload identity reference

    tools = Column(JSON, default=list)  # ["web_search", "sql_query", "jira_api", "send_email", "code_executor"]
    permissions = Column(JSON, default=list)  # ["read:db", "write:db", "exec:code", "send:email"]
    data_sources = Column(JSON, default=list)

    has_code_execution = Column(Boolean, default=False)
    has_database_access = Column(Boolean, default=False)
    has_payment_access = Column(Boolean, default=False)
    has_email_access = Column(Boolean, default=False)
    has_git_access = Column(Boolean, default=False)
    has_git_write_access = Column(Boolean, default=False)
    has_external_web_access = Column(Boolean, default=False)
    has_external_communication_access = Column(Boolean, default=False)
    can_invoke_other_agents = Column(Boolean, default=False)
    accesses_pii = Column(Boolean, default=False)

    autonomy_level = Column(String(50), default="Semi-Autonomous")  # Supervised, Semi-Autonomous, Fully Autonomous
    human_approval_required = Column(Boolean, default=True)
    rate_limit_config = Column(JSON, default=dict)  # e.g. {"max_actions_per_minute": 10}
    environments = Column(JSON, default=list)  # ["Development", "Staging", "Production"]
    status = Column(String(50), default="Active")  # Proposed, Active, Restricted, Suspended, Retired
    approved_use_cases = Column(JSON, default=list)
    prohibited_actions = Column(JSON, default=list)
    risk_score = Column(Float, default=0.0)  # computed from permission breadth + autonomy + approval gate presence

    kill_switch_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    ai_system = relationship("AISystem", back_populates="agents")
    model = relationship("AIModel", foreign_keys=[model_id])
    parent_agent = relationship("AIAgent", remote_side=[id], foreign_keys=[parent_agent_id])

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    service_type = Column(String(100), default="Foundation Model Provider")
    models_provided = Column(JSON, default=list)  # legacy free-text list; models relationship below is the real link
    contract_status = Column(String(50), default="Active")
    contract_owner = Column(String(255), nullable=True)
    vendor_owner = Column(String(255), nullable=True)
    contract_expiry_date = Column(DateTime, nullable=True)
    data_processing_role = Column(String(50), nullable=True)  # Controller, Processor, Sub-processor, Joint Controller
    data_retention_days = Column(Integer, default=0)
    data_residency = Column(JSON, default=list)  # countries/regions where data is stored
    subprocessors = Column(JSON, default=list)
    regions = Column(JSON, default=list)
    allows_customer_data_training = Column(Boolean, default=False)  # Zero data retention / no training
    certifications = Column(JSON, default=list)  # ["SOC 2 Type II", "ISO 27001", "HIPAA"]
    privacy_documentation_url = Column(String(500), nullable=True)
    security_documentation_url = Column(String(500), nullable=True)
    ai_governance_documentation_url = Column(String(500), nullable=True)
    incident_obligations = Column(Text, nullable=True)
    business_continuity_plan = Column(Text, nullable=True)
    exit_strategy = Column(Text, nullable=True)
    risk_rating = Column(String(50), default="Low")  # Low, Medium, High, Critical
    dpa_signed = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    models = relationship("AIModel", back_populates="vendor")

# ---------------------------------------------------------
# Controls & Compliance Crosswalk Models
# ---------------------------------------------------------
class CustomerControl(Base):
    __tablename__ = "customer_controls"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    organization_id = Column(String(36), nullable=False, index=True)
    control_id = Column(String(50), nullable=False, index=True)  # UC-AI-SEC-001
    status = Column(String(50), default="In Progress")  # Not Started, In Progress, Implemented, Tested, Accepted Risk, Exempt
    effectiveness = Column(String(50), default="Effective")  # Ineffective, Partially Effective, Effective
    implementation_notes = Column(Text, nullable=True)
    owner = Column(String(255), default="Security Lead")
    last_reviewed_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class Assessment(Base):
    __tablename__ = "assessments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    organization_id = Column(String(36), nullable=False, index=True)
    system_id = Column(String(36), ForeignKey("ai_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    framework_id = Column(String(50), nullable=False)  # eu_ai_act, nist_ai_rmf, etc.
    status = Column(String(50), default="In Progress")  # Draft, In Progress, Under Review, Completed
    readiness_percentage = Column(Float, default=0.0)
    implementation_score = Column(Float, default=0.0)
    evidence_score = Column(Float, default=0.0)
    effectiveness_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)
    
    ai_system = relationship("AISystem", back_populates="assessments")
    responses = relationship("AssessmentResponse", back_populates="assessment", cascade="all, delete-orphan")

class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id = Column(String(100), nullable=False)  # EU-AIA-ART-09, NIST-RMF-GOV-1.1
    status = Column(String(50), default="Yes")  # Yes, No, Partial, N/A, Unknown
    rationale = Column(Text, nullable=True)
    evidence_ids = Column(JSON, default=list)  # Links to Evidence records
    reviewer_notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utc_now)
    
    assessment = relationship("Assessment", back_populates="responses")

# ---------------------------------------------------------
# Evidence Management (Multi-Control Satisfaction)
# ---------------------------------------------------------
class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    organization_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    evidence_type = Column(String(100), default="Policy")  # Policy, Architecture, Test Report, Model Card, DPIA, Runbook, Audit Log
    file_url = Column(String(500), default="https://storage.aegis-ai.internal/evidence/doc.pdf")
    # Storage backend key (local path or S3 object key) for real uploaded files.
    # Null for legacy/metadata-only evidence records that only reference an external file_url.
    storage_key = Column(String(500), nullable=True)
    storage_backend = Column(String(20), nullable=True)  # "local" | "s3"
    original_filename = Column(String(255), nullable=True)
    content_type = Column(String(100), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    file_hash_sha256 = Column(String(64), nullable=False)
    owner = Column(String(255), default="Compliance Manager")
    version = Column(String(50), default="1.0")
    # Evidence quality workflow (spec #30): Draft -> Submitted -> Under Review -> Accepted/Rejected/Insufficient
    approval_status = Column(String(50), default="Draft")
    reviewed_by = Column(String(255), nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    review_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    control_mappings = relationship("EvidenceControlMap", back_populates="evidence", cascade="all, delete-orphan")

class EvidenceControlMap(Base):
    """
    CRITICAL MOAT: One evidence artifact satisfies multiple Unified Controls
    and therefore supports all mapped frameworks without duplicated evidence uploads!
    """
    __tablename__ = "evidence_control_maps"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    evidence_id = Column(String(36), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    control_id = Column(String(50), nullable=False, index=True)  # UC-AI-SEC-001
    # Full Coverage | Partial Coverage | Supporting Evidence | Context Only (spec #31)
    coverage_type = Column(String(50), default="Full Coverage")

    evidence = relationship("Evidence", back_populates="control_mappings")

# ---------------------------------------------------------
# Risk Register & Threat Modeling
# ---------------------------------------------------------
class Risk(Base):
    __tablename__ = "risks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    organization_id = Column(String(36), nullable=False, index=True)
    system_id = Column(String(36), ForeignKey("ai_systems.id", ondelete="CASCADE"), nullable=True, index=True)
    
    risk_code = Column(String(50), nullable=False)  # RSK-AI-001
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="Security")  # Safety, Security, Privacy, Legal, Fairness, Agent, Model
    threat_source = Column(String(255), nullable=True)
    
    inherent_likelihood = Column(Integer, default=3)  # 1-5
    inherent_impact = Column(Integer, default=4)      # 1-5
    inherent_score = Column(Integer, default=12)      # 1-25
    
    residual_likelihood = Column(Integer, default=1)  # 1-5
    residual_impact = Column(Integer, default=2)      # 1-5
    residual_score = Column(Integer, default=2)       # 1-25
    
    treatment = Column(String(50), default="Mitigate")  # Mitigate, Accept, Transfer, Avoid
    status = Column(String(50), default="Open")          # Open, In Progress, Closed, Accepted
    owner = Column(String(255), default="Risk Manager")
    mitre_atlas_technique = Column(String(100), nullable=True)
    owasp_category = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=utc_now)
    
    ai_system = relationship("AISystem", back_populates="risks")
    findings = relationship("Finding", back_populates="risk")

class Finding(Base):
    __tablename__ = "findings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    organization_id = Column(String(36), nullable=False, index=True)
    system_id = Column(String(36), nullable=True, index=True)
    control_id = Column(String(50), nullable=True)
    risk_id = Column(String(36), ForeignKey("risks.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(50), default="High")  # Critical, High, Medium, Low
    source = Column(String(100), default="Assessment")  # Assessment, Red Team, Vulnerability Scan, Audit
    status = Column(String(50), default="Open")    # Open, Remediating, Resolved, Accepted Risk
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    risk = relationship("Risk", back_populates="findings")
    remediations = relationship("RemediationTask", back_populates="finding", cascade="all, delete-orphan")

class RemediationTask(Base):
    __tablename__ = "remediation_tasks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    finding_id = Column(String(36), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    assigned_to = Column(String(255), default="AI Engineer")
    priority = Column(String(50), default="High")  # Critical, High, Medium, Low
    status = Column(String(50), default="In Progress")  # Backlog, Todo, In Progress, In Review, Done
    target_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    finding = relationship("Finding", back_populates="remediations")

# ---------------------------------------------------------
# Audit Trail & Policy Management
# ---------------------------------------------------------
class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    actor_id = Column(String(36), nullable=True)
    actor_email = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)  # CREATE_AI_SYSTEM, UPDATE_CONTROL, UPLOAD_EVIDENCE, etc.
    object_type = Column(String(100), nullable=False)
    object_id = Column(String(100), nullable=False)
    changes = Column(JSON, default=dict)
    ip_address = Column(String(50), default="127.0.0.1")
    timestamp = Column(DateTime, default=utc_now)

class PolicyDocument(Base):
    __tablename__ = "policy_documents"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    organization_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    policy_type = Column(String(100), default="Responsible AI Policy")
    status = Column(String(50), default="Approved")  # Draft, Under Review, Approved
    version = Column(String(50), default="1.0")
    approved_by = Column(String(255), default="Chief Risk Officer")
    effective_date = Column(DateTime, default=utc_now)
    review_date = Column(DateTime, nullable=True)
    content = Column(Text, nullable=True)

class ApplicabilityDecision(Base):
    """
    Persisted record of every regulatory applicability/classification determination.
    Every intake evaluation creates one of these so decisions are reproducible,
    reviewable, and never silently overwritten (spec #7, #10, #75, #112, #113).
    """
    __tablename__ = "applicability_decisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    organization_id = Column(String(36), nullable=True, index=True)
    system_id = Column(String(36), nullable=True, index=True)  # may be null: decision made before system record exists

    system_name = Column(String(255), nullable=False)
    input_snapshot = Column(JSON, default=dict)  # full IntakeQuestionnaireInput as submitted

    # APPLICABLE | LIKELY_APPLICABLE | POTENTIALLY_APPLICABLE | NOT_APPLICABLE | EXEMPT | UNKNOWN | LEGAL_REVIEW_REQUIRED
    decision_status = Column(String(50), default="UNKNOWN")
    risk_level = Column(String(50), nullable=False)
    eu_ai_act_classification = Column(String(100), nullable=False)
    rationale = Column(Text, nullable=False)
    recommended_frameworks = Column(JSON, default=list)
    required_controls = Column(JSON, default=list)
    rules_fired = Column(JSON, default=list)  # [{rule_id, framework, requirement_id, version}, ...]
    confidence = Column(String(50), default="Rule-Based")
    unresolved_questions = Column(JSON, default=list)

    # Human-in-the-loop review (spec #75) - the AI/rule engine never overrides this.
    requires_legal_review = Column(Boolean, default=False)
    reviewer_id = Column(String(36), nullable=True)
    reviewer_email = Column(String(255), nullable=True)
    reviewer_decision = Column(String(50), nullable=True)  # Accepted, Rejected, Modified
    reviewer_rationale = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    ruleset_version = Column(String(50), nullable=True)
    assessed_as_of_date = Column(DateTime, default=utc_now)  # spec #112/#113: "as of" temporal logic
    created_at = Column(DateTime, default=utc_now)
    superseded_by_id = Column(String(36), nullable=True)  # link to a later re-assessment; history is never overwritten

    # "system" (per-AI-system intake, the original behaviour) or "organization"
    # (company-wide onboarding applicability). Defaults to "system" so every
    # existing row keeps its original meaning.
    scope = Column(String(20), default="system", nullable=False)
    # Company-scope only: [{framework_key, framework_name, exposure, confidence,
    # reasoning, jurisdiction, basis, source_reference, category}] - the full
    # explainable framework-exposure map from the company applicability engine.
    framework_exposure = Column(JSON, default=list)
    # Facts we still need from the customer before applicability can be firmed up.
    open_questions = Column(JSON, default=list)


class OrganizationProfile(Base):
    """
    Company-level compliance/AI-risk profile captured by the SME onboarding
    wizard (spec sections 5-7). One row per organization. This is ADDITIVE - it
    never replaces the Organization row; it enriches it with the fuller fact set
    the applicability engine and Trust Score need. `answers` stores the raw
    questionnaire exactly as submitted (reproducibility); the flat columns are
    the normalised facts the rule engine consumes.
    """
    __tablename__ = "organization_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    answers = Column(JSON, default=dict)          # raw questionnaire as submitted
    # Normalised company facts (mirrors of answers, used by company_rule_engine)
    headquarters_country = Column(String(8), default="US")
    operating_countries = Column(JSON, default=list)      # ISO codes: ["DE","GB","IN","SG","US"]
    employee_count = Column(Integer, default=20)
    industry = Column(String(80), default="b2b_saas")
    sells_to_enterprises = Column(Boolean, default=True)
    sells_to_government = Column(Boolean, default=False)
    sells_to_financial_institutions = Column(Boolean, default=False)
    sells_to_healthcare = Column(Boolean, default=False)

    develops_ai_products = Column(Boolean, default=True)
    deploys_ai_internally = Column(Boolean, default=True)
    uses_generative_ai = Column(Boolean, default=True)
    builds_ai_agents = Column(Boolean, default=False)
    uses_rag = Column(Boolean, default=False)
    uses_third_party_models = Column(Boolean, default=True)
    makes_decisions_about_people = Column(Boolean, default=False)
    decision_domains = Column(JSON, default=list)         # employment, credit, healthcare, education, biometrics, safety
    uses_biometrics = Column(Boolean, default=False)

    ai_providers = Column(JSON, default=list)             # ["openai","anthropic","google","azure_openai","aws_bedrock",...]
    data_types = Column(JSON, default=list)               # personal, employee, health, financial, biometric, children, payment, source_code, confidential_customer

    sells_software = Column(Boolean, default=True)
    is_saas = Column(Boolean, default=True)
    sells_connected_hardware = Column(Boolean, default=False)
    is_iot = Column(Boolean, default=False)
    has_embedded_software = Column(Boolean, default=False)
    is_cybersecurity_product = Column(Boolean, default=False)
    product_marketed_in_eu = Column(Boolean, default=False)

    soc2_required = Column(Boolean, default=False)
    iso27001_required = Column(Boolean, default=False)
    gets_security_questionnaires = Column(Boolean, default=True)
    existing_certifications = Column(JSON, default=list)
    has_compliance_staff = Column(Boolean, default=False)
    has_security_staff = Column(Boolean, default=False)

    starter_pack = Column(String(40), nullable=True)      # applied sector pack id
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class IncidentReport(Base):
    __tablename__ = "incident_reports"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    organization_id = Column(String(36), nullable=False, index=True)
    system_id = Column(String(36), nullable=True)
    incident_title = Column(String(255), nullable=False)
    severity = Column(String(50), default="Medium")  # Critical, High, Medium, Low
    status = Column(String(50), default="Contained")  # Detected, Triage, Contained, Investigating, Closed
    detected_at = Column(DateTime, default=utc_now)
    contained_at = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    affected_users_count = Column(Integer, default=0)
    data_affected = Column(Boolean, default=False)
    regulatory_reported = Column(Boolean, default=False)
