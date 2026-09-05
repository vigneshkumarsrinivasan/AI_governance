"""
Pydantic v2 schemas for API requests and responses.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# ---------------------------------------------------------
# Auth & User Schemas
# ---------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    tenant_id: Optional[str] = None
    role: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: str
    # Ignored server-side unless it is one of the roles allowed for self-signup
    # (see core/permissions.SELF_SIGNUP_ALLOWED_ROLES) - a new signup always
    # becomes the founding Tenant Admin of its tenant.
    role: str = "Tenant Admin"

class UserResponse(BaseModel):
    id: str
    tenant_id: str
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    is_demo_tenant: bool = False
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# AI System & Intake Schemas
# ---------------------------------------------------------
class AISystemBase(BaseModel):
    name: str
    description: Optional[str] = None
    business_purpose: Optional[str] = None
    owner: str = "AI Governance Lead"
    business_unit: str = "Enterprise Applications"
    countries_deployed: List[str] = ["US", "EU"]
    users_affected_count: int = 5000
    internal_or_external: str = "External"
    ai_technology: str = "Generative AI"
    model_provider: str = "Anthropic"
    model_name: str = "Claude 3.5 Sonnet"
    model_version: str = "20241022"
    has_foundation_model: bool = True
    is_fine_tuned: bool = False
    uses_rag: bool = True
    uses_traditional_ml: bool = False
    uses_computer_vision: bool = False
    uses_nlp: bool = True
    is_generative_ai: bool = True
    is_agentic_ai: bool = False
    makes_autonomous_decisions: bool = False
    human_in_the_loop: bool = True
    processes_personal_data: bool = False
    processes_sensitive_data: bool = False
    training_data_sources: Optional[str] = None
    deployment_environment: str = "Cloud"
    cloud_provider: str = "AWS"
    production_status: str = "In Production"
    criticality: str = "High"
    risk_classification: str = "High Risk"
    eu_ai_act_classification: str = "High-Risk (Annex III)"
    kill_switch_implemented: bool = True

class AISystemCreate(AISystemBase):
    pass

class AISystemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    business_purpose: Optional[str] = None
    owner: Optional[str] = None
    business_unit: Optional[str] = None
    production_status: Optional[str] = None
    criticality: Optional[str] = None
    risk_classification: Optional[str] = None
    eu_ai_act_classification: Optional[str] = None
    kill_switch_implemented: Optional[bool] = None

class AISystemResponse(AISystemBase):
    id: str
    tenant_id: str
    organization_id: str
    classification_reasoning: Optional[str] = None
    applicable_frameworks: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Guided Dynamic Intake Questionnaire
class IntakeQuestionnaireInput(BaseModel):
    system_name: str
    business_purpose: str
    business_unit: str = "Customer Operations"
    deployment_countries: List[str] = ["EU", "US"]
    
    # Core Intake Triggers
    makes_decisions_about_individuals: bool = False
    decision_domains: List[str] = [] # "employment", "credit", "education", "insurance", "healthcare", "biometrics"
    interacts_directly_with_humans: bool = True
    generates_synthetic_content: bool = True
    processes_personal_data: bool = True
    processes_sensitive_personal_data: bool = False
    
    # Architecture & Agentic Triggers
    is_generative_ai: bool = True
    uses_foundation_model: bool = True
    foundation_model_provider: str = "Anthropic"
    is_autonomous_agent: bool = False
    agent_tools: List[str] = [] # "email", "database", "payment", "code_execution", "external_api"
    can_execute_code: bool = False
    can_access_database: bool = False
    can_initiate_payments: bool = False
    human_in_the_loop_approval: bool = True

class IntakeEvaluationResult(BaseModel):
    # extra="allow" so the applicability service can attach rule-engine
    # provenance (rules_fired, ruleset_version) for internal persistence
    # without widening the documented public response fields below.
    model_config = ConfigDict(extra="allow")

    system_name: str
    risk_level: str # "Unacceptable / Prohibited", "High Risk", "Specific Transparency", "Minimal Risk"
    eu_ai_act_classification: str
    eu_ai_act_rationale: str
    privacy_regulations_applicable: List[str]
    privacy_rationale: str
    cybersecurity_regulations_applicable: List[str]
    cybersecurity_rationale: str
    recommended_frameworks: List[str]
    required_unified_controls: List[str]
    agent_security_required: bool
    disclaimer: str

# ---------------------------------------------------------
# Framework & Control Schemas
# ---------------------------------------------------------
class RequirementItem(BaseModel):
    id: str
    article: str
    title: str
    normalized_requirement: str
    applicability: str
    effective_date: str
    implementation_guidance: str
    evidence_expected: List[str]
    domain: str
    official_url: str

class FrameworkSummary(BaseModel):
    id: str
    name: str
    short_name: str
    official_reference: str
    jurisdiction: str
    type: str
    version: str
    publication_date: str
    effective_date: str
    official_url: str
    status: str
    description: str
    requirement_count: int

class UnifiedControlItem(BaseModel):
    id: str
    code: str
    title: str
    domain: str
    objective: str
    description: str
    control_type: str
    implementation_type: str
    control_frequency: str
    risk_addressed: str
    implementation_guidance: str
    expected_evidence: List[str]
    test_procedure: str
    customer_status: Optional[str] = "In Progress"
    customer_effectiveness: Optional[str] = "Effective"

class CrosswalkMappingItem(BaseModel):
    framework_id: str
    framework_name: str
    requirement_id: str
    article: str
    requirement_title: str
    confidence: str # Exact, Strong, Partial, Related
    rationale: str

class CrosswalkControlRow(BaseModel):
    control_id: str
    control_code: str
    control_title: str
    domain: str
    mappings: List[CrosswalkMappingItem]

class CustomerControlUpdate(BaseModel):
    status: str # Not Started, In Progress, Implemented, Tested, Accepted Risk, Exempt
    effectiveness: str # Ineffective, Partially Effective, Effective
    implementation_notes: Optional[str] = None
    owner: Optional[str] = None

# ---------------------------------------------------------
# Assessment Schemas
# ---------------------------------------------------------
class AssessmentCreate(BaseModel):
    system_id: str
    framework_id: str
    title: str

class AssessmentResponseInput(BaseModel):
    requirement_id: str
    status: str # Yes, No, Partial, N/A, Unknown
    rationale: str
    evidence_ids: List[str] = []

class AssessmentDetailResponse(BaseModel):
    id: str
    system_id: str
    system_name: str
    framework_id: str
    framework_name: str
    title: str
    status: str
    readiness_percentage: float
    implementation_score: float
    evidence_score: float
    effectiveness_score: float
    responses: List[Dict[str, Any]]
    created_at: datetime
    completed_at: Optional[datetime] = None

# ---------------------------------------------------------
# Evidence Schemas (Multi-Control Satisfaction)
# ---------------------------------------------------------
class EvidenceCreate(BaseModel):
    title: str
    description: Optional[str] = None
    evidence_type: str = "Policy"
    file_url: str = "https://storage.aegis-ai.internal/evidence/doc.pdf"
    file_content_mock: Optional[str] = None
    owner: str = "Compliance Manager"
    version: str = "1.0"
    control_ids: List[str] = [] # Satisfies multiple controls at once!
    expiry_date: Optional[datetime] = None

class EvidenceResponse(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: Optional[str] = None
    evidence_type: str
    file_url: str
    file_hash_sha256: str
    owner: str
    version: str
    approval_status: str
    satisfied_controls: List[str]
    satisfied_frameworks_count: int
    created_at: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# Risk & Security Schemas
# ---------------------------------------------------------
class RiskCreate(BaseModel):
    system_id: Optional[str] = None
    risk_code: str
    title: str
    description: Optional[str] = None
    category: str = "Security"
    threat_source: Optional[str] = None
    inherent_likelihood: int = 3
    inherent_impact: int = 4
    treatment: str = "Mitigate"
    mitre_atlas_technique: Optional[str] = None
    owasp_category: Optional[str] = None

class RiskResponse(BaseModel):
    id: str
    risk_code: str
    title: str
    description: Optional[str] = None
    category: str
    system_id: Optional[str] = None
    system_name: Optional[str] = None
    inherent_score: int
    residual_score: int
    treatment: str
    status: str
    owner: str
    mitre_atlas_technique: Optional[str] = None
    owasp_category: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class FindingResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    severity: str
    source: str
    status: str
    system_id: Optional[str] = None
    system_name: Optional[str] = None
    control_id: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime

# ---------------------------------------------------------
# AI Governance Copilot Schemas
# ---------------------------------------------------------
class CopilotQueryInput(BaseModel):
    query: str
    system_id: Optional[str] = None
    framework_id: Optional[str] = None

class CopilotQueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[Dict[str, str]]
    confidence: str
    # "rules_based" (default, no external AI call) or "generative_<provider>"
    # when a real LLM provider is configured (services/ai_provider.py).
    mode: str = "rules_based"
    disclaimer: str

# ---------------------------------------------------------
# Executive Dashboard Schemas
# ---------------------------------------------------------
class DashboardMetricsResponse(BaseModel):
    total_ai_systems: int
    high_risk_systems_count: int
    prohibited_systems_count: int
    genai_systems_count: int
    agentic_systems_count: int
    overall_readiness_percentage: float
    implementation_score: float
    evidence_completeness_score: float
    control_effectiveness_score: float
    open_findings_count: int
    critical_findings_count: int
    active_evidence_artifacts_count: int
    # Real per-framework readiness, computed only from frameworks that have at
    # least one completed Assessment for this tenant - never a fabricated
    # fraction of the overall score (see services/dashboard.md-worthy note in
    # api/dashboard.py for why this replaced hardcoded per-framework multipliers).
    framework_readiness: Dict[str, float]
    # Frameworks the applicability engine has recommended for this tenant's
    # systems but that have no Assessment yet - shown as "Not Assessed" in the
    # UI rather than silently omitted or given a fake score.
    unassessed_frameworks: List[str]
    risk_category_distribution: Dict[str, int]
    legal_disclaimer: str

# ---------------------------------------------------------
# Org Structure: Business Units & AI Products
# ---------------------------------------------------------
class BusinessUnitCreate(BaseModel):
    name: str
    description: Optional[str] = None
    owner: Optional[str] = None
    parent_business_unit_id: Optional[str] = None

class BusinessUnitResponse(BusinessUnitCreate):
    id: str
    tenant_id: str
    organization_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AIProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    owner: Optional[str] = None
    business_unit_id: Optional[str] = None

class AIProductResponse(AIProductCreate):
    id: str
    tenant_id: str
    organization_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------
# Model Registry
# ---------------------------------------------------------
class ModelCreate(BaseModel):
    name: str
    provider: str = "OpenAI"
    version: str = "1.0"
    model_type: str = "LLM"
    context_window: int = 128000
    license: str = "Proprietary Commercial API"
    hosted_location: str = "US-East"
    is_proprietary: bool = False
    is_foundation_model: bool = True
    is_fine_tuned: bool = False
    hosting_type: str = "Vendor API"
    endpoint: Optional[str] = None
    release_date: Optional[datetime] = None
    purpose: Optional[str] = None
    capabilities: List[str] = []
    limitations: Optional[str] = None
    training_data_info: Optional[str] = None
    known_risks: List[str] = []
    approved_uses: List[str] = []
    prohibited_uses: List[str] = []
    customer_data_handling: Optional[str] = None
    data_retention_policy: Optional[str] = None
    deployment_locations: List[str] = []
    status: str = "Active"
    vendor_id: Optional[str] = None
    system_id: Optional[str] = None  # originating/primary system, optional

class ModelUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    endpoint: Optional[str] = None
    purpose: Optional[str] = None
    capabilities: Optional[List[str]] = None
    limitations: Optional[str] = None
    known_risks: Optional[List[str]] = None
    approved_uses: Optional[List[str]] = None
    prohibited_uses: Optional[List[str]] = None
    customer_data_handling: Optional[str] = None
    data_retention_policy: Optional[str] = None
    vendor_id: Optional[str] = None

class ModelResponse(ModelCreate):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ModelLinkSystemInput(BaseModel):
    system_id: str
    role: str = "Primary"

# ---------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------
class AgentCreate(BaseModel):
    name: str
    system_id: str
    model_id: Optional[str] = None
    parent_agent_id: Optional[str] = None
    purpose: Optional[str] = None
    owner: Optional[str] = None
    orchestrator: Optional[str] = None
    identity: Optional[str] = None
    tools: List[str] = []
    permissions: List[str] = []
    data_sources: List[str] = []
    has_code_execution: bool = False
    has_database_access: bool = False
    has_payment_access: bool = False
    has_email_access: bool = False
    has_git_access: bool = False
    has_git_write_access: bool = False
    has_external_web_access: bool = False
    has_external_communication_access: bool = False
    can_invoke_other_agents: bool = False
    accesses_pii: bool = False
    autonomy_level: str = "Semi-Autonomous"
    human_approval_required: bool = True
    rate_limit_config: Dict[str, Any] = {}
    environments: List[str] = ["Production"]
    status: str = "Active"
    approved_use_cases: List[str] = []
    prohibited_actions: List[str] = []

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    purpose: Optional[str] = None
    owner: Optional[str] = None
    tools: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    has_code_execution: Optional[bool] = None
    has_database_access: Optional[bool] = None
    has_payment_access: Optional[bool] = None
    has_email_access: Optional[bool] = None
    has_git_access: Optional[bool] = None
    has_git_write_access: Optional[bool] = None
    has_external_web_access: Optional[bool] = None
    has_external_communication_access: Optional[bool] = None
    can_invoke_other_agents: Optional[bool] = None
    accesses_pii: Optional[bool] = None
    autonomy_level: Optional[str] = None
    human_approval_required: Optional[bool] = None
    status: Optional[str] = None
    approved_use_cases: Optional[List[str]] = None
    prohibited_actions: Optional[List[str]] = None

class AgentResponse(AgentCreate):
    id: str
    tenant_id: str
    risk_score: float = 0.0
    kill_switch_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------
# Vendor Registry
# ---------------------------------------------------------
class VendorCreate(BaseModel):
    name: str
    service_type: str = "Foundation Model Provider"
    contract_status: str = "Active"
    contract_owner: Optional[str] = None
    vendor_owner: Optional[str] = None
    contract_expiry_date: Optional[datetime] = None
    data_processing_role: Optional[str] = None
    data_retention_days: int = 0
    data_residency: List[str] = []
    subprocessors: List[str] = []
    regions: List[str] = []
    allows_customer_data_training: bool = False
    certifications: List[str] = []
    privacy_documentation_url: Optional[str] = None
    security_documentation_url: Optional[str] = None
    ai_governance_documentation_url: Optional[str] = None
    incident_obligations: Optional[str] = None
    business_continuity_plan: Optional[str] = None
    exit_strategy: Optional[str] = None
    risk_rating: str = "Low"
    dpa_signed: bool = True

class VendorUpdate(BaseModel):
    contract_status: Optional[str] = None
    contract_owner: Optional[str] = None
    vendor_owner: Optional[str] = None
    contract_expiry_date: Optional[datetime] = None
    data_processing_role: Optional[str] = None
    data_residency: Optional[List[str]] = None
    subprocessors: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    risk_rating: Optional[str] = None
    dpa_signed: Optional[bool] = None
    incident_obligations: Optional[str] = None
    business_continuity_plan: Optional[str] = None
    exit_strategy: Optional[str] = None

class VendorResponse(VendorCreate):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
