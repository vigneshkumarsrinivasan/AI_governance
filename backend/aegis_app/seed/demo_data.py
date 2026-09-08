"""
Seed Script for Demonstration Tenant: Acme Financial Services.
Populates 5 realistic AI systems with distinct risk profiles, models, agents,
unified customer controls, evidence artifacts, risks, findings, and demo users.
"""

import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from aegis_app.core.database import AsyncSessionLocal, engine, Base
from aegis_app.core.security import get_password_hash
from aegis_app.models.models import (
    Tenant, Organization, User, AISystem, AIModel, AIAgent, Vendor,
    CustomerControl, Assessment, AssessmentResponse, Evidence, EvidenceControlMap,
    Risk, Finding, RemediationTask, AuditEvent
)
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.services.agent_risk import calculate_agent_risk_score

async def seed_demo_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing_user = await session.execute(select(User).where(User.email == "compliance@acmefinancial.com"))
        if existing_user.scalars().first():
            print("Demo data already seeded. Skipping.")
            return

        print("Seeding Acme Financial Services demo tenant...")
        
        # 1. Tenant & Organization
        tenant = Tenant(name="Acme Financial Services")
        session.add(tenant)
        await session.flush()

        org = Organization(
            tenant_id=tenant.id,
            name="Acme Financial Services Inc.",
            industry="Banking & Financial Services",
            headquarters_country="United States",
            countries_operating=["US", "EU", "GB", "SG"],
            employee_count=12500,
            is_financial_institution=True,
            is_critical_infrastructure=True,
            eu_market_exposure=True,
            is_demo=True
        )
        session.add(org)
        await session.flush()

        # 2. Demo Users (RBAC Roles)
        password_hash = get_password_hash("Password123!")
        users_data = [
            ("compliance@acmefinancial.com", "Sarah Jenkins", "AI Governance Lead"),
            ("ciso@acmefinancial.com", "David Vance", "CISO/Security"),
            ("risk@acmefinancial.com", "Elena Rostova", "Risk Manager"),
            ("ai-engineer@acmefinancial.com", "Marcus Chen", "AI Engineer"),
            ("auditor@acmefinancial.com", "Rachel Adams", "Auditor")
        ]
        
        created_users = []
        for email, name, role in users_data:
            user = User(
                tenant_id=tenant.id,
                organization_id=org.id,
                email=email,
                hashed_password=password_hash,
                full_name=name,
                role=role
            )
            session.add(user)
            created_users.append(user)
        await session.flush()
        lead_user = created_users[0]

        # Membership rows so the demo users appear in / can switch companies.
        from aegis_app.models.models import OrganizationMembership
        for u in created_users:
            session.add(OrganizationMembership(
                user_id=u.id, tenant_id=tenant.id, organization_id=org.id,
                role=u.role, is_default=True,
            ))
        await session.flush()

        # 3. Third-Party AI Vendors
        vendors_data = [
            Vendor(
                tenant_id=tenant.id,
                name="Anthropic PBC",
                service_type="Foundation Model API",
                models_provided=["Claude 3.5 Sonnet", "Claude 3 Haiku"],
                contract_status="Active Enterprise Agreement",
                data_retention_days=0,
                allows_customer_data_training=False,
                certifications=["SOC 2 Type II", "HIPAA", "ISO 27001"],
                risk_rating="Low",
                dpa_signed=True
            ),
            Vendor(
                tenant_id=tenant.id,
                name="OpenAI LLC",
                service_type="Foundation Model API",
                models_provided=["GPT-4o", "text-embedding-3-large"],
                contract_status="Active Enterprise Agreement",
                data_retention_days=0,
                allows_customer_data_training=False,
                certifications=["SOC 2 Type II", "ISO 27001"],
                risk_rating="Low",
                dpa_signed=True
            ),
            Vendor(
                tenant_id=tenant.id,
                name="Amazon Web Services (Bedrock)",
                service_type="Cloud Model Hosting Infrastructure",
                models_provided=["AWS Titan", "Hosted Llama-3"],
                contract_status="Active BAA",
                data_retention_days=0,
                allows_customer_data_training=False,
                certifications=["FedRAMP High", "SOC 1/2/3", "PCI-DSS"],
                risk_rating="Low",
                dpa_signed=True
            )
        ]
        for v in vendors_data:
            session.add(v)
        await session.flush()

        # 4. Five Realistic AI Systems
        # System 1: Customer Support Copilot
        sys1 = AISystem(
            tenant_id=tenant.id,
            organization_id=org.id,
            name="Customer Support Copilot",
            description="Conversational GenAI copilot assisting retail banking customers with account inquiries, transaction disputes, and balance verification using Retrieval-Augmented Generation (RAG).",
            business_purpose="Automate Tier-1 customer banking inquiries with 24/7 self-service.",
            owner="Sarah Jenkins",
            business_unit="Customer Operations",
            countries_deployed=["US", "GB", "DE", "FR"],
            users_affected_count=450000,
            internal_or_external="External",
            ai_technology="Generative AI (RAG)",
            model_provider="Anthropic",
            model_name="Claude 3.5 Sonnet",
            model_version="20241022",
            has_foundation_model=True,
            is_fine_tuned=False,
            uses_rag=True,
            is_generative_ai=True,
            is_agentic_ai=False,
            makes_autonomous_decisions=False,
            human_in_the_loop=True,
            processes_personal_data=True,
            processes_sensitive_data=False,
            deployment_environment="Cloud",
            cloud_provider="AWS",
            production_status="In Production",
            criticality="High",
            risk_classification="Specific Transparency",
            eu_ai_act_classification="Specific Transparency (Article 50)",
            classification_reasoning="Interacts directly with natural persons and generates synthetic conversational text, triggering Article 50 transparency obligations. Personal banking data processing activates GDPR Article 25.",
            applicable_frameworks=["eu_ai_act", "nist_ai_rmf", "nist_ai_600_1", "owasp_llm", "gdpr_ai", "dora"],
            kill_switch_implemented=True
        )
        session.add(sys1)

        # System 2: Loan Decision AI (High-Risk Annex III)
        sys2 = AISystem(
            tenant_id=tenant.id,
            organization_id=org.id,
            name="Loan Decision AI",
            description="Algorithmic credit evaluation and underwriting engine predicting default probability for personal loans and small business credit applications.",
            business_purpose="Automated credit scoring, risk tiering, and loan approval recommendations.",
            owner="Elena Rostova",
            business_unit="Credit Underwriting",
            countries_deployed=["US", "DE", "FR", "NL"],
            users_affected_count=85000,
            internal_or_external="Internal",
            ai_technology="Traditional ML (Gradient Boosted Trees)",
            model_provider="Internal ML Platform",
            model_name="Acme-CreditNet-v3",
            model_version="3.4.1",
            has_foundation_model=False,
            is_fine_tuned=True,
            uses_traditional_ml=True,
            is_generative_ai=False,
            makes_autonomous_decisions=True,
            human_in_the_loop=True,
            processes_personal_data=True,
            processes_sensitive_data=True,
            deployment_environment="Hybrid Cloud",
            cloud_provider="AWS",
            production_status="In Production",
            criticality="Critical",
            risk_classification="High Risk",
            eu_ai_act_classification="High-Risk AI System (Annex III)",
            classification_reasoning="Evaluates natural persons' creditworthiness and determines access to financial loans, directly triggering EU AI Act Annex III point 5(b) and GDPR Article 22 automated profiling constraints.",
            applicable_frameworks=["eu_ai_act", "nist_ai_rmf", "gdpr_ai", "dora", "singapore_ai_verify"],
            kill_switch_implemented=True
        )
        session.add(sys2)

        # System 3: Fraud Detection ML
        sys3 = AISystem(
            tenant_id=tenant.id,
            organization_id=org.id,
            name="Fraud Detection ML",
            description="Sub-millisecond inference engine analyzing credit card transactions in real-time to detect anomalous purchase patterns and syndicate fraud.",
            business_purpose="Prevent payment card fraud and protect financial infrastructure integrity.",
            owner="David Vance",
            business_unit="Financial Crime & Security",
            countries_deployed=["US", "EU", "GB", "SG"],
            users_affected_count=1200000,
            internal_or_external="Internal",
            ai_technology="Real-Time Tabular ML / Deep Autoencoder",
            model_provider="Internal Engineering",
            model_name="FraudShield-Realtime",
            model_version="5.1.0",
            uses_traditional_ml=True,
            is_generative_ai=False,
            makes_autonomous_decisions=True,
            human_in_the_loop=True,
            processes_personal_data=True,
            deployment_environment="Cloud",
            cloud_provider="AWS",
            production_status="In Production",
            criticality="Critical",
            risk_classification="High Risk",
            eu_ai_act_classification="Critical Infrastructure / High-Risk",
            classification_reasoning="Subject to DORA digital resilience and NIS2 critical security measures due to real-time transaction processing role in banking infrastructure.",
            applicable_frameworks=["dora", "nis2", "nist_csf_2", "nist_sp_800_53", "gdpr_ai"],
            kill_switch_implemented=True
        )
        session.add(sys3)

        # System 4: Internal Coding Assistant
        sys4 = AISystem(
            tenant_id=tenant.id,
            organization_id=org.id,
            name="Internal Coding Assistant",
            description="Developer productivity tool generating unit tests, code documentation, and boilerplate within IDEs via an enterprise-governed gateway.",
            business_purpose="Accelerate software engineering velocity while preventing proprietary code leakage.",
            owner="Marcus Chen",
            business_unit="Software Engineering",
            countries_deployed=["US", "EU", "GB"],
            users_affected_count=1800,
            internal_or_external="Internal",
            ai_technology="Generative AI (Code LLM)",
            model_provider="OpenAI",
            model_name="GPT-4o",
            model_version="2024-11-20",
            has_foundation_model=True,
            is_generative_ai=True,
            processes_personal_data=False,
            deployment_environment="Cloud",
            cloud_provider="Azure",
            production_status="In Production",
            criticality="Medium",
            risk_classification="Minimal Risk",
            eu_ai_act_classification="Minimal Legal Risk",
            classification_reasoning="Internal developer tool not interacting with general public or evaluating individuals.",
            applicable_frameworks=["nist_ai_rmf", "nist_sp_800_218", "owasp_llm", "uk_ai_cyber_code"],
            kill_switch_implemented=True
        )
        session.add(sys4)

        # System 5: Autonomous IT Support Agent
        sys5 = AISystem(
            tenant_id=tenant.id,
            organization_id=org.id,
            name="Autonomous IT Support Agent",
            description="Agentic AI capable of triaging internal IT helpdesk tickets, provisioning sandbox environments, executing read-only database queries, and generating Jira tasks.",
            business_purpose="Autonomous resolution of Tier-1 and Tier-2 internal enterprise IT requests.",
            owner="Marcus Chen",
            business_unit="IT Infrastructure",
            countries_deployed=["US", "EU"],
            users_affected_count=5000,
            internal_or_external="Internal",
            ai_technology="Agentic AI (Multi-Tool Autonomous)",
            model_provider="Anthropic",
            model_name="Claude 3.5 Sonnet",
            model_version="20241022",
            has_foundation_model=True,
            is_generative_ai=True,
            is_agentic_ai=True,
            makes_autonomous_decisions=True,
            human_in_the_loop=True,
            processes_personal_data=True,
            deployment_environment="Cloud",
            cloud_provider="AWS",
            production_status="In Production",
            criticality="High",
            risk_classification="High Risk",
            eu_ai_act_classification="Specific Risk / Autonomous Agent",
            classification_reasoning="Equipped with tool-calling capabilities (Jira API, SQL read, Python code executor), activating OWASP Agentic AI security controls and emergency kill-switch requirements.",
            applicable_frameworks=["owasp_agentic_ai", "owasp_llm", "nist_ai_600_1", "nist_csf_2"],
            kill_switch_implemented=True
        )
        session.add(sys5)
        await session.flush()

        # Add Agent Record for System 5
        agent_attrs = dict(
            has_code_execution=True,
            has_database_access=True,
            has_payment_access=False,
            has_email_access=False,
            autonomy_level="Semi-Autonomous",
            human_approval_required=True,
            kill_switch_active=False,
        )
        agent = AIAgent(
            tenant_id=tenant.id,
            system_id=sys5.id,
            name="IT-Ops-Agent-Alpha",
            purpose="Autonomous diagnostic and ticket resolution agent with tool execution capabilities.",
            tools=["jira_api_client", "sql_read_replica", "python_sandbox_runner", "active_directory_lookup"],
            permissions=["read:jira", "write:jira_comment", "read:db_replica", "exec:sandboxed_python"],
            risk_score=calculate_agent_risk_score(agent_attrs),
            **agent_attrs,
        )
        session.add(agent)
        await session.flush()

        # 5. Seed Customer Controls (Populated from Unified Control Library)
        all_uc = crosswalk_service.get_unified_controls()
        control_statuses = {
            "UC-AI-GOV-001": ("Implemented", "Effective", "Enterprise AI Governance Policy formally approved by Board Risk Committee in Q1 2026."),
            "UC-AI-GOV-002": ("Implemented", "Effective", "AI RACI matrix published; designated owners assigned to all 5 active systems."),
            "UC-AI-INV-001": ("Implemented", "Effective", "Centralized inventory complete and reconciled against AWS tag discoveries."),
            "UC-AI-INV-002": ("Implemented", "Effective", "Intake checkpoint active; 0 systems approved violating EU AI Act Art. 5."),
            "UC-AI-RSK-001": ("Implemented", "Effective", "Pre-deployment risk evaluations conducted for all high-risk assets."),
            "UC-AI-SEC-001": ("Implemented", "Effective", "Llama Guard 3 and NeMo guardrails deployed filtering direct/indirect injection."),
            "UC-AI-SEC-002": ("In Progress", "Partially Effective", "Automated cryptographic checksum validation in CI/CD pipeline."),
            "UC-AI-SEC-003": ("Implemented", "Effective", "Output sanitization middleware encoding all model completions."),
            "UC-AI-AGT-001": ("Implemented", "Effective", "IAM policies restrict agent tokens to ephemeral 15-minute tool scopes."),
            "UC-AI-AGT-002": ("Implemented", "Effective", "Hardware and software kill-switch tested semi-annually; halts loops in <2s."),
            "UC-AI-AGT-003": ("Implemented", "Effective", "Mandatory human approval gate enforced on all production schema changes."),
            "UC-AI-AGT-004": ("In Progress", "Partially Effective", "Partitioned scratchpad stores isolated per user session."),
            "UC-AI-AGT-005": ("Implemented", "Effective", "gVisor sandbox container isolates Python code execution."),
            "UC-AI-DAT-001": ("Implemented", "Effective", "Microsoft Presidio redaction mask active on customer support inputs."),
            "UC-AI-DAT-002": ("Implemented", "Effective", "DPIAs completed and signed by DPO for Loan AI and Customer Copilot."),
            "UC-AI-TRN-001": ("Implemented", "Effective", "Persistent banner in chatbot UI informs users of AI interaction."),
            "UC-AI-TRN-002": ("In Progress", "Partially Effective", "C2PA metadata integration underway for synthetic document exports."),
            "UC-AI-LOG-001": ("Implemented", "Effective", "Immutable audit logs streamed to Datadog/Splunk with 365-day retention."),
            "UC-AI-INC-001": ("Implemented", "Effective", "AI Incident Response Plan operational with 24h statutory alert triggers."),
            "UC-AI-SC-001": ("Implemented", "Effective", "Enterprise DPAs executed with Anthropic and OpenAI barring model training."),
            "UC-AI-SC-002": ("Implemented", "Effective", "Automated CycloneDX SBOM generated for all AI container builds."),
            "UC-AI-TST-001": ("Implemented", "Effective", "External red team completed jailbreak and adversarial evaluation in Jan 2026."),
            "UC-AI-TST-002": ("Tested", "Effective", "Disparate impact ratio verified at 0.89 across demographic classes on Loan AI."),
            "UC-AI-ACC-001": ("Implemented", "Effective", "RAG pipeline enforces vector citations and secondary fact-checking verifier."),
            "UC-AI-VUL-001": ("Implemented", "Effective", "Trivy daily container vulnerability scan enforcing 7-day critical SLA."),
            "UC-AI-VND-001": ("Implemented", "Effective", "Executed contract addenda guarantee zero training on customer data."),
            "UC-AI-RES-001": ("In Progress", "Partially Effective", "Multi-region failover between US-East and US-West active.")
        }

        for uc in all_uc:
            cid = uc["id"]
            status, eff, notes = control_statuses.get(cid, ("In Progress", "Partially Effective", "Standard operational control"))
            cc = CustomerControl(
                tenant_id=tenant.id,
                organization_id=org.id,
                control_id=cid,
                status=status,
                effectiveness=eff,
                implementation_notes=notes,
                owner="Sarah Jenkins"
            )
            session.add(cc)
        await session.flush()

        # 6. Realistic Evidence Artifacts (CRITICAL MOAT: Satisfying Multiple Controls)
        evidence_items = [
            (
                "Acme Enterprise Responsible AI & Governance Policy v2.1",
                "Executive board approved policy establishing trustworthy AI principles, accountability roles, and regulatory oversight.",
                "Policy",
                "https://storage.acmefinancial.internal/compliance/Acme_AI_Policy_2026.pdf",
                "Sarah Jenkins",
                ["UC-AI-GOV-001", "UC-AI-GOV-002", "UC-AI-INV-002", "UC-AI-RSK-001"]
            ),
            (
                "Customer Support Copilot Prompt Injection & Guardrail Penetration Test",
                "Third-party adversarial security evaluation report verifying Llama Guard 3 prompt firewall effectiveness against direct and indirect jailbreaks.",
                "Test Report",
                "https://storage.acmefinancial.internal/security/PenTest_Prompt_Injection_2026.pdf",
                "David Vance",
                ["UC-AI-SEC-001", "UC-AI-SEC-003", "UC-AI-TST-001", "UC-AI-ACC-001"]
            ),
            (
                "Autonomous IT Agent Permission Graph and Kill-Switch Architecture Spec",
                "Technical architecture documentation defining tool isolation boundaries, gVisor code sandboxing, and immutable kill-switch trigger runbook.",
                "Architecture",
                "https://storage.acmefinancial.internal/architecture/Agent_Security_Architecture.pdf",
                "Marcus Chen",
                ["UC-AI-AGT-001", "UC-AI-AGT-002", "UC-AI-AGT-003", "UC-AI-AGT-005"]
            ),
            (
                "Loan Decision AI Disparate Impact & Fairness Audit Report",
                "Quantitative fairness evaluation demonstrating demographic parity and 0.89 disparate impact ratio across protected demographic cohorts.",
                "Evaluation",
                "https://storage.acmefinancial.internal/audits/LoanAI_Fairness_Audit_Q1_2026.pdf",
                "Elena Rostova",
                ["UC-AI-TST-002", "UC-AI-DAT-002"]
            ),
            (
                "Enterprise Foundation Model Data Processing Agreement with No-Train Clause",
                "Signed enterprise contract addendum with Anthropic and OpenAI establishing zero data retention and strict prohibition against customer data model training.",
                "Policy",
                "https://storage.acmefinancial.internal/legal/Anthropic_OpenAI_Enterprise_DPA.pdf",
                "Sarah Jenkins",
                ["UC-AI-SC-001", "UC-AI-VND-001", "UC-AI-DAT-001"]
            )
        ]

        for title, desc, etype, url, owner, cids in evidence_items:
            sha = hashlib.sha256((title + url).encode("utf-8")).hexdigest()
            ev = Evidence(
                tenant_id=tenant.id,
                organization_id=org.id,
                title=title,
                description=desc,
                evidence_type=etype,
                file_url=url,
                file_hash_sha256=sha,
                owner=owner,
                approval_status="Approved",
                expiry_date=datetime.now(timezone.utc) + timedelta(days=300)
            )
            session.add(ev)
            await session.flush()
            
            for cid in cids:
                mapping = EvidenceControlMap(evidence_id=ev.id, control_id=cid)
                session.add(mapping)
        await session.flush()

        # 7. AI Risks
        risks_data = [
            Risk(
                tenant_id=tenant.id,
                organization_id=org.id,
                system_id=sys1.id,
                risk_code="RSK-AI-001",
                title="Adversarial Prompt Injection via User Chat Input",
                description="Malicious user attempts to override system prompt instructions to extract private customer records.",
                category="Security",
                threat_source="External Adversary",
                inherent_likelihood=4,
                inherent_impact=4,
                inherent_score=16,
                residual_likelihood=1,
                residual_impact=2,
                residual_score=2,
                treatment="Mitigate",
                status="In Progress",
                owner="David Vance",
                mitre_atlas_technique="AML.T0051",
                owasp_category="LLM01: Prompt Injection"
            ),
            Risk(
                tenant_id=tenant.id,
                organization_id=org.id,
                system_id=sys2.id,
                risk_code="RSK-AI-002",
                title="Algorithmic Demographic Bias in Credit Underwriting",
                description="Historical credit training data skew could lead to disparate impact against protected demographic groups.",
                category="Fairness",
                threat_source="Training Data Skew",
                inherent_likelihood=3,
                inherent_impact=5,
                inherent_score=15,
                residual_likelihood=1,
                residual_impact=2,
                residual_score=2,
                treatment="Mitigate",
                status="Open",
                owner="Elena Rostova",
                mitre_atlas_technique="AML.T0043",
                owasp_category="Algorithmic Fairness"
            ),
            Risk(
                tenant_id=tenant.id,
                organization_id=org.id,
                system_id=sys5.id,
                risk_code="RSK-AI-003",
                title="Autonomous Agent Tool Privilege Escalation",
                description="Agent attempts unauthorized database write or executes unvetted shell commands in IT environment.",
                category="Agent",
                threat_source="Agent Logic Runaway",
                inherent_likelihood=3,
                inherent_impact=4,
                inherent_score=12,
                residual_likelihood=1,
                residual_impact=2,
                residual_score=2,
                treatment="Mitigate",
                status="In Progress",
                owner="Marcus Chen",
                mitre_atlas_technique="AML.T0051",
                owasp_category="AGENT-01: Privilege Escalation"
            )
        ]
        for r in risks_data:
            session.add(r)
        await session.flush()

        # 8. Findings & Remediations
        finding1 = Finding(
            tenant_id=tenant.id,
            organization_id=org.id,
            system_id=sys5.id,
            risk_id=risks_data[2].id,
            control_id="UC-AI-AGT-004",
            title="Agent Persistent Memory Isolation Lacks Ephemeral Token Expiry",
            description="Agent memory scratchpads persist session context beyond 24 hours without automatic token revocation.",
            severity="Medium",
            source="Internal Security Review",
            status="Open",
            due_date=datetime.now(timezone.utc) + timedelta(days=21)
        )
        session.add(finding1)
        await session.flush()

        rem1 = RemediationTask(
            tenant_id=tenant.id,
            finding_id=finding1.id,
            title="Implement Redis 1-Hour TTL on Agent Context Scratchpads",
            description="Configure automated session key expiry on agent vector stores to enforce strict memory isolation.",
            assigned_to="Marcus Chen",
            priority="Medium",
            status="In Progress",
            target_date=datetime.now(timezone.utc) + timedelta(days=14)
        )
        session.add(rem1)

        # Audit Event
        audit_init = AuditEvent(
            tenant_id=tenant.id,
            actor_id=lead_user.id,
            actor_email=lead_user.email,
            action="INITIALIZE_DEMO_TENANT",
            object_type="Tenant",
            object_id=tenant.id,
            changes={"tenant_name": tenant.name, "systems_seeded": 5}
        )
        session.add(audit_init)

        await session.commit()
        print("Successfully seeded Acme Financial Services demo tenant with 5 AI systems!")

if __name__ == "__main__":
    asyncio.run(seed_demo_data())
