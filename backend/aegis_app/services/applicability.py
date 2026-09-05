"""
AI Applicability and Classification Service.

Thin adapter between the API layer and the configurable rule engine
(services/rule_engine.py, data/applicability_rules.json). This module's only
job is: (1) translate an IntakeQuestionnaireInput into the flat "facts" dict
the rule engine consumes, including a couple of small derived facts that are
cheaper to compute once in Python than to re-express as rule conditions
(EU-exposure, the high-risk-domain intersection), and (2) translate the rule
engine's generic output back into the IntakeEvaluationResult response shape.

No regulatory classification logic (which article triggers what, which
frameworks/controls apply) lives in this file anymore - it all lives in the
versioned rules JSON, per spec #8/#9 (a configurable, non-hard-coded
applicability rule engine).
"""

from typing import Dict, Any
from aegis_app.schemas.schemas import IntakeQuestionnaireInput, IntakeEvaluationResult
from aegis_app.core.config import settings
from aegis_app.services.rule_engine import rule_engine

EU_COUNTRY_CODES = {"EU", "DE", "FR", "ES", "IT", "NL", "IE", "PL", "SE"}
HIGH_RISK_DOMAINS = {"employment", "credit", "education", "insurance", "healthcare", "biometrics"}


def _build_facts(data: IntakeQuestionnaireInput) -> Dict[str, Any]:
    deployment_countries_upper = [c.upper() for c in data.deployment_countries]
    high_risk_intersection = sorted(set(data.decision_domains) & HIGH_RISK_DOMAINS)
    eu_exposed = any(c in EU_COUNTRY_CODES for c in deployment_countries_upper)

    return {
        "system_name": data.system_name,
        "business_purpose": data.business_purpose,
        "business_purpose_lower": data.business_purpose.lower(),
        "business_unit": data.business_unit,
        "deployment_countries": deployment_countries_upper,
        "makes_decisions_about_individuals": data.makes_decisions_about_individuals,
        "decision_domains": data.decision_domains,
        "interacts_directly_with_humans": data.interacts_directly_with_humans,
        "generates_synthetic_content": data.generates_synthetic_content,
        "processes_personal_data": data.processes_personal_data,
        "processes_sensitive_personal_data": data.processes_sensitive_personal_data,
        "is_generative_ai": data.is_generative_ai,
        "uses_foundation_model": data.uses_foundation_model,
        "is_autonomous_agent": data.is_autonomous_agent,
        "agent_tools": data.agent_tools,
        "can_execute_code": data.can_execute_code,
        "can_access_database": data.can_access_database,
        "can_initiate_payments": data.can_initiate_payments,
        "human_in_the_loop_approval": data.human_in_the_loop_approval,
        # Derived facts
        "eu_exposed": eu_exposed,
        "high_risk_domain_intersection": high_risk_intersection,
    }


def evaluate_ai_system_applicability(data: IntakeQuestionnaireInput) -> IntakeEvaluationResult:
    """
    Evaluates an AI system's intake answers against the versioned applicability
    ruleset, producing an explainable classification with per-rule provenance.
    """
    facts = _build_facts(data)
    outcome = rule_engine.evaluate(facts)

    cybersecurity_applicable = ["NIST CSF 2.0", "OWASP Top 10 for LLM"]
    cybersecurity_rationale = "Baseline cybersecurity and prompt security controls apply."
    if outcome["agent_security_required"]:
        cybersecurity_applicable.append("OWASP Agentic AI Security Guidance")
        cybersecurity_rationale += (
            " System deploys autonomous agent capabilities (tools, code execution, database mutation, "
            "or payment initiation), triggering mandatory agent privilege boundaries, tool sandboxing, "
            "and emergency kill-switches."
        )

    result = IntakeEvaluationResult(
        system_name=data.system_name,
        risk_level=outcome["risk_level"],
        eu_ai_act_classification=outcome["eu_ai_act_classification"],
        eu_ai_act_rationale=outcome["eu_ai_act_rationale"],
        privacy_regulations_applicable=outcome["privacy_regulations_applicable"],
        privacy_rationale=outcome["privacy_rationale"],
        cybersecurity_regulations_applicable=cybersecurity_applicable,
        cybersecurity_rationale=cybersecurity_rationale,
        recommended_frameworks=outcome["recommended_frameworks"],
        required_unified_controls=outcome["required_unified_controls"],
        agent_security_required=outcome["agent_security_required"],
        disclaimer=settings.LEGAL_DISCLAIMER,
    )
    # Attached for callers that need rule-level provenance (persisted onto
    # ApplicabilityDecision by api/ai_systems.py) without widening the public
    # API response schema that the frontend/tests already depend on.
    result.rules_fired = outcome["rules_fired"]
    result.ruleset_version = outcome["ruleset_version"]
    return result
