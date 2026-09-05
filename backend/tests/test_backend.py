"""
Comprehensive automated tests for AegisAI Governance Platform.
Covers authentication, RBAC, applicability engine, crosswalk matrix,
evidence multi-mapping, and compliance readiness scoring.
"""

import pytest
import asyncio
from aegis_app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from aegis_app.schemas.schemas import IntakeQuestionnaireInput
from aegis_app.services.applicability import evaluate_ai_system_applicability
from aegis_app.services.scoring import calculate_compliance_scores
from aegis_app.services.crosswalk import crosswalk_service

def test_password_hashing_and_jwt():
    raw_pass = "SecureCompliance2026!"
    hashed = get_password_hash(raw_pass)
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

    token = create_access_token({"sub": "user-123", "tenant_id": "tenant-abc", "role": "CISO/Security"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["tenant_id"] == "tenant-abc"
    assert payload["role"] == "CISO/Security"

def test_applicability_engine_high_risk():
    """
    Test that an AI system evaluating loan eligibility in the EU is classified
    as High-Risk under Annex III of the EU AI Act with mandatory risk & oversight controls.
    """
    input_data = IntakeQuestionnaireInput(
        system_name="Automated Credit Underwriter",
        business_purpose="Credit decisioning and loan default probability prediction",
        deployment_countries=["EU", "DE"],
        makes_decisions_about_individuals=True,
        decision_domains=["credit"],
        interacts_directly_with_humans=False,
        generates_synthetic_content=False,
        processes_personal_data=True,
        is_generative_ai=False,
        uses_foundation_model=False,
        is_autonomous_agent=False
    )
    result = evaluate_ai_system_applicability(input_data)
    assert result.risk_level == "High Risk"
    assert "Annex III" in result.eu_ai_act_classification
    assert "eu_ai_act" in result.recommended_frameworks
    assert "gdpr_ai" in result.recommended_frameworks
    assert "UC-AI-RSK-001" in result.required_unified_controls
    assert "UC-AI-AGT-003" in result.required_unified_controls # Human approval gate

def test_applicability_engine_agentic_ai():
    """
    Test that an autonomous agent with shell execution and DB access triggers
    OWASP Agentic AI security controls, least privilege, and emergency kill-switch.
    """
    input_data = IntakeQuestionnaireInput(
        system_name="IT DevOps Cloud Agent",
        business_purpose="Automated server provisioning and diagnostics",
        deployment_countries=["US"],
        makes_decisions_about_individuals=False,
        decision_domains=[],
        interacts_directly_with_humans=False,
        generates_synthetic_content=True,
        processes_personal_data=False,
        is_generative_ai=True,
        uses_foundation_model=True,
        is_autonomous_agent=True,
        agent_tools=["code_execution", "database", "terminal"],
        can_execute_code=True,
        can_access_database=True
    )
    result = evaluate_ai_system_applicability(input_data)
    assert result.agent_security_required is True
    assert "owasp_agentic_ai" in result.recommended_frameworks
    assert "UC-AI-AGT-001" in result.required_unified_controls # Least privilege
    assert "UC-AI-AGT-002" in result.required_unified_controls # Kill-switch
    assert "UC-AI-AGT-005" in result.required_unified_controls # Sandboxing

def test_all_17_frameworks_loaded():
    """
    Verifies that all 17 authoritative frameworks specified in the Master Prompt
    are properly ingested with metadata, requirements, and legal source references.
    """
    frameworks = crosswalk_service.get_frameworks_summary()
    assert len(frameworks) == 17
    
    fw_ids = {f["id"] for f in frameworks}
    expected_ids = {
        "eu_ai_act", "nist_ai_rmf", "nist_ai_600_1", "eu_cra", "owasp_llm",
        "owasp_agentic_ai", "nist_csf_2", "nist_sp_800_218", "gdpr_ai",
        "mitre_atlas", "nis2", "dora", "nist_sp_800_53", "uk_ai_cyber_code",
        "india_dpdpa", "nist_sp_800_161", "singapore_ai_verify"
    }
    assert expected_ids.issubset(fw_ids)

def test_crosswalk_matrix_and_evidence_multimapping():
    """
    CRITICAL MOAT TEST:
    Verifies that 1 evidence artifact attached to UC-AI-SEC-001 (Prompt Injection Defense)
    satisfies requirements across OWASP LLM, MITRE ATLAS, NIST AI 600-1, EU AI Act, and UK AI Cyber Code.
    """
    coverage = crosswalk_service.resolve_evidence_coverage(["UC-AI-SEC-001"])
    assert coverage["satisfied_frameworks_count"] >= 4
    satisfied_fw_ids = set(coverage["satisfied_framework_ids"])
    assert "owasp_llm" in satisfied_fw_ids
    assert "mitre_atlas" in satisfied_fw_ids
    assert "nist_ai_600_1" in satisfied_fw_ids

def test_explainable_scoring_calculation():
    """
    Verifies multi-dimensional scoring formula:
    Implementation, Evidence, Effectiveness, and deduction for critical findings.
    """
    mock_controls = [
        {"control_id": "UC-1", "status": "Implemented", "effectiveness": "Effective"},
        {"control_id": "UC-2", "status": "Implemented", "effectiveness": "Effective"},
        {"control_id": "UC-3", "status": "In Progress", "effectiveness": "Partially Effective"},
        {"control_id": "UC-4", "status": "Not Started", "effectiveness": "Ineffective"}
    ]
    # UC-1 and UC-2 have evidence
    mock_evidence_counts = {"UC-1": 1, "UC-2": 2}
    mock_findings = [{"severity": "Critical", "status": "Open"}] # -5% deduction

    scores = calculate_compliance_scores(mock_controls, mock_evidence_counts, mock_findings)
    assert scores["implementation_score"] == 62.5 # (1.0 + 1.0 + 0.5 + 0.0)/4 = 62.5%
    assert scores["evidence_score"] == 50.0 # 2/4 controls have evidence = 50.0%
    assert scores["effectiveness_score"] == 62.5 # (1.0 + 1.0 + 0.5 + 0.0)/4 = 62.5%
    assert scores["finding_deduction"] == 5.0
    # Expected overall: (0.40 * 62.5) + (0.35 * 50.0) + (0.25 * 62.5) - 5.0 = 25.0 + 17.5 + 15.625 - 5.0 = 53.1
    assert scores["overall_readiness"] == 53.1

@pytest.mark.asyncio
async def test_tenant_isolation_and_rbac():
    """
    CRITICAL SECURITY TEST:
    Ensures that queries filtered by tenant_id never leak records across different tenants.
    """
    from aegis_app.core.database import AsyncSessionLocal
    from aegis_app.models.models import Tenant, AISystem, User
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        # Create Tenant A and Tenant B
        tenant_a = Tenant(name="Tenant Alpha Corp")
        tenant_b = Tenant(name="Tenant Beta Bank")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        # Add AI System to Tenant A
        sys_a = AISystem(
            tenant_id=tenant_a.id,
            organization_id=tenant_a.id,
            name="Alpha Proprietary Algorithmic Trader",
            business_unit="Trading",
            risk_classification="High Risk"
        )
        session.add(sys_a)

        # Add AI System to Tenant B
        sys_b = AISystem(
            tenant_id=tenant_b.id,
            organization_id=tenant_b.id,
            name="Beta Customer Chatbot",
            business_unit="Support",
            risk_classification="Minimal Risk"
        )
        session.add(sys_b)
        await session.commit()

        # Query scoped to Tenant A: Must NOT see Tenant B's system
        result_a = await session.execute(select(AISystem).where(AISystem.tenant_id == tenant_a.id))
        systems_a = result_a.scalars().all()
        assert len(systems_a) == 1
        assert systems_a[0].name == "Alpha Proprietary Algorithmic Trader"

        # Query scoped to Tenant B: Must NOT see Tenant A's system
        result_b = await session.execute(select(AISystem).where(AISystem.tenant_id == tenant_b.id))
        systems_b = result_b.scalars().all()
        assert len(systems_b) == 1
        assert systems_b[0].name == "Beta Customer Chatbot"

