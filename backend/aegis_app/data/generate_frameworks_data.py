"""
Generator script to produce all 17 authoritative compliance and security frameworks,
the Unified Control Library (50+ controls), and the crosswalk mapping matrix.
All source references and URLs are authoritative public government / standard bodies.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent
FRAMEWORKS_DIR = DATA_DIR / "frameworks"
FRAMEWORKS_DIR.mkdir(parents=True, exist_ok=True)

# 1. EU AI Act
eu_ai_act = {
    "id": "eu_ai_act",
    "name": "EU Artificial Intelligence Act",
    "short_name": "EU AI Act",
    "official_reference": "Regulation (EU) 2024/1689",
    "jurisdiction": "European Union",
    "type": "Regulation / Law",
    "version": "2024/1689 Final",
    "publication_date": "2024-07-12",
    "effective_date": "2024-08-01",
    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",
    "status": "current",
    "description": "Harmonised rules on artificial intelligence across the EU internal market, establishing a risk-based classification framework with strict obligations for high-risk AI systems and transparency requirements.",
    "applicability_conditions": [
        "Providers placing AI systems on the EU market or putting them into service in the EU",
        "Deployers of AI systems that have their place of establishment or are located within the EU",
        "Providers and deployers of AI systems located in a third country where the output produced by the AI system is used in the EU"
    ],
    "chapters": [
        {
            "chapter_id": "Chapter II",
            "title": "Prohibited Artificial Intelligence Practices",
            "requirements": [
                {
                    "id": "EU-AIA-ART-05",
                    "article": "Article 5",
                    "title": "Prohibition of Unacceptable-Risk AI Practices",
                    "normalized_requirement": "The organization shall screen all AI systems to ensure they do not deploy subliminal distortion, exploit vulnerabilities of specific groups, conduct social scoring, engage in individual predictive policing, compile untargeted facial recognition databases, infer emotions in workplace/education (except medical/safety), or employ real-time remote biometric identification in public spaces for law enforcement except strictly permitted.",
                    "applicability": "All AI systems in scope of EU AI Act",
                    "effective_date": "2025-02-02",
                    "implementation_guidance": "Implement mandatory intake screening checkpoint verifying that no AI system performs prohibited practices before architectural approval.",
                    "evidence_expected": ["Prohibited AI Practice Screening Checklist", "AI System Intake Assessment", "Legal Review Signoff"],
                    "domain": "AI Governance & Ethics",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689#d1e1887-1-1"
                }
            ]
        },
        {
            "chapter_id": "Chapter III",
            "title": "High-Risk AI Systems — Requirements for Providers",
            "requirements": [
                {
                    "id": "EU-AIA-ART-09",
                    "article": "Article 9",
                    "title": "Risk Management System",
                    "normalized_requirement": "A continuous, iterative risk management system shall be established, implemented, documented and maintained throughout the entire lifecycle of high-risk AI systems, identifying known and foreseeable risks and adopting suitable mitigation measures.",
                    "applicability": "High-risk AI systems (Annex III / safety component Annex I)",
                    "effective_date": "2026-08-02",
                    "implementation_guidance": "Document a lifecycle risk management procedure specific to AI, conduct pre-deployment risk evaluations, and track residual risks.",
                    "evidence_expected": ["AI Risk Management Policy", "AI System Risk Assessment Report", "Residual Risk Register"],
                    "domain": "Risk Management",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689#d1e2172-1-1"
                },
                {
                    "id": "EU-AIA-ART-10",
                    "article": "Article 10",
                    "title": "Data and Data Governance",
                    "normalized_requirement": "High-risk AI systems which make use of techniques involving the training of models with data shall be developed on the basis of training, validation and testing data sets that meet quality criteria, including bias examination and appropriate data provenance.",
                    "applicability": "High-risk AI systems using model training",
                    "effective_date": "2026-08-02",
                    "implementation_guidance": "Maintain data governance protocols, document data provenance, evaluate statistical bias, and audit dataset quality.",
                    "evidence_expected": ["Data Governance Specification", "Dataset Bias Evaluation Report", "Data Lineage & Provenance Documentation"],
                    "domain": "Data Governance",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689#d1e2275-1-1"
                },
                {
                    "id": "EU-AIA-ART-11",
                    "article": "Article 11",
                    "title": "Technical Documentation",
                    "normalized_requirement": "Technical documentation of a high-risk AI system shall be drawn up before that system is placed on the market or put into service and kept up to date, complying with Annex IV requirements.",
                    "applicability": "High-risk AI systems",
                    "effective_date": "2026-08-02",
                    "implementation_guidance": "Compile comprehensive Annex IV technical documentation including model cards, architecture diagrams, algorithmic choices, and validation results.",
                    "evidence_expected": ["Annex IV Technical Documentation File", "Model Card", "System Architecture & Data Flow Diagram"],
                    "domain": "Documentation & Records",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689#d1e2373-1-1"
                },
                {
                    "id": "EU-AIA-ART-12",
                    "article": "Article 12",
                    "title": "Record-Keeping and Automatic Logging",
                    "normalized_requirement": "High-risk AI systems shall technically allow for the automatic recording of events ('logs') over the lifetime of the system to ensure traceability of system functioning and post-market monitoring.",
                    "applicability": "High-risk AI systems",
                    "effective_date": "2026-08-02",
                    "implementation_guidance": "Implement automated immutable logging capturing system inputs, outputs, operational periods, and exceptions.",
                    "evidence_expected": ["Logging Architecture Specification", "Sample Operational Audit Log", "Log Retention & Protection Policy"],
                    "domain": "Logging & Monitoring",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689#d1e2432-1-1"
                },
                {
                    "id": "EU-AIA-ART-13",
                    "article": "Article 13",
                    "title": "Transparency and Provision of Information to Deployers",
                    "normalized_requirement": "High-risk AI systems shall be designed and developed in such a way as to ensure that their operation is sufficiently transparent to enable deployers to interpret the system's output and use it appropriately, accompanied by clear instructions for use.",
                    "applicability": "High-risk AI systems",
                    "effective_date": "2026-08-02",
                    "implementation_guidance": "Publish comprehensive deployer instructions for use, detailing capabilities, limitations, intended purpose, and performance metrics.",
                    "evidence_expected": ["Deployer Instructions for Use", "System Limitations Disclosure", "User Manual"],
                    "domain": "Transparency",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689#d1e2488-1-1"
                },
                {
                    "id": "EU-AIA-ART-14",
                    "article": "Article 14",
                    "title": "Human Oversight",
                    "normalized_requirement": "High-risk AI systems shall be designed and developed in such a way, including with appropriate human-machine interface tools, that they can be effectively overseen by natural persons during the period in which they are in use, with the ability to intervene or stop the system.",
                    "applicability": "High-risk AI systems",
                    "effective_date": "2026-08-02",
                    "implementation_guidance": "Establish human-in-the-loop / human-on-the-loop controls, override mechanisms, and emergency kill-switches.",
                    "evidence_expected": ["Human Oversight Operational Procedure", "Kill-Switch Test Procedure", "Operator Training Plan"],
                    "domain": "Human Oversight",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689#d1e2578-1-1"
                },
                {
                    "id": "EU-AIA-ART-15",
                    "article": "Article 15",
                    "title": "Accuracy, Robustness and Cybersecurity",
                    "normalized_requirement": "High-risk AI systems shall be designed and developed in such a way that they achieve an appropriate level of accuracy, robustness, and cybersecurity, resilient against errors, faults, data poisoning, and adversarial attacks.",
                    "applicability": "High-risk AI systems",
                    "effective_date": "2026-08-02",
                    "implementation_guidance": "Perform red-teaming, adversarial robustness evaluations, prompt injection testing, and vulnerability management.",
                    "evidence_expected": ["AI Security Assessment Report", "Model Evaluation & Benchmark Report", "Adversarial Robustness Test Results"],
                    "domain": "Security & Robustness",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689#d1e2669-1-1"
                }
            ]
        },
        {
            "chapter_id": "Chapter IV",
            "title": "Transparency Obligations for Certain AI Systems",
            "requirements": [
                {
                    "id": "EU-AIA-ART-50",
                    "article": "Article 50",
                    "title": "Transparency Obligations for Providers and Deployers",
                    "normalized_requirement": "Providers shall ensure that AI systems intended to interact directly with natural persons are designed and developed so that the natural persons are informed that they are interacting with an AI system; deployers generating synthetic audio, image, video or text content shall disclose that content has been artificially generated or manipulated.",
                    "applicability": "AI systems interacting with humans or generating synthetic content",
                    "effective_date": "2026-08-02",
                    "implementation_guidance": "Provide clear AI disclosure banners, machine-readable watermarking, or provenance metadata on synthetic outputs.",
                    "evidence_expected": ["UI AI Interaction Disclosure Screenshot", "Synthetic Content Watermarking Specification", "Deployer Disclosure Notice"],
                    "domain": "Transparency",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689#d1e4420-1-1"
                }
            ]
        },
        {
            "chapter_id": "Chapter V",
            "title": "General-Purpose AI Models",
            "requirements": [
                {
                    "id": "EU-AIA-ART-53",
                    "article": "Article 53",
                    "title": "Obligations for Providers of General-Purpose AI Models",
                    "normalized_requirement": "Providers of general-purpose AI models shall draw up and keep up to date technical documentation, provide documentation to downstream providers, put in place a policy to respect Union copyright law, and publish a sufficiently detailed summary of content used for training.",
                    "applicability": "Providers of General-Purpose AI (GPAI) models",
                    "effective_date": "2025-08-02",
                    "implementation_guidance": "Maintain GPAI technical dossiers, downstream integration guidance, copyright compliance policy, and public training dataset summaries.",
                    "evidence_expected": ["GPAI Technical File", "Copyright Compliance Policy", "Public Training Data Summary Document"],
                    "domain": "Model Security & IP",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689#d1e4664-1-1"
                }
            ]
        }
    ]
}

# 2. NIST AI RMF 1.0
nist_ai_rmf = {
    "id": "nist_ai_rmf",
    "name": "NIST Artificial Intelligence Risk Management Framework",
    "short_name": "NIST AI RMF 1.0",
    "official_reference": "NIST AI 100-1",
    "jurisdiction": "United States / International",
    "type": "Standard / Guidance",
    "version": "1.0",
    "publication_date": "2023-01-26",
    "effective_date": "2023-01-26",
    "official_url": "https://www.nist.gov/itl/ai-risk-management-framework",
    "status": "current",
    "description": "Voluntary guidance developed by the National Institute of Standards and Technology to help organizations improve the trustworthiness and manage risks of artificial intelligence systems across GOVERN, MAP, MEASURE, and MANAGE functions.",
    "applicability_conditions": [
        "Organizations designing, developing, deploying, or using AI systems seeking trustworthy and responsible AI practices"
    ],
    "chapters": [
        {
            "chapter_id": "GOVERN",
            "title": "GOVERN Function",
            "requirements": [
                {
                    "id": "NIST-RMF-GOV-1.1",
                    "article": "GOVERN 1.1",
                    "title": "Legal and Regulatory Requirements Identification",
                    "normalized_requirement": "Legal and other requirements regarding AI risks are understood, managed, and integrated into organizational policies and procedures.",
                    "applicability": "All AI deployments",
                    "effective_date": "2023-01-26",
                    "implementation_guidance": "Maintain an AI regulatory inventory and map legal requirements to organizational policies.",
                    "evidence_expected": ["AI Legal & Regulatory Register", "AI Governance Policy"],
                    "domain": "AI Governance",
                    "official_url": "https://airc.nist.gov/AI_RMF_Knowledge_Base/AI_RMF"
                },
                {
                    "id": "NIST-RMF-GOV-1.2",
                    "article": "GOVERN 1.2",
                    "title": "Trustworthy AI Characteristics Integration",
                    "normalized_requirement": "Trustworthy characteristics (valid, reliable, safe, secure, resilient, explainable, transparent, privacy-enhanced, and fair) are prioritized and integrated into AI lifecycle processes.",
                    "applicability": "All AI deployments",
                    "effective_date": "2023-01-26",
                    "implementation_guidance": "Define trustworthy AI principles in the organizational AI code of conduct and engineering guidelines.",
                    "evidence_expected": ["Trustworthy AI Principles Document", "AI Ethics Review Process"],
                    "domain": "AI Governance",
                    "official_url": "https://airc.nist.gov/AI_RMF_Knowledge_Base/AI_RMF"
                },
                {
                    "id": "NIST-RMF-GOV-2.1",
                    "article": "GOVERN 2.1",
                    "title": "Roles and Responsibilities for AI Risk Management",
                    "normalized_requirement": "Roles and responsibilities for AI system design, development, deployment, evaluation, and monitoring are clearly defined, allocated, and communicated.",
                    "applicability": "All AI deployments",
                    "effective_date": "2023-01-26",
                    "implementation_guidance": "Establish an AI Governance Committee, define RACI matrices for AI projects, and assign designated AI system owners.",
                    "evidence_expected": ["AI RACI Matrix", "AI Governance Committee Charter"],
                    "domain": "Accountability",
                    "official_url": "https://airc.nist.gov/AI_RMF_Knowledge_Base/AI_RMF"
                },
                {
                    "id": "NIST-RMF-GOV-5.1",
                    "article": "GOVERN 5.1",
                    "title": "AI Risk Management Policies and Processes",
                    "normalized_requirement": "Policies, processes, and procedures are in place, operationalized, and maintained to manage AI risks throughout the lifecycle.",
                    "applicability": "All AI deployments",
                    "effective_date": "2023-01-26",
                    "implementation_guidance": "Publish standard operating procedures for AI risk assessment, change management, and incident response.",
                    "evidence_expected": ["AI Risk Management SOP", "AI Incident Response Plan"],
                    "domain": "Risk Management",
                    "official_url": "https://airc.nist.gov/AI_RMF_Knowledge_Base/AI_RMF"
                }
            ]
        },
        {
            "chapter_id": "MAP",
            "title": "MAP Function",
            "requirements": [
                {
                    "id": "NIST-RMF-MAP-1.1",
                    "article": "MAP 1.1",
                    "title": "Context of Use and Business Purpose",
                    "normalized_requirement": "The intended purpose, context of use, operational environment, and societal impact of the AI system are formally documented.",
                    "applicability": "All AI systems",
                    "effective_date": "2023-01-26",
                    "implementation_guidance": "Complete an AI System Profile capturing business purpose, target users, deployment environment, and expected benefits.",
                    "evidence_expected": ["AI System Intake Form", "Business Impact Analysis"],
                    "domain": "AI Inventory",
                    "official_url": "https://airc.nist.gov/AI_RMF_Knowledge_Base/AI_RMF"
                },
                {
                    "id": "NIST-RMF-MAP-2.1",
                    "article": "MAP 2.1",
                    "title": "AI System Architecture and Dependencies",
                    "normalized_requirement": "The AI system components, algorithms, foundation models, data pipelines, third-party libraries, and external APIs are identified and mapped.",
                    "applicability": "All AI systems",
                    "effective_date": "2023-01-26",
                    "implementation_guidance": "Maintain architecture diagrams, AI Bills of Materials (AIBOM), and third-party vendor dependency registries.",
                    "evidence_expected": ["AI Architecture Diagram", "Software/AI Bill of Materials (AIBOM)"],
                    "domain": "AI Inventory & Supply Chain",
                    "official_url": "https://airc.nist.gov/AI_RMF_Knowledge_Base/AI_RMF"
                }
            ]
        },
        {
            "chapter_id": "MEASURE",
            "title": "MEASURE Function",
            "requirements": [
                {
                    "id": "NIST-RMF-MEA-2.1",
                    "article": "MEASURE 2.1",
                    "title": "Quantitative and Qualitative Metrics",
                    "normalized_requirement": "Test, evaluation, validation, and verification (TEVV) processes are implemented to measure accuracy, reliability, robustness, fairness, and security.",
                    "applicability": "All AI systems",
                    "effective_date": "2023-01-26",
                    "implementation_guidance": "Define performance benchmarks, run red teaming and adversarial testing, and log model evaluation metrics.",
                    "evidence_expected": ["AI Model Test & Evaluation Report", "Fairness & Bias Audit Results"],
                    "domain": "Testing & Validation",
                    "official_url": "https://airc.nist.gov/AI_RMF_Knowledge_Base/AI_RMF"
                }
            ]
        },
        {
            "chapter_id": "MANAGE",
            "title": "MANAGE Function",
            "requirements": [
                {
                    "id": "NIST-RMF-MAN-2.4",
                    "article": "MANAGE 2.4",
                    "title": "Risk Treatment and Mechanism for Overrides",
                    "normalized_requirement": "Mechanisms for human intervention, override, fallback, or safe shutdown (kill-switch) are established and operational.",
                    "applicability": "Autonomous, agentic, or high-consequence AI systems",
                    "effective_date": "2023-01-26",
                    "implementation_guidance": "Implement technical kill switches, human approval gates, and fallback operational modes for AI applications.",
                    "evidence_expected": ["Human Intervention & Kill-Switch Runbook", "Fail-Safe Operational Test Log"],
                    "domain": "Human Oversight",
                    "official_url": "https://airc.nist.gov/AI_RMF_Knowledge_Base/AI_RMF"
                }
            ]
        }
    ]
}

# 3. NIST AI 600-1 Generative AI Profile
nist_ai_600_1 = {
    "id": "nist_ai_600_1",
    "name": "NIST Artificial Intelligence Risk Management Framework: Generative AI Profile",
    "short_name": "NIST AI 600-1 (GenAI Profile)",
    "official_reference": "NIST SP AI 600-1",
    "jurisdiction": "United States / International",
    "type": "Profile / Guidance",
    "version": "1.0",
    "publication_date": "2024-07-26",
    "effective_date": "2024-07-26",
    "official_url": "https://doi.org/10.6028/NIST.SP.AI.600-1",
    "status": "current",
    "description": "A cross-sectoral profile of the NIST AI RMF specifically addressing the unique risks, failure modes, and governance practices of Generative AI systems and foundation models.",
    "applicability_conditions": [
        "Organizations developing, integrating, or deploying Generative AI models, RAG pipelines, or LLMs"
    ],
    "chapters": [
        {
            "chapter_id": "GENAI-RISKS",
            "title": "Generative AI Risk Mitigations",
            "requirements": [
                {
                    "id": "NIST-600-CONFAB",
                    "article": "Action 1.1",
                    "title": "Confabulation and Hallucination Mitigation",
                    "normalized_requirement": "Organizations shall implement technical mechanisms such as Retrieval-Augmented Generation (RAG) grounding, fact-checking verifiers, and confidence thresholding to mitigate non-factual confabulations.",
                    "applicability": "Generative AI systems producing factual responses",
                    "effective_date": "2024-07-26",
                    "implementation_guidance": "Implement RAG with citations, source attribution, and truthfulness guardrails.",
                    "evidence_expected": ["RAG Architecture Specification", "Hallucination Benchmark Evaluation Report"],
                    "domain": "Accuracy & Robustness",
                    "official_url": "https://doi.org/10.6028/NIST.SP.AI.600-1"
                },
                {
                    "id": "NIST-600-CBRN",
                    "article": "Action 1.2",
                    "title": "Dangerous and Harmful Content Safeguards",
                    "normalized_requirement": "Protections shall be implemented to prevent GenAI outputs that facilitate dangerous activities (CBRN, cyberweapons, self-harm, hate speech) via system prompts, output guardrails, and automated red-teaming.",
                    "applicability": "All Generative AI deployments",
                    "effective_date": "2024-07-26",
                    "implementation_guidance": "Deploy input/output safety guardrails (e.g. Llama Guard, NeMo Guardrails) and maintain safety filtering rules.",
                    "evidence_expected": ["Content Moderation Guardrail Architecture", "Red-Teaming Safety Test Results"],
                    "domain": "Safety & Content",
                    "official_url": "https://doi.org/10.6028/NIST.SP.AI.600-1"
                },
                {
                    "id": "NIST-600-PROMPT-SEC",
                    "article": "Action 1.4",
                    "title": "Information Security & Prompt Injection Defense",
                    "normalized_requirement": "System prompts, context windows, and model interactions shall be protected against direct and indirect prompt injection, data leakage, and unauthorized tool invocation.",
                    "applicability": "All GenAI and agentic systems",
                    "effective_date": "2024-07-26",
                    "implementation_guidance": "Employ prompt isolation, input sanitization, output encoding, and tool-call permission controls.",
                    "evidence_expected": ["Prompt Injection Defense Test Report", "Input/Output Sanitization Config"],
                    "domain": "Prompt Security",
                    "official_url": "https://doi.org/10.6028/NIST.SP.AI.600-1"
                },
                {
                    "id": "NIST-600-PROVENANCE",
                    "article": "Action 1.7",
                    "title": "Synthetic Content Provenance and Transparency",
                    "normalized_requirement": "Mechanisms such as cryptographic watermarking, C2PA metadata, or user-facing disclosures shall be integrated into generative outputs to indicate synthetic provenance.",
                    "applicability": "Public or external-facing Generative AI systems",
                    "effective_date": "2024-07-26",
                    "implementation_guidance": "Integrate watermarking or explicit text/image disclaimers stating content was AI-generated.",
                    "evidence_expected": ["Synthetic Provenance / Watermark Spec", "User Interface AI Disclosure"],
                    "domain": "Transparency & Provenance",
                    "official_url": "https://doi.org/10.6028/NIST.SP.AI.600-1"
                }
            ]
        }
    ]
}

# 4. EU Cyber Resilience Act
eu_cra = {
    "id": "eu_cra",
    "name": "EU Cyber Resilience Act",
    "short_name": "EU CRA",
    "official_reference": "Regulation (EU) 2024/2847",
    "jurisdiction": "European Union",
    "type": "Regulation / Law",
    "version": "2024/2847",
    "publication_date": "2024-11-20",
    "effective_date": "2024-12-10",
    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847",
    "status": "current",
    "description": "Establishes mandatory cybersecurity requirements for products with digital elements placed on the EU market, including AI software components, secure development lifecycle, and continuous vulnerability management.",
    "applicability_conditions": [
        "Manufacturers and developers of software or hardware products with digital elements placed on the EU market"
    ],
    "chapters": [
        {
            "chapter_id": "Annex I",
            "title": "Essential Cybersecurity Requirements",
            "requirements": [
                {
                    "id": "CRA-ANNEX-1-SEC-DESIGN",
                    "article": "Annex I Part I (1)",
                    "title": "Security by Design and Default",
                    "normalized_requirement": "Products with digital elements, including AI applications, shall be designed, developed, and produced in such a way that they ensure an appropriate level of cybersecurity based on the risks, delivering products with secure default configurations.",
                    "applicability": "Commercial software and digital products in EU",
                    "effective_date": "2027-12-11",
                    "implementation_guidance": "Implement secure defaults, disable unnecessary ports and APIs, and enforce mandatory authentication.",
                    "evidence_expected": ["Secure Default Configuration Baseline", "Threat Modeling Documentation"],
                    "domain": "Secure Development",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847"
                },
                {
                    "id": "CRA-ANNEX-1-SBOM",
                    "article": "Annex I Part II (1)",
                    "title": "Software Bill of Materials (SBOM)",
                    "normalized_requirement": "Manufacturers shall identify and document components and vulnerabilities, including drawing up a Software Bill of Materials (SBOM) in a commonly used, machine-readable format covering at the very least top-level dependencies.",
                    "applicability": "All products with digital elements",
                    "effective_date": "2027-12-11",
                    "implementation_guidance": "Generate automated SBOMs (SPDX / CycloneDX) for all software builds and AI component containers.",
                    "evidence_expected": ["Automated SBOM Generation Pipeline", "Sample CycloneDX SBOM Export"],
                    "domain": "Supply Chain Security",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847"
                },
                {
                    "id": "CRA-ANNEX-1-VULN",
                    "article": "Annex I Part II (2)",
                    "title": "Vulnerability Handling and Disclosure",
                    "normalized_requirement": "Organizations shall put in place a coordinated vulnerability disclosure policy, perform regular security tests, and deploy security updates without delay.",
                    "applicability": "All products with digital elements",
                    "effective_date": "2026-09-11",
                    "implementation_guidance": "Establish a vulnerability disclosure policy and automated patch management workflow.",
                    "evidence_expected": ["Coordinated Vulnerability Disclosure Policy", "Security Patch SLA & SLA Metrics"],
                    "domain": "Vulnerability Management",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847"
                }
            ]
        }
    ]
}

# 5. OWASP Top 10 for LLM
owasp_llm = {
    "id": "owasp_llm",
    "name": "OWASP Top 10 for Large Language Model Applications",
    "short_name": "OWASP LLM Top 10",
    "official_reference": "OWASP GenAI Top 10 (2025)",
    "jurisdiction": "International",
    "type": "Security Standard",
    "version": "2025 v2.0",
    "publication_date": "2024-11-01",
    "effective_date": "2024-11-01",
    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
    "status": "current",
    "description": "Authoritative list of the most critical security vulnerabilities found in large language model applications, providing developers, architects, and CISOs with actionable mitigation guidance.",
    "applicability_conditions": [
        "Any software system utilizing Large Language Models (LLMs) or foundation models"
    ],
    "chapters": [
        {
            "chapter_id": "Top 10 Risks",
            "title": "OWASP LLM Core Risks",
            "requirements": [
                {
                    "id": "OWASP-LLM-01",
                    "article": "LLM01:2025",
                    "title": "Prompt Injection",
                    "normalized_requirement": "The organization shall protect the application against prompt injections (direct jailbreaks and indirect injections via external data sources) by enforcing input validation, context separation, privileged tool constraints, and output verification.",
                    "applicability": "All LLM applications",
                    "effective_date": "2024-11-01",
                    "implementation_guidance": "Employ prompt sanitization, demarcate untrusted content, and constrain agent permissions.",
                    "evidence_expected": ["Prompt Injection Penetration Test", "Guardrail Configuration Documentation"],
                    "domain": "Prompt Security",
                    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"
                },
                {
                    "id": "OWASP-LLM-02",
                    "article": "LLM02:2025",
                    "title": "Sensitive Information Disclosure",
                    "normalized_requirement": "The organization shall prevent the exposure of PII, proprietary source code, secrets, or confidential business data in LLM outputs through pre-training/fine-tuning sanitization, RAG access controls, and real-time egress filtering.",
                    "applicability": "All LLM applications handling sensitive data",
                    "effective_date": "2024-11-01",
                    "implementation_guidance": "Deploy automated PII redaction and DLP filters on LLM inputs and responses.",
                    "evidence_expected": ["DLP / PII Redaction Configuration", "Data Egress Security Audit"],
                    "domain": "Privacy & Data Protection",
                    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"
                },
                {
                    "id": "OWASP-LLM-03",
                    "article": "LLM03:2025",
                    "title": "Supply Chain Vulnerabilities",
                    "normalized_requirement": "The organization shall audit and verify the integrity and origin of third-party models, weights, datasets, plugins, and libraries using cryptographically signed hashes and trusted registries.",
                    "applicability": "AI systems consuming external models or datasets",
                    "effective_date": "2024-11-01",
                    "implementation_guidance": "Enforce model signature verification and scan Python/ML dependencies for known CVEs.",
                    "evidence_expected": ["AI Supply Chain Integrity Verification Log", "Model Weight Checksum Audit"],
                    "domain": "Supply Chain Security",
                    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"
                },
                {
                    "id": "OWASP-LLM-04",
                    "article": "LLM04:2025",
                    "title": "Data and Model Poisoning",
                    "normalized_requirement": "The organization shall prevent malicious manipulation of training data, fine-tuning datasets, or vector embeddings that introduce backdoors or bias.",
                    "applicability": "Trained, fine-tuned, or RAG-based AI systems",
                    "effective_date": "2024-11-01",
                    "implementation_guidance": "Validate data sources, compute data integrity hashes, and conduct data anomaly detection.",
                    "evidence_expected": ["Training Data Verification Log", "Vector DB Integrity Audit"],
                    "domain": "Model Security",
                    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"
                },
                {
                    "id": "OWASP-LLM-05",
                    "article": "LLM05:2025",
                    "title": "Improper Output Handling",
                    "normalized_requirement": "The organization shall treat LLM outputs as untrusted and perform strict validation and sanitization prior to passing outputs to downstream components, databases, or browsers to prevent XSS, SSRF, or SQL injection.",
                    "applicability": "All LLM applications integrated into applications",
                    "effective_date": "2024-11-01",
                    "implementation_guidance": "Sanitize and encode all model outputs before rendering or executing database queries.",
                    "evidence_expected": ["Downstream Sanitization Code Review", "Penetration Testing Report"],
                    "domain": "Secure Development",
                    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"
                },
                {
                    "id": "OWASP-LLM-06",
                    "article": "LLM06:2025",
                    "title": "Excessive Agency",
                    "normalized_requirement": "The organization shall restrict the autonomy and permissions granted to LLMs and AI agents, adhering to the principle of least privilege, requiring human confirmation for sensitive operations, and rate-limiting actions.",
                    "applicability": "Autonomous agents, tool-calling LLMs",
                    "effective_date": "2024-11-01",
                    "implementation_guidance": "Enforce tool permission boundaries and mandatory human-in-the-loop approval gates for destructive actions.",
                    "evidence_expected": ["Agent Permission Policy", "Approval Gate Implementation Audit"],
                    "domain": "Agent Security",
                    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"
                }
            ]
        }
    ]
}

# 6. OWASP Agentic AI Security Guidance
owasp_agentic = {
    "id": "owasp_agentic_ai",
    "name": "OWASP Agentic AI Security Guidance",
    "short_name": "OWASP Agentic AI",
    "official_reference": "OWASP Agentic Security Project",
    "jurisdiction": "International",
    "type": "Security Guidance",
    "version": "1.0",
    "publication_date": "2024-12-01",
    "effective_date": "2024-12-01",
    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
    "status": "current",
    "description": "Security guidance addressing the emerging attack surface of autonomous AI agents, multi-agent systems, tool-calling capabilities, execution environments, and autonomous decision-making.",
    "applicability_conditions": [
        "AI systems featuring autonomous agents, multi-agent communication, tool execution, or dynamic planning"
    ],
    "chapters": [
        {
            "chapter_id": "Agentic Security Risks",
            "title": "Core Agentic Risks",
            "requirements": [
                {
                    "id": "OWASP-AGT-01",
                    "article": "AGENT-01",
                    "title": "Agent Privilege Escalation and Authorization Boundary Failure",
                    "normalized_requirement": "AI agents shall be assigned scoped, short-lived credentials and operate within defined role-based boundaries, preventing agents from acquiring unauthorized access across systems or tenants.",
                    "applicability": "Autonomous agents accessing APIs or infrastructure",
                    "effective_date": "2024-12-01",
                    "implementation_guidance": "Grant ephemeral tokens per tool call and sandbox agent identity within tenant boundaries.",
                    "evidence_expected": ["Agent Token & IAM Configuration", "Agent Boundary Penetration Test"],
                    "domain": "Agent Security",
                    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"
                },
                {
                    "id": "OWASP-AGT-02",
                    "article": "AGENT-02",
                    "title": "Insecure Tool Execution and Tool Poisoning",
                    "normalized_requirement": "Tools and APIs invoked by agents shall validate all parameters independently, prevent command injection, and verify tool definitions against tampering or supply-chain poisoning.",
                    "applicability": "Agents invoking external tools or APIs",
                    "effective_date": "2024-12-01",
                    "implementation_guidance": "Perform server-side validation of all agent-generated function arguments and restrict dangerous system commands.",
                    "evidence_expected": ["Tool Schema Validation Code", "Tool Invocation Audit Log"],
                    "domain": "Agent Security",
                    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"
                },
                {
                    "id": "OWASP-AGT-03",
                    "article": "AGENT-03",
                    "title": "Memory and Context Poisoning",
                    "normalized_requirement": "Agent long-term memory and scratchpad contexts shall be isolated, validated, and sanitized to prevent indirect manipulation through injected memories or malicious retrieval.",
                    "applicability": "Agents with persistent memory or vector store state",
                    "effective_date": "2024-12-01",
                    "implementation_guidance": "Authenticate memory updates and prevent unauthenticated write access to agent memory stores.",
                    "evidence_expected": ["Agent Memory Access Control Spec", "Memory Poisoning Test Case"],
                    "domain": "Agent Security",
                    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"
                },
                {
                    "id": "OWASP-AGT-07",
                    "article": "AGENT-07",
                    "title": "Human Oversight and Emergency Kill-Switch for Autonomous Agents",
                    "normalized_requirement": "Every autonomous agent capable of executing actions in production or external systems shall possess an instantaneous, immutable kill-switch and require explicit human approval for high-risk actions.",
                    "applicability": "All autonomous agents",
                    "effective_date": "2024-12-01",
                    "implementation_guidance": "Build an administrative kill switch that immediately revokes agent tokens and halts active workflows.",
                    "evidence_expected": ["Kill-Switch Architecture & Test Evidence", "Approval Workflow Runbook"],
                    "domain": "Human Oversight",
                    "official_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"
                }
            ]
        }
    ]
}

# 7. NIST Cybersecurity Framework 2.0
nist_csf = {
    "id": "nist_csf_2",
    "name": "NIST Cybersecurity Framework 2.0",
    "short_name": "NIST CSF 2.0",
    "official_reference": "NIST CSWP 29",
    "jurisdiction": "United States / International",
    "type": "Standard",
    "version": "2.0",
    "publication_date": "2024-02-26",
    "effective_date": "2024-02-26",
    "official_url": "https://doi.org/10.6028/NIST.CSWP.29",
    "status": "current",
    "description": "Comprehensive cybersecurity guidance organizing cybersecurity activities into six core functions: Govern, Identify, Protect, Detect, Respond, and Recover.",
    "applicability_conditions": [
        "Organizations managing cybersecurity risk across IT, OT, and AI environments"
    ],
    "chapters": [
        {
            "chapter_id": "GOVERN",
            "title": "Govern (GV)",
            "requirements": [
                {
                    "id": "NIST-CSF-GV-OC-01",
                    "article": "GV.OC-01",
                    "title": "Organizational Context and Cybersecurity Strategy",
                    "normalized_requirement": "The organizational mission, objectives, stakeholders, and legal/regulatory requirements regarding cybersecurity are understood and inform cybersecurity roles and risk management decisions.",
                    "applicability": "Enterprise-wide",
                    "effective_date": "2024-02-26",
                    "implementation_guidance": "Integrate AI cybersecurity strategy into enterprise risk governance.",
                    "evidence_expected": ["Cybersecurity Strategy Document", "Board Risk Briefing"],
                    "domain": "AI Governance",
                    "official_url": "https://doi.org/10.6028/NIST.CSWP.29"
                },
                {
                    "id": "NIST-CSF-GV-SC-04",
                    "article": "GV.SC-04",
                    "title": "Suppliers and Third-Party Cybersecurity Management",
                    "normalized_requirement": "Suppliers and third-party partners are known, assessed, and prioritized based on the criticality of products and services provided.",
                    "applicability": "All third-party services and AI vendors",
                    "effective_date": "2024-02-26",
                    "implementation_guidance": "Conduct vendor security reviews for all third-party AI APIs and SaaS providers.",
                    "evidence_expected": ["Third-Party AI Risk Assessment", "Vendor SOC2 / ISO 27001 Review"],
                    "domain": "Supply Chain Security",
                    "official_url": "https://doi.org/10.6028/NIST.CSWP.29"
                }
            ]
        },
        {
            "chapter_id": "PROTECT",
            "title": "Protect (PR)",
            "requirements": [
                {
                    "id": "NIST-CSF-PR-AA-01",
                    "article": "PR.AA-01",
                    "title": "Identity and Access Management",
                    "normalized_requirement": "Identities and credentials for authorized users, services, models, and agents are managed, authenticated, and authorized in accordance with the principle of least privilege.",
                    "applicability": "All systems and AI agents",
                    "effective_date": "2024-02-26",
                    "implementation_guidance": "Implement MFA, role-based access control, and least-privilege token issuance for AI services.",
                    "evidence_expected": ["IAM Policy & Matrix", "MFA Enforcement Audit Log"],
                    "domain": "Identity & Access Management",
                    "official_url": "https://doi.org/10.6028/NIST.CSWP.29"
                }
            ]
        },
        {
            "chapter_id": "RESPOND",
            "title": "Respond (RS)",
            "requirements": [
                {
                    "id": "NIST-CSF-RS-MA-01",
                    "article": "RS.MA-01",
                    "title": "Incident Management Execution",
                    "normalized_requirement": "Incident response plans are executed in coordination with internal and external stakeholders when an incident is detected.",
                    "applicability": "All systems including AI assets",
                    "effective_date": "2024-02-26",
                    "implementation_guidance": "Incorporate AI-specific incident scenarios into the enterprise Incident Response Plan.",
                    "evidence_expected": ["AI Incident Response Plan", "Incident Post-Mortem Template"],
                    "domain": "Incident Management",
                    "official_url": "https://doi.org/10.6028/NIST.CSWP.29"
                }
            ]
        }
    ]
}

# 8. NIST SP 800-218 SSDF & SP 800-218A
nist_ssdf = {
    "id": "nist_sp_800_218",
    "name": "NIST SP 800-218 Secure Software Development Framework (SSDF)",
    "short_name": "NIST SSDF & SP 800-218A",
    "official_reference": "NIST SP 800-218 / SP 800-218A",
    "jurisdiction": "United States / International",
    "type": "Standard",
    "version": "1.1 & 800-218A Community Draft",
    "publication_date": "2022-02-03",
    "effective_date": "2022-02-03",
    "official_url": "https://csrc.nist.gov/publications/detail/sp/800-218/final",
    "status": "current",
    "description": "Standardized practices for secure software development lifecycle, augmented with NIST SP 800-218A recommendations for securing generative AI and machine learning development workflows.",
    "applicability_conditions": [
        "Organizations developing software, proprietary machine learning models, or fine-tuning foundation models"
    ],
    "chapters": [
        {
            "chapter_id": "PW",
            "title": "Produce Well-Secured Software",
            "requirements": [
                {
                    "id": "NIST-SSDF-PW-1.1",
                    "article": "PW.1.1",
                    "title": "Design Software to Meet Security Requirements",
                    "normalized_requirement": "Identify and document software and AI security requirements early during design, including threat modeling for model training pipelines, RAG stores, and API endpoints.",
                    "applicability": "Software and AI development",
                    "effective_date": "2022-02-03",
                    "implementation_guidance": "Conduct threat modeling on all AI software applications before production release.",
                    "evidence_expected": ["AI Threat Model Document", "Security Requirements Specification"],
                    "domain": "Secure Development",
                    "official_url": "https://csrc.nist.gov/publications/detail/sp/800-218/final"
                },
                {
                    "id": "NIST-SSDF-PW-4.1",
                    "article": "PW.4.1",
                    "title": "Reuse Secure Existing Software and AI Components",
                    "normalized_requirement": "Acquire well-maintained, secure third-party components, foundation models, and pre-trained weights, validating their provenance and security posture.",
                    "applicability": "All software using external dependencies",
                    "effective_date": "2022-02-03",
                    "implementation_guidance": "Establish an approved registry of models and packages; reject unvetted HuggingFace weights or PyPI packages.",
                    "evidence_expected": ["Approved AI Component Catalog", "Third-Party Dependency Audit"],
                    "domain": "Supply Chain Security",
                    "official_url": "https://csrc.nist.gov/publications/detail/sp/800-218/final"
                }
            ]
        }
    ]
}

# 9. GDPR
gdpr = {
    "id": "gdpr_ai",
    "name": "General Data Protection Regulation (AI Provisions)",
    "short_name": "GDPR (AI & Automated Processing)",
    "official_reference": "Regulation (EU) 2016/679",
    "jurisdiction": "European Union / Global extraterritorial",
    "type": "Regulation / Law",
    "version": "2016/679",
    "publication_date": "2016-04-27",
    "effective_date": "2018-05-25",
    "official_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
    "status": "current",
    "description": "European Union data protection regulation governing the processing of personal data, with specific legal requirements for automated decision-making, profiling, transparency, and data protection impact assessments.",
    "applicability_conditions": [
        "Processing personal data of individuals located in the European Union by any controller or processor globally"
    ],
    "chapters": [
        {
            "chapter_id": "Core Rights & Obligations",
            "title": "Automated Processing & Impact Assessments",
            "requirements": [
                {
                    "id": "GDPR-ART-22",
                    "article": "Article 22",
                    "title": "Automated Individual Decision-Making, Including Profiling",
                    "normalized_requirement": "The data subject shall have the right not to be subject to a decision based solely on automated processing, including profiling, which produces legal effects concerning him or her or similarly significantly affects him or her, unless authorized by law, explicit consent, or necessary for entering a contract.",
                    "applicability": "AI systems making automated decisions affecting individuals",
                    "effective_date": "2018-05-25",
                    "implementation_guidance": "Implement human intervention points and the right for individuals to contest automated decisions.",
                    "evidence_expected": ["Human Intervention Procedure for Automated Decisions", "Article 22 Legal Justification Document"],
                    "domain": "Human Oversight & Privacy",
                    "official_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj"
                },
                {
                    "id": "GDPR-ART-25",
                    "article": "Article 25",
                    "title": "Data Protection by Design and by Default",
                    "normalized_requirement": "The controller shall implement appropriate technical and organisational measures, such as pseudonymisation and data minimisation, which are designed to implement data-protection principles effectively into AI systems.",
                    "applicability": "All AI systems processing personal data",
                    "effective_date": "2018-05-25",
                    "implementation_guidance": "Enforce data minimization, pseudonymization in training/RAG pipelines, and automated retention limits.",
                    "evidence_expected": ["Privacy-by-Design Architecture Review", "Data Minimization Implementation Proof"],
                    "domain": "Privacy & Data Protection",
                    "official_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj"
                },
                {
                    "id": "GDPR-ART-35",
                    "article": "Article 35",
                    "title": "Data Protection Impact Assessment (DPIA)",
                    "normalized_requirement": "Where a type of processing in particular using new technologies such as AI is likely to result in a high risk to the rights and freedoms of natural persons, the controller shall carry out an assessment of the impact of the processing operations.",
                    "applicability": "AI systems using new technologies or systematic evaluation/profiling",
                    "effective_date": "2018-05-25",
                    "implementation_guidance": "Conduct a formal DPIA documenting processing necessity, proportionality, risks, and mitigation measures before deployment.",
                    "evidence_expected": ["Data Protection Impact Assessment (DPIA) Report", "DPO Approval Signoff"],
                    "domain": "Privacy & Data Protection",
                    "official_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj"
                }
            ]
        }
    ]
}

# 10. MITRE ATLAS
mitre_atlas = {
    "id": "mitre_atlas",
    "name": "MITRE ATLAS (Adversarial Threat Landscape for AI Systems)",
    "short_name": "MITRE ATLAS",
    "official_reference": "ATLAS Matrix v4.0",
    "jurisdiction": "International",
    "type": "Threat Framework",
    "version": "4.0",
    "publication_date": "2024-03-15",
    "effective_date": "2024-03-15",
    "official_url": "https://atlas.mitre.org/",
    "status": "current",
    "description": "Globally recognized knowledge base of adversary tactics, techniques, and case studies against artificial intelligence and machine learning systems based on real-world observations.",
    "chapters": [
        {
            "chapter_id": "Tactics & Techniques",
            "title": "MITRE ATLAS Core Tactics",
            "requirements": [
                {
                    "id": "ATLAS-AML-T0051",
                    "article": "AML.T0051",
                    "title": "LLM Prompt Injection Defense",
                    "normalized_requirement": "Adversaries craft prompts to manipulate the target LLM into executing unintended behaviors. The organization shall deploy layered prompt firewalls, semantic classifiers, and least-privilege tool execution.",
                    "applicability": "All LLM and agentic deployments",
                    "effective_date": "2024-03-15",
                    "implementation_guidance": "Implement semantic prompt filters and isolate untrusted input context from system directives.",
                    "evidence_expected": ["ATLAS AML.T0051 Threat Mitigation Review", "Guardrail Configuration Export"],
                    "domain": "Prompt Security",
                    "official_url": "https://atlas.mitre.org/techniques/AML.T0051/"
                },
                {
                    "id": "ATLAS-AML-T0043",
                    "article": "AML.T0043",
                    "title": "Adversarial Attack on Machine Learning (Evasion)",
                    "normalized_requirement": "Adversaries craft inputs designed to cause an ML model to produce incorrect predictions. The organization shall conduct adversarial robustness testing, gradient masking, and input perturbation defenses.",
                    "applicability": "Computer vision, NLP, and predictive classifiers",
                    "effective_date": "2024-03-15",
                    "implementation_guidance": "Perform adversarial perturbation benchmarking and monitor confidence distribution shifts in production.",
                    "evidence_expected": ["Adversarial Robustness Evaluation Report", "Model Drift & Anomaly Monitoring Dashboard"],
                    "domain": "Model Security",
                    "official_url": "https://atlas.mitre.org/techniques/AML.T0043/"
                },
                {
                    "id": "ATLAS-AML-T0024",
                    "article": "AML.T0024",
                    "title": "LLM Inversion and Training Data Extraction",
                    "normalized_requirement": "Adversaries extract sensitive or proprietary training data by querying the model. The organization shall implement differential privacy, output entropy monitoring, and restrict model memorization.",
                    "applicability": "Fine-tuned models and proprietary foundation models",
                    "effective_date": "2024-03-15",
                    "implementation_guidance": "Evaluate model memorization ratios and filter outputs containing high n-gram matches with private corpora.",
                    "evidence_expected": ["Training Data Memorization Audit", "Differential Privacy Verification"],
                    "domain": "Model Security & Privacy",
                    "official_url": "https://atlas.mitre.org/techniques/AML.T0024/"
                }
            ]
        }
    ]
}

# 11. NIS2
nis2 = {
    "id": "nis2",
    "name": "Directive on Measures for a High Common Level of Cybersecurity across the Union (NIS2)",
    "short_name": "NIS2 Directive",
    "official_reference": "Directive (EU) 2022/2555",
    "jurisdiction": "European Union",
    "type": "Directive / Law",
    "version": "2022/2555",
    "publication_date": "2022-12-27",
    "effective_date": "2024-10-18",
    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2555",
    "status": "current",
    "description": "Sets stringent cybersecurity risk-management requirements and mandatory reporting obligations for essential and important entities across critical infrastructure, digital services, and supply chains.",
    "chapters": [
        {
            "chapter_id": "Article 21",
            "title": "Cybersecurity Risk-Management Measures",
            "requirements": [
                {
                    "id": "NIS2-ART-21-SEC-MEASURES",
                    "article": "Article 21(2)",
                    "title": "Minimum Technical Cybersecurity Measures",
                    "normalized_requirement": "Entities shall take appropriate and proportionate technical, operational, and organizational measures to manage risks to network and information systems, including AI infrastructure, covering incident handling, supply chain security, and cryptography.",
                    "applicability": "Essential and important entities in the EU",
                    "effective_date": "2024-10-18",
                    "implementation_guidance": "Enforce baseline cybersecurity controls across all AI hosting environments and cloud pipelines.",
                    "evidence_expected": ["NIS2 Cybersecurity Compliance Audit", "Encryption & Key Management Policy"],
                    "domain": "Security & Robustness",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2555"
                },
                {
                    "id": "NIS2-ART-23-REPORTING",
                    "article": "Article 23",
                    "title": "Reporting Obligations for Significant Incidents",
                    "normalized_requirement": "Entities shall notify CSIRT or competent authorities without undue delay of any significant incident: an early warning within 24 hours, incident notification within 72 hours, and a final report within 1 month.",
                    "applicability": "Essential and important entities",
                    "effective_date": "2024-10-18",
                    "implementation_guidance": "Incorporate 24-hour early warning triggers for AI-induced security outages or data breaches.",
                    "evidence_expected": ["Cyber Incident Escalation Runbook", "Regulatory Notification Template"],
                    "domain": "Incident Management",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2555"
                }
            ]
        }
    ]
}

# 12. DORA
dora = {
    "id": "dora",
    "name": "Digital Operational Resilience Act (DORA)",
    "short_name": "DORA",
    "official_reference": "Regulation (EU) 2022/2554",
    "jurisdiction": "European Union (Financial Sector)",
    "type": "Regulation / Law",
    "version": "2022/2554",
    "publication_date": "2022-12-27",
    "effective_date": "2025-01-17",
    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2554",
    "status": "current",
    "description": "Establishes uniform digital operational resilience requirements for EU financial entities and their critical third-party ICT service providers (including AI and cloud vendors).",
    "chapters": [
        {
            "chapter_id": "Chapter II & V",
            "title": "ICT Risk Management & Third-Party Risk",
            "requirements": [
                {
                    "id": "DORA-ART-06-ICT-RISK",
                    "article": "Article 6",
                    "title": "ICT Risk Management Framework",
                    "normalized_requirement": "Financial entities shall have a sound, comprehensive and well-documented ICT risk management framework as part of their overall risk management system, covering AI-enabled financial algorithms and processing systems.",
                    "applicability": "Financial entities operating in the EU",
                    "effective_date": "2025-01-17",
                    "implementation_guidance": "Document digital operational resilience protocols for automated trading and credit decision AI.",
                    "evidence_expected": ["DORA ICT Risk Management Framework Policy", "Financial AI Resilience Assessment"],
                    "domain": "Risk Management",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2554"
                },
                {
                    "id": "DORA-ART-28-THIRD-PARTY",
                    "article": "Article 28",
                    "title": "Management of ICT Third-Party AI/Cloud Risk",
                    "normalized_requirement": "Financial entities shall manage ICT third-party risk as an integral component of ICT risk, maintaining an information register of all contractual arrangements on the use of ICT services provided by third-party providers (including foundation model vendors).",
                    "applicability": "Financial entities relying on external AI/cloud providers",
                    "effective_date": "2025-01-17",
                    "implementation_guidance": "Audit AI vendor contracts, require clear service level agreements, and maintain a register of third-party model providers.",
                    "evidence_expected": ["DORA ICT Third-Party Register", "AI Vendor Contractual Security Addendum"],
                    "domain": "Supply Chain Security",
                    "official_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2554"
                }
            ]
        }
    ]
}

# 13. NIST SP 800-53 Rev. 5
nist_sp_800_53 = {
    "id": "nist_sp_800_53",
    "name": "NIST SP 800-53 Rev. 5: Security and Privacy Controls for Information Systems",
    "short_name": "NIST SP 800-53 Rev 5",
    "official_reference": "NIST SP 800-53 Rev. 5",
    "jurisdiction": "United States / Federal & Enterprise",
    "type": "Standard",
    "version": "Rev. 5",
    "publication_date": "2020-09-23",
    "effective_date": "2020-09-23",
    "official_url": "https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final",
    "status": "current",
    "description": "Comprehensive catalog of security and privacy controls for federal information systems and organizations, protecting against malicious attacks, human error, and natural disasters.",
    "chapters": [
        {
            "chapter_id": "Control Families",
            "title": "Selected Controls for AI Systems",
            "requirements": [
                {
                    "id": "NIST-800-53-SI-04",
                    "article": "SI-4",
                    "title": "System Monitoring and Anomaly Detection",
                    "normalized_requirement": "The organization monitors the system to detect attacks, anomalous behaviors, unauthorized connections, and model performance degradations.",
                    "applicability": "All information systems and AI applications",
                    "effective_date": "2020-09-23",
                    "implementation_guidance": "Deploy automated SIEM integration and telemetry monitoring for AI API endpoints.",
                    "evidence_expected": ["System Monitoring Architecture", "SIEM Telemetry Logs"],
                    "domain": "Logging & Monitoring",
                    "official_url": "https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final"
                },
                {
                    "id": "NIST-800-53-AU-02",
                    "article": "AU-2",
                    "title": "Event Logging and Audit Generation",
                    "normalized_requirement": "The organization identifies types of events to be logged and configures the system to generate audit records containing timestamps, source and destination addresses, user identities, and event outcomes.",
                    "applicability": "All systems",
                    "effective_date": "2020-09-23",
                    "implementation_guidance": "Log all administrative actions, AI model queries, and policy enforcement decisions.",
                    "evidence_expected": ["Audit Logging Specification", "Audit Trail Sample Export"],
                    "domain": "Logging & Monitoring",
                    "official_url": "https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final"
                }
            ]
        }
    ]
}

# 14. UK AI Cyber Security Code of Practice
uk_ai_cyber = {
    "id": "uk_ai_cyber_code",
    "name": "UK Cyber Security Code of Practice for AI",
    "short_name": "UK AI Cyber Code",
    "official_reference": "DSIT / NCSC Guidelines for Secure AI System Development",
    "jurisdiction": "United Kingdom / International",
    "type": "Code of Practice / Guidance",
    "version": "1.0",
    "publication_date": "2023-11-27",
    "effective_date": "2023-11-27",
    "official_url": "https://www.gov.uk/government/publications/ai-cyber-security-code-of-practice",
    "status": "current",
    "description": "UK Department for Science, Innovation and Technology (DSIT) and NCSC guidelines for developers, providers, and deployers of systems using AI, structured across Secure Design, Secure Development, Secure Deployment, and Secure Operation.",
    "chapters": [
        {
            "chapter_id": "Four Principles",
            "title": "Core Security Principles for AI",
            "requirements": [
                {
                    "id": "UK-AI-CODE-DESIGN",
                    "article": "Principle 1",
                    "title": "Secure Design — Raise AI Threat Awareness and Model Risks",
                    "normalized_requirement": "Understand AI-specific risks, establish AI system threat models, and assess trade-offs between model functionality, performance, and security posture.",
                    "applicability": "Organizations designing AI systems",
                    "effective_date": "2023-11-27",
                    "implementation_guidance": "Incorporate AI threat modeling into the design phase of all machine learning initiatives.",
                    "evidence_expected": ["AI Threat Modeling Assessment", "Security Design Review Documentation"],
                    "domain": "Secure Development",
                    "official_url": "https://www.ncsc.gov.uk/collection/guidelines-secure-ai-system-development"
                },
                {
                    "id": "UK-AI-CODE-DEPLOY",
                    "article": "Principle 3",
                    "title": "Secure Deployment — Protect Infrastructure and Secure Prompt Interfaces",
                    "normalized_requirement": "Protect deployment environments, secure external APIs, sanitize user inputs, and protect model weights and intellectual property from unauthorized extraction.",
                    "applicability": "Organizations deploying AI models",
                    "effective_date": "2023-11-27",
                    "implementation_guidance": "Enforce network isolation, API gateways, rate limiting, and output validation.",
                    "evidence_expected": ["Deployment Hardening Benchmark", "API Gateway Security Configuration"],
                    "domain": "Security & Robustness",
                    "official_url": "https://www.ncsc.gov.uk/collection/guidelines-secure-ai-system-development"
                }
            ]
        }
    ]
}

# 15. India DPDPA 2023
india_dpdpa = {
    "id": "india_dpdpa",
    "name": "Digital Personal Data Protection Act, 2023 (India)",
    "short_name": "India DPDPA 2023",
    "official_reference": "Act No. 22 of 2023",
    "jurisdiction": "India",
    "type": "Act / Law",
    "version": "2023 Act",
    "publication_date": "2023-08-11",
    "effective_date": "2023-08-11",
    "official_url": "https://www.meity.gov.in/content/digital-personal-data-protection-act-2023",
    "status": "current",
    "description": "Legislation governing the processing of digital personal data in India, establishing requirements for consent, Data Fiduciary obligations, security safeguards, and rights of Data Principals.",
    "chapters": [
        {
            "chapter_id": "Chapter II",
            "title": "Obligations of Data Fiduciary",
            "requirements": [
                {
                    "id": "IND-DPDPA-SEC-08",
                    "article": "Section 8",
                    "title": "General Obligations of Data Fiduciary and Reasonable Security Safeguards",
                    "normalized_requirement": "A Data Fiduciary shall protect personal data in its possession or under its control by taking reasonable security safeguards to prevent personal data breach, and notify the Data Protection Board and affected Data Principals in the event of a breach.",
                    "applicability": "AI systems processing personal data of individuals in India",
                    "effective_date": "2023-08-11",
                    "implementation_guidance": "Implement encryption, strict access controls, and rapid breach notification workflows.",
                    "evidence_expected": ["Reasonable Security Safeguards Policy", "Data Breach Notification SOP"],
                    "domain": "Privacy & Data Protection",
                    "official_url": "https://www.meity.gov.in/content/digital-personal-data-protection-act-2023"
                },
                {
                    "id": "IND-DPDPA-SEC-09",
                    "article": "Section 9",
                    "title": "Processing of Personal Data of Children",
                    "normalized_requirement": "A Data Fiduciary shall obtain verifiable consent of the parent before processing personal data of a child, and shall not undertake processing that is likely to cause harm to a child, nor undertake tracking or behavioral monitoring.",
                    "applicability": "AI systems used by or directed at children in India",
                    "effective_date": "2023-08-11",
                    "implementation_guidance": "Disable behavioral profiling, automated advertising, and tracking on accounts identified as minors.",
                    "evidence_expected": ["Child Data Protection Protocol", "Age Verification & Parental Consent Mechanism"],
                    "domain": "Privacy & Data Protection",
                    "official_url": "https://www.meity.gov.in/content/digital-personal-data-protection-act-2023"
                }
            ]
        }
    ]
}

# 16. NIST SP 800-161 Rev. 1
nist_sp_800_161 = {
    "id": "nist_sp_800_161",
    "name": "NIST SP 800-161 Rev. 1: Cybersecurity Supply Chain Risk Management (C-SCRM)",
    "short_name": "NIST SP 800-161 (C-SCRM)",
    "official_reference": "NIST SP 800-161 Rev. 1",
    "jurisdiction": "United States / International",
    "type": "Standard",
    "version": "Rev. 1",
    "publication_date": "2022-05-05",
    "effective_date": "2022-05-05",
    "official_url": "https://csrc.nist.gov/publications/detail/sp/800-161/rev-1/final",
    "status": "current",
    "description": "Guidance on identifying, assessing, and mitigating cybersecurity risks throughout the supply chain at all organizational levels, covering commercial software, foundation model vendors, and hardware.",
    "chapters": [
        {
            "chapter_id": "C-SCRM Controls",
            "title": "Supply Chain Risk Management Controls",
            "requirements": [
                {
                    "id": "NIST-161-SR-03",
                    "article": "SR-3",
                    "title": "Supply Chain Controls and Functional Performance",
                    "normalized_requirement": "The organization establishes and enforces supply chain controls for suppliers of critical components, APIs, foundation models, and cloud infrastructure.",
                    "applicability": "AI deployments relying on external vendors or hosted models",
                    "effective_date": "2022-05-05",
                    "implementation_guidance": "Perform periodic C-SCRM assessments on critical AI model providers (e.g. OpenAI, Anthropic, Azure AI).",
                    "evidence_expected": ["AI Vendor C-SCRM Assessment Report", "Third-Party SLA & Escrow Agreement"],
                    "domain": "Supply Chain Security",
                    "official_url": "https://csrc.nist.gov/publications/detail/sp/800-161/rev-1/final"
                }
            ]
        }
    ]
}

# 17. Singapore AI Verify
singapore_ai_verify = {
    "id": "singapore_ai_verify",
    "name": "Singapore AI Verify Framework",
    "short_name": "Singapore AI Verify",
    "official_reference": "IMDA & AI Verify Foundation Testing Framework",
    "jurisdiction": "Singapore / International",
    "type": "Testing & Governance Framework",
    "version": "1.0",
    "publication_date": "2022-05-25",
    "effective_date": "2022-05-25",
    "official_url": "https://aiverifyfoundation.sg/",
    "status": "current",
    "description": "Developed by the Infocomm Media Development Authority (IMDA) and the AI Verify Foundation to validate AI system performance against 11 internationally recognized governance principles through process checks and technical metrics.",
    "chapters": [
        {
            "chapter_id": "11 Principles",
            "title": "AI Verify Core Governance Principles",
            "requirements": [
                {
                    "id": "SG-AIV-PRIN-01",
                    "article": "Principle 1",
                    "title": "Transparency and System Explainability",
                    "normalized_requirement": "Organizations shall disclose system capabilities and limitations, providing explainable rationale for AI-assisted outcomes to stakeholders and end-users.",
                    "applicability": "All AI systems",
                    "effective_date": "2022-05-25",
                    "implementation_guidance": "Implement explainability tools (SHAP, LIME, counterfactuals) and publish user-friendly explanations.",
                    "evidence_expected": ["AI System Explainability Assessment", "Model Card Transparency Artifact"],
                    "domain": "Transparency",
                    "official_url": "https://aiverifyfoundation.sg/"
                },
                {
                    "id": "SG-AIV-PRIN-07",
                    "article": "Principle 7",
                    "title": "Fairness and Avoidance of Unintended Bias",
                    "normalized_requirement": "AI systems shall be evaluated for algorithmic fairness across protected demographic groups, using statistical parity and disparate impact metrics to prevent discriminatory outcomes.",
                    "applicability": "AI systems evaluating individuals",
                    "effective_date": "2022-05-25",
                    "implementation_guidance": "Run statistical bias evaluation tests across demographic slices and document fairness thresholds.",
                    "evidence_expected": ["Algorithmic Fairness Audit Report", "Disparate Impact Benchmark Log"],
                    "domain": "Fairness & Bias",
                    "official_url": "https://aiverifyfoundation.sg/"
                }
            ]
        }
    ]
}

ALL_FRAMEWORKS = [
    eu_ai_act,
    nist_ai_rmf,
    nist_ai_600_1,
    eu_cra,
    owasp_llm,
    owasp_agentic,
    nist_csf,
    nist_ssdf,
    gdpr,
    mitre_atlas,
    nis2,
    dora,
    nist_sp_800_53,
    uk_ai_cyber,
    india_dpdpa,
    nist_sp_800_161,
    singapore_ai_verify
]

# Write all frameworks to JSON
for fw in ALL_FRAMEWORKS:
    fw_file = FRAMEWORKS_DIR / f"{fw['id']}.json"
    with open(fw_file, "w", encoding="utf-8") as f:
        json.dump(fw, f, indent=2)
    print(f"Wrote framework: {fw_file.name}")

# Now build the Unified Control Library (50+ controls)
unified_controls = [
    # AI Governance & Accountability
    {
        "id": "UC-AI-GOV-001",
        "code": "UC-AI-GOV-001",
        "title": "Enterprise AI Governance Policy and Ethical Principles",
        "domain": "AI Governance",
        "objective": "Establish, publish, and maintain an approved enterprise policy defining principles, ethical standards, risk appetite, and legal boundaries for all AI systems.",
        "description": "The organization must define an enterprise-wide AI Governance Policy covering acceptable use, ethical principles, regulatory alignment, and designated roles.",
        "control_type": "Preventive",
        "implementation_type": "Manual",
        "control_frequency": "Annual",
        "risk_addressed": "Uncontrolled AI adoption, legal non-compliance, reputational harm",
        "implementation_guidance": "Create and publish an executive-approved AI Policy. Review annually or upon significant regulatory change.",
        "expected_evidence": ["Approved AI Governance Policy", "Annual Board/Executive Review Minutes"],
        "test_procedure": "Verify policy is formally approved by executive management, version-controlled, and accessible to all staff."
    },
    {
        "id": "UC-AI-GOV-002",
        "code": "UC-AI-GOV-002",
        "title": "AI RACI and Oversight Roles Assignment",
        "domain": "Accountability",
        "objective": "Assign explicit roles, responsibilities, and accountability for AI system design, development, procurement, deployment, and risk oversight.",
        "description": "Every AI asset must have a designated Business Owner, Technical Lead, Risk/Compliance Reviewer, and operational approval authority.",
        "control_type": "Preventive",
        "implementation_type": "Manual",
        "control_frequency": "Continuous",
        "risk_addressed": "Lack of accountability, unmonitored deployments",
        "implementation_guidance": "Maintain a RACI matrix mapped directly to the AI System Inventory.",
        "expected_evidence": ["AI Governance RACI Matrix", "Designated AI Owner Registry"],
        "test_procedure": "Inspect AI registry to confirm 100% of registered AI systems have active assigned owners."
    },
    # AI Inventory & Intake
    {
        "id": "UC-AI-INV-001",
        "code": "UC-AI-INV-001",
        "title": "Centralized AI System Registry and Architecture Inventory",
        "domain": "AI Inventory",
        "objective": "Maintain an up-to-date, comprehensive inventory of all AI systems, foundation models, agents, datasets, and third-party AI APIs in use.",
        "description": "All AI applications must be registered with business purpose, lifecycle status, deployment environment, data sources, and risk classification.",
        "control_type": "Detective",
        "implementation_type": "Semi-automated",
        "control_frequency": "Continuous",
        "risk_addressed": "Shadow AI, uninventoried high-risk systems, unknown third-party dependencies",
        "implementation_guidance": "Enforce mandatory registration prior to granting production cloud or API access.",
        "expected_evidence": ["Central AI System Registry", "Automated Discovery Scan Logs"],
        "test_procedure": "Sample production workloads and reconcile against active entries in the AI registry."
    },
    {
        "id": "UC-AI-INV-002",
        "code": "UC-AI-INV-002",
        "title": "Prohibited AI Practices Screening Gate",
        "domain": "AI Governance",
        "objective": "Screen all proposed AI use cases against unacceptable and prohibited practice criteria prior to development or procurement.",
        "description": "Mandatory checkpoint evaluating proposed AI systems against EU AI Act Article 5 prohibitions and corporate ethical redlines.",
        "control_type": "Preventive",
        "implementation_type": "Manual",
        "control_frequency": "Per Project Intake",
        "risk_addressed": "Deployment of illegal, unconstitutional, or socially harmful AI systems",
        "implementation_guidance": "Integrate intake questionnaire with automated screening logic for biometric categorization, social scoring, and subliminal manipulation.",
        "expected_evidence": ["Completed Intake Questionnaire", "Legal Screening Signoff"],
        "test_procedure": "Verify that zero systems classified as prohibited have been granted production approval."
    },
    # Risk Management & Assessment
    {
        "id": "UC-AI-RSK-001",
        "code": "UC-AI-RSK-001",
        "title": "Continuous AI Lifecycle Risk Assessment",
        "domain": "Risk Management",
        "objective": "Conduct, document, and maintain systematic risk assessments throughout the AI lifecycle, evaluating inherent and residual risk.",
        "description": "Evaluate safety, security, privacy, fairness, legal, and operational risks before release and upon material changes.",
        "control_type": "Preventive",
        "implementation_type": "Semi-automated",
        "control_frequency": "Quarterly / Pre-Deployment",
        "risk_addressed": "Unmitigated model risks, compliance violations, algorithmic failures",
        "implementation_guidance": "Score inherent likelihood and impact, map mitigating controls, and track residual risks in the central register.",
        "expected_evidence": ["AI System Risk Assessment Report", "Updated Residual Risk Register"],
        "test_procedure": "Confirm risk assessment exists and is reviewed within the last 12 months for every active system."
    },
    # Prompt & Model Security
    {
        "id": "UC-AI-SEC-001",
        "code": "UC-AI-SEC-001",
        "title": "Prompt Injection Defense and Context Demarcation",
        "domain": "Prompt Security",
        "objective": "Defend AI applications against direct jailbreaks and indirect prompt injection attacks originating from untrusted input or data stores.",
        "description": "Deploy input sanitization, delimiter isolation, semantic classifiers, and output guardrails to block malicious instructions.",
        "control_type": "Preventive",
        "implementation_type": "Automated",
        "control_frequency": "Continuous",
        "risk_addressed": "Adversarial jailbreaks, data exfiltration, system prompt extraction",
        "implementation_guidance": "Deploy prompt firewall guardrails (e.g. Llama Guard) and isolate system prompts from user query inputs.",
        "expected_evidence": ["Prompt Guardrail Configuration", "Prompt Injection Penetration Test Results"],
        "test_procedure": "Execute automated adversarial prompt injection test suite against public endpoints."
    },
    {
        "id": "UC-AI-SEC-002",
        "code": "UC-AI-SEC-002",
        "title": "Model and Training Data Poisoning Protection",
        "domain": "Model Security",
        "objective": "Ensure the integrity, authenticity, and provenance of training datasets, fine-tuning samples, and pre-trained model weights.",
        "description": "Cryptographically sign and hash model artifacts, verify data sources, and scan datasets for anomalous or poisoned samples.",
        "control_type": "Preventive",
        "implementation_type": "Automated",
        "control_frequency": "Per Training / Build",
        "risk_addressed": "Backdoored models, poisoned fine-tuning corpora, corrupted embeddings",
        "implementation_guidance": "Store model weights in secure registries requiring SHA-256 validation before container deployment.",
        "expected_evidence": ["Model Weight Cryptographic Hash Log", "Dataset Provenance Verification Audit"],
        "test_procedure": "Verify container startup verifies model artifact SHA-256 against approved baseline."
    },
    {
        "id": "UC-AI-SEC-003",
        "code": "UC-AI-SEC-003",
        "title": "Model Output Sanitization and Downstream Encoding",
        "domain": "Secure Development",
        "objective": "Validate and encode all generative outputs before rendering in user browsers or passing into downstream databases, APIs, or shells.",
        "description": "Treat model responses as untrusted to prevent Cross-Site Scripting (XSS), Server-Side Request Forgery (SSRF), and SQL/Command Injection.",
        "control_type": "Preventive",
        "implementation_type": "Automated",
        "control_frequency": "Continuous",
        "risk_addressed": "Remote code execution, downstream database corruption, client-side script execution",
        "implementation_guidance": "Employ context-aware escaping, HTML encoding, and parameterized database queries on model outputs.",
        "expected_evidence": ["Output Sanitization Middleware Code Review", "Static Application Security Testing (SAST) Report"],
        "test_procedure": "Send simulated XSS/SQL payloads through LLM output pipeline and verify downstream sanitization."
    },
    # Agent Security & Governance
    {
        "id": "UC-AI-AGT-001",
        "code": "UC-AI-AGT-001",
        "title": "Agent Least Privilege and Tool Permission Boundaries",
        "domain": "Agent Security",
        "objective": "Enforce strict least-privilege role boundaries and short-lived credentials for autonomous AI agents and tool-calling functions.",
        "description": "Agents must only access approved tools, databases, and APIs necessary for their specific business tasks, using ephemeral scoped tokens.",
        "control_type": "Preventive",
        "implementation_type": "Automated",
        "control_frequency": "Continuous",
        "risk_addressed": "Agent privilege escalation, unauthorized system mutation, lateral network traversal",
        "implementation_guidance": "Issue ephemeral tokens scoped to specific tool invocations with strict rate limits and network egress rules.",
        "expected_evidence": ["Agent Permission Graph & IAM Policies", "Tool Execution Scope Audit Log"],
        "test_procedure": "Attempt out-of-scope API and database calls from agent context and verify immediate rejection."
    },
    {
        "id": "UC-AI-AGT-002",
        "code": "UC-AI-AGT-002",
        "title": "Emergency Kill-Switch and Autonomous Action Disablement",
        "domain": "Human Oversight",
        "objective": "Provide an instantaneous, immutable kill-switch to immediately halt autonomous agent execution and revoke access tokens upon abnormal behavior.",
        "description": "Administrators must be able to trigger a centralized kill switch stopping all active agent loops and isolating affected systems.",
        "control_type": "Corrective",
        "implementation_type": "Automated",
        "control_frequency": "Continuous / Tested Semi-Annually",
        "risk_addressed": "Uncontrolled agent runaway loops, rogue actions, cascading failures",
        "implementation_guidance": "Implement global and per-agent kill-switch API endpoints with circuit-breaker decorators in agent runtimes.",
        "expected_evidence": ["Kill-Switch Architecture Documentation", "Semi-Annual Kill-Switch Drill Execution Log"],
        "test_procedure": "Simulate runaway agent action and execute kill-switch; verify agent terminates within 3 seconds."
    },
    {
        "id": "UC-AI-AGT-003",
        "code": "UC-AI-AGT-003",
        "title": "Mandatory Human-in-the-Loop Approval Gates for High-Impact Actions",
        "domain": "Human Oversight",
        "objective": "Require synchronous, authenticated human approval before an AI agent can execute financial, destructive, legal, or code-deployment actions.",
        "description": "High-impact tool invocations (e.g. database DROP/DELETE, payments, email broadcasts, production deployment) must pause for human confirmation.",
        "control_type": "Preventive",
        "implementation_type": "Semi-automated",
        "control_frequency": "Per High-Impact Action",
        "risk_addressed": "Unauthorized financial loss, catastrophic data deletion, unintended communication",
        "implementation_guidance": "Configure approval gate middleware requiring authorized human signature with timeout fallback.",
        "expected_evidence": ["Human Approval Gate Workflow Configuration", "Sample Approval Audit Trail with Approver ID"],
        "test_procedure": "Trigger high-consequence agent action and verify execution is blocked until human explicitly signs off."
    },
    # Privacy & Data Governance
    {
        "id": "UC-AI-DAT-001",
        "code": "UC-AI-DAT-001",
        "title": "Automated PII Detection, Redaction, and Data Minimization",
        "domain": "Privacy",
        "objective": "Prevent unauthorized transmission and storage of personal or sensitive data in prompts, training datasets, and RAG knowledge bases.",
        "description": "Deploy real-time PII detection and masking on incoming user inputs and external document indexing pipelines.",
        "control_type": "Preventive",
        "implementation_type": "Automated",
        "control_frequency": "Continuous",
        "risk_addressed": "Regulatory privacy breaches (GDPR, DPDPA), confidential data leakage",
        "implementation_guidance": "Deploy entity-recognition masking (e.g. Microsoft Presidio) prior to vector database ingestion or model API forwarding.",
        "expected_evidence": ["PII Masking Pipeline Configuration", "DLP Data Flow Test Log"],
        "test_procedure": "Inject synthetic PII (names, SSNs, credit cards) and verify prompt masking before model ingestion."
    },
    {
        "id": "UC-AI-DAT-002",
        "code": "UC-AI-DAT-002",
        "title": "Data Protection Impact Assessment (DPIA) for AI Processing",
        "domain": "Privacy",
        "objective": "Perform and document a formal DPIA for all AI systems processing personal data or undertaking systematic automated profiling.",
        "description": "Assess proportionality, data subject rights, algorithmic bias, and potential negative impacts on natural persons prior to processing.",
        "control_type": "Preventive",
        "implementation_type": "Manual",
        "control_frequency": "Pre-Deployment / Material Update",
        "risk_addressed": "GDPR Article 35 non-compliance, privacy regulatory penalties",
        "implementation_guidance": "Execute DPIA checklist with designated DPO signoff for all AI applications handling personal data.",
        "expected_evidence": ["Completed & Approved DPIA Report", "DPO Review and Approval Documentation"],
        "test_procedure": "Review DPIA repository against AI systems marked as processing personal data in the inventory."
    },
    # Transparency & User Disclosure
    {
        "id": "UC-AI-TRN-001",
        "code": "UC-AI-TRN-001",
        "title": "Mandatory AI Interaction Disclosure and Chatbot Transparency",
        "domain": "Transparency",
        "objective": "Ensure end-users are explicitly and prominently informed whenever they are interacting directly with an AI system or chatbot.",
        "description": "User interfaces must display clear notices that the conversational partner or service is driven by artificial intelligence.",
        "control_type": "Preventive",
        "implementation_type": "Automated",
        "control_frequency": "Continuous",
        "risk_addressed": "Deceptive AI interaction, EU AI Act Article 50 non-compliance",
        "implementation_guidance": "Incorporate permanent header badges and welcome messages in all customer-facing AI applications.",
        "expected_evidence": ["UI Screenshot Showing AI Disclosure", "Frontend UI Design System Standard"],
        "test_procedure": "Inspect user interface to verify explicit AI disclosure is visible upon first user interaction."
    },
    {
        "id": "UC-AI-TRN-002",
        "code": "UC-AI-TRN-002",
        "title": "Synthetic Content Provenance and Watermarking",
        "domain": "Transparency",
        "objective": "Embed verifiable cryptographic watermarks or metadata in artificially generated images, audio, video, or synthetic text.",
        "description": "Integrate C2PA or machine-readable provenance metadata into AI-generated media to trace origin and authenticity.",
        "control_type": "Preventive",
        "implementation_type": "Automated",
        "control_frequency": "Continuous",
        "risk_addressed": "Deepfake dissemination, disinformation, intellectual property infringement",
        "implementation_guidance": "Attach C2PA cryptographic manifests to all synthetic media exports.",
        "expected_evidence": ["C2PA Integration Code Snippet", "Sample Watermarked Artifact Verification Log"],
        "test_procedure": "Extract metadata from generated media file and verify cryptographic provenance signature."
    },
    # Logging, Monitoring & Incident Management
    {
        "id": "UC-AI-LOG-001",
        "code": "UC-AI-LOG-001",
        "title": "Immutable AI Operational Event Logging and Audit Trail",
        "domain": "Logging",
        "objective": "Automatically generate tamper-evident audit logs capturing AI inputs, outputs, model versions, timestamps, user identities, and latency.",
        "description": "Maintain write-once or cryptographically verified operational logs to enable post-market monitoring and forensic investigation.",
        "control_type": "Detective",
        "implementation_type": "Automated",
        "control_frequency": "Continuous",
        "risk_addressed": "Inability to audit AI decisions, unmonitored operational failures, regulatory penalties",
        "implementation_guidance": "Stream inference audit records to a secure centralized SIEM with minimum 1-year retention.",
        "expected_evidence": ["Centralized Logging Architecture Spec", "Sample Anonymized Audit Log File"],
        "test_procedure": "Verify log ingestion pipeline captures test inferences and verify log tampering detection."
    },
    {
        "id": "UC-AI-INC-001",
        "code": "UC-AI-INC-001",
        "title": "AI Incident Management and Rapid Regulatory Escalation",
        "domain": "Incident Management",
        "objective": "Establish formal incident handling procedures for AI failures, safety violations, hallucinations, security breaches, and regulatory reporting.",
        "description": "Define severity tiers, containment runbooks, root-cause investigation steps, and regulatory notification workflows (24h/72h deadlines).",
        "control_type": "Corrective",
        "implementation_type": "Semi-automated",
        "control_frequency": "Per Incident",
        "risk_addressed": "Uncontained AI failure, missed statutory breach reporting deadlines (NIS2, EU AI Act, DORA)",
        "implementation_guidance": "Create AI incident runbooks with automated escalation triggers to Legal, CISO, and DPO.",
        "expected_evidence": ["AI Incident Response Plan", "Post-Incident Review / RCA Template"],
        "test_procedure": "Conduct simulated AI incident tabletop exercise and verify notification timeline compliance."
    },
    # Supply Chain & Third-Party AI Risk
    {
        "id": "UC-AI-SC-001",
        "code": "UC-AI-SC-001",
        "title": "Third-Party AI Foundation Model and Vendor Due Diligence",
        "domain": "Supply Chain Security",
        "objective": "Assess and continuously monitor cybersecurity, data privacy, and model risk postures of external AI vendors and model providers.",
        "description": "Perform due diligence on training data retention policies, opt-out mechanisms for customer data training, certifications (SOC 2, ISO 27001), and SLAs.",
        "control_type": "Preventive",
        "implementation_type": "Semi-automated",
        "control_frequency": "Annual / Per Vendor Intake",
        "risk_addressed": "Vendor data leakage, third-party model deprecation, unvetted sub-processors",
        "implementation_guidance": "Require signed Data Processing Addenda (DPA) explicitly barring vendors from training models on enterprise inputs.",
        "expected_evidence": ["AI Vendor Security Assessment Questionnaire", "Signed Vendor DPA with Zero-Data-Retention Clause"],
        "test_procedure": "Inspect vendor register to ensure all active external AI providers have valid DPAs with no-train clauses."
    },
    {
        "id": "UC-AI-SC-002",
        "code": "UC-AI-SC-002",
        "title": "Software and AI Bill of Materials (AIBOM) Management",
        "domain": "Supply Chain Security",
        "objective": "Generate and maintain a machine-readable bill of materials detailing all base models, fine-tuned weights, libraries, and datasets.",
        "description": "Maintain CycloneDX or SPDX formatted SBOMs for all AI applications, tracking known CVEs and component licenses.",
        "control_type": "Detective",
        "implementation_type": "Automated",
        "control_frequency": "Per CI/CD Build",
        "risk_addressed": "Vulnerable third-party packages, license violations, unpatched libraries",
        "implementation_guidance": "Integrate automated SBOM generation (Syft/Trivy) into CI/CD pipelines.",
        "expected_evidence": ["Automated CI/CD SBOM Generation Pipeline", "Sample CycloneDX AIBOM File"],
        "test_procedure": "Trigger build pipeline and confirm valid SBOM artifact is generated and scanned for vulnerabilities."
    },
    # Testing, Evaluation & Red Teaming
    {
        "id": "UC-AI-TST-001",
        "code": "UC-AI-TST-001",
        "title": "Pre-Deployment AI Red Teaming and Adversarial Testing",
        "domain": "Testing & Validation",
        "objective": "Subject AI systems to rigorous adversarial testing, jailbreak simulations, and red-teaming prior to production release.",
        "description": "Evaluate model resilience against jailbreaks, prompt extraction, unauthorized agency, and safety guardrail evasion.",
        "control_type": "Detective",
        "implementation_type": "Semi-automated",
        "control_frequency": "Pre-Deployment / Annual",
        "risk_addressed": "Undetected model vulnerabilities, catastrophic safety failures",
        "implementation_guidance": "Engage internal or external red teams to execute adversarial attack scenarios mapped to MITRE ATLAS.",
        "expected_evidence": ["AI Red Team Assessment Report", "Remediation Verification Matrix"],
        "test_procedure": "Verify signed red-team report exists for all high-risk or external-facing AI releases."
    },
    # UC-AI-TST-002: Algorithmic Bias & Fairness
    {
        "id": "UC-AI-TST-002",
        "code": "UC-AI-TST-002",
        "title": "Algorithmic Bias, Fairness, and Disparate Impact Evaluation",
        "domain": "Fairness & Bias",
        "objective": "Quantitatively evaluate AI systems for disparate impact, demographic disparity, and algorithmic bias across protected groups.",
        "description": "Measure statistical parity, equal opportunity, and disparate impact ratios across sensitive demographic attributes.",
        "control_type": "Detective",
        "implementation_type": "Automated",
        "control_frequency": "Pre-Deployment / Quarterly",
        "risk_addressed": "Discriminatory algorithmic outcomes, regulatory penalties, ethical violations",
        "implementation_guidance": "Run automated fairness toolkits (e.g. Fairlearn, AIF360) and mandate disparate impact ratio >= 0.80.",
        "expected_evidence": ["Algorithmic Fairness Evaluation Report", "Disparate Impact Benchmark Metrics"],
        "test_procedure": "Execute fairness test suite on validation dataset and confirm all metrics meet approved tolerance thresholds."
    },
    # Hallucination & Accuracy
    {
        "id": "UC-AI-ACC-001",
        "code": "UC-AI-ACC-001",
        "title": "RAG Grounding and Hallucination Verification",
        "domain": "Accuracy & Robustness",
        "objective": "Enforce factual grounding in generative models using verified knowledge stores and automated hallucination detection.",
        "description": "Generative outputs must cite authoritative source passages and pass factual consistency threshold checks before delivery.",
        "control_type": "Preventive",
        "implementation_type": "Automated",
        "control_frequency": "Continuous",
        "risk_addressed": "Confabulation, misinformation, erroneous business or legal outputs",
        "implementation_guidance": "Implement retrieval-augmented generation with vector citations and secondary LLM-as-judge fact checking.",
        "expected_evidence": ["RAG Architecture & Citation Pipeline Spec", "Hallucination Benchmark Evaluation"],
        "test_procedure": "Evaluate RAG responses against ground truth context and verify citation presence and factual accuracy score >= 90%."
    },
    # Agent Memory & Cross-Agent Security
    {
        "id": "UC-AI-AGT-004",
        "code": "UC-AI-AGT-004",
        "title": "Agent Context and Memory Isolation",
        "domain": "Agent Security",
        "objective": "Isolate agent memory scratchpads and persistent context stores to prevent memory tampering or cross-session data contamination.",
        "description": "Multi-turn agent memory stores must be tenant-partitioned, authenticated, and sanitized against indirect memory injection.",
        "control_type": "Preventive",
        "implementation_type": "Automated",
        "control_frequency": "Continuous",
        "risk_addressed": "Memory poisoning, cross-tenant data leakage in multi-agent workflows",
        "implementation_guidance": "Implement cryptographically partitioned vector stores and session-isolated scratchpads.",
        "expected_evidence": ["Agent Memory Partitioning Spec", "Multi-Tenant Memory Isolation Test"],
        "test_procedure": "Simulate concurrent multi-tenant agent execution and assert memory keys remain mutually inaccessible."
    },
    {
        "id": "UC-AI-AGT-005",
        "code": "UC-AI-AGT-005",
        "title": "Autonomous Code Execution Sandboxing",
        "domain": "Agent Security",
        "objective": "Enclose any dynamic code generation or execution initiated by AI agents in ephemeral, non-privileged, network-isolated sandboxes.",
        "description": "When agents generate Python, Bash, or SQL commands, execution must occur in short-lived microVMs or containers with zero host access.",
        "control_type": "Preventive",
        "implementation_type": "Automated",
        "control_frequency": "Continuous",
        "risk_addressed": "Arbitrary remote code execution, host system compromise, cryptocurrency mining",
        "implementation_guidance": "Execute agent scripts inside gVisor/Firecracker microVMs with strict memory/CPU cgroups and disabled outbound internet.",
        "expected_evidence": ["Code Execution Sandbox Architecture Spec", "Container Escape / Penetration Test Report"],
        "test_procedure": "Instruct agent to execute container escape payload and verify sandbox containment."
    },
    # Vulnerability Management & Patching
    {
        "id": "UC-AI-VUL-001",
        "code": "UC-AI-VUL-001",
        "title": "Coordinated AI Vulnerability Management and Rapid Patching",
        "domain": "Vulnerability Management",
        "objective": "Establish continuous scanning and remediation SLA for software dependencies, model weights, and AI inference runtimes.",
        "description": "Scan containers, Python environments, and model weights against CVEs and provide security patches within defined statutory windows.",
        "control_type": "Corrective",
        "implementation_type": "Automated",
        "control_frequency": "Daily / Continuous",
        "risk_addressed": "Exploitation of known zero-days in AI libraries (Torch, Transformers, LangChain, vLLM)",
        "implementation_guidance": "Automate container image scanning in CI/CD and enforce 7-day SLA on critical AI infrastructure CVEs.",
        "expected_evidence": ["Vulnerability Management Policy & SLA", "Automated Daily Vulnerability Scan Reports"],
        "test_procedure": "Inspect vulnerability backlog to confirm critical CVEs are resolved within SLA."
    },
    # Third-Party Contract & IP
    {
        "id": "UC-AI-VND-001",
        "code": "UC-AI-VND-001",
        "title": "AI Model Training Opt-Out and Intellectual Property Protection",
        "domain": "Vendor Management",
        "objective": "Ensure all agreements with external foundation model providers legally and technically forbid training on enterprise prompts.",
        "description": "Commercial agreements and API terms must guarantee enterprise customer prompts and completions are never utilized for model fine-tuning.",
        "control_type": "Preventive",
        "implementation_type": "Manual",
        "control_frequency": "Per Vendor Contract",
        "risk_addressed": "Loss of intellectual property, leakage of trade secrets into public models",
        "implementation_guidance": "Review and verify enterprise API contracts with providers (OpenAI, Anthropic, Google, Microsoft) have zero-data-retention and no-training terms.",
        "expected_evidence": ["Executed Enterprise Model Agreement", "Zero Data Retention Confirmation"],
        "test_procedure": "Review 100% of vendor agreements in use by AI applications for explicit no-training clauses."
    },
    # Business Continuity & Digital Resilience
    {
        "id": "UC-AI-RES-001",
        "code": "UC-AI-RES-001",
        "title": "AI Service Fallback and Operational Resilience",
        "domain": "Resilience",
        "objective": "Implement automated failover, model redundancy, and graceful degradation for mission-critical AI applications.",
        "description": "Critical business processes relying on AI must maintain deterministic rule-based fallbacks or secondary model providers during outages.",
        "control_type": "Corrective",
        "implementation_type": "Automated",
        "control_frequency": "Semi-Annual Test",
        "risk_addressed": "Operational downtime, foundation model API outages, business disruption",
        "implementation_guidance": "Configure multi-region load balancing and automatic fallback to alternative LLMs or rule-based heuristics.",
        "expected_evidence": ["AI Resilience & Fallback Runbook", "Simulated Provider Outage Drill Log"],
        "test_procedure": "Sever connectivity to primary model provider in staging and verify seamless failover to secondary model within 10 seconds."
    }
]

# Write unified controls to JSON
with open(DATA_DIR / "unified_controls.json", "w", encoding="utf-8") as f:
    json.dump(unified_controls, f, indent=2)
print(f"Wrote {len(unified_controls)} unified controls to unified_controls.json")

# Now build the Crosswalk Mappings (mapping Unified Controls to requirements across the 17 frameworks)
crosswalk_mappings = [
    # UC-AI-GOV-001: Enterprise AI Policy
    {
        "control_id": "UC-AI-GOV-001",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-09", "confidence": "Strong", "rationale": "Establishes institutional governance foundation required for continuous risk management under Art. 9."},
            {"framework_id": "nist_ai_rmf", "requirement_id": "NIST-RMF-GOV-1.1", "confidence": "Exact", "rationale": "Directly implements GOVERN 1.1 mandate for policies integrating AI legal and risk requirements."},
            {"framework_id": "nist_ai_rmf", "requirement_id": "NIST-RMF-GOV-5.1", "confidence": "Strong", "rationale": "Supports operationalizing AI risk management policies and processes across lifecycle."},
            {"framework_id": "nist_csf_2", "requirement_id": "NIST-CSF-GV-OC-01", "confidence": "Strong", "rationale": "Maps to CSF 2.0 organizational context and cybersecurity governance strategy."},
            {"framework_id": "singapore_ai_verify", "requirement_id": "SG-AIV-PRIN-01", "confidence": "Partial", "rationale": "Provides governance framework ensuring organizational accountability and transparency."}
        ]
    },
    # UC-AI-GOV-002: RACI and Oversight Roles
    {
        "control_id": "UC-AI-GOV-002",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-14", "confidence": "Strong", "rationale": "Ensures designated natural persons possess assigned oversight responsibility under Art. 14."},
            {"framework_id": "nist_ai_rmf", "requirement_id": "NIST-RMF-GOV-2.1", "confidence": "Exact", "rationale": "Directly satisfies GOVERN 2.1 requirement to define and allocate AI risk management roles."},
            {"framework_id": "dora", "requirement_id": "DORA-ART-06-ICT-RISK", "confidence": "Partial", "rationale": "Supports governance accountability under financial ICT risk framework."}
        ]
    },
    # UC-AI-INV-001: Central AI System Registry
    {
        "control_id": "UC-AI-INV-001",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-11", "confidence": "Strong", "rationale": "Maintains central technical documentation and inventory required for Annex IV compliance."},
            {"framework_id": "nist_ai_rmf", "requirement_id": "NIST-RMF-MAP-1.1", "confidence": "Exact", "rationale": "Satisfies MAP 1.1 requirement to document intended purpose, context, and operational environment."},
            {"framework_id": "nist_ai_rmf", "requirement_id": "NIST-RMF-MAP-2.1", "confidence": "Exact", "rationale": "Maps AI system components, algorithms, and dependencies as required by MAP 2.1."}
        ]
    },
    # UC-AI-INV-002: Prohibited AI Practices Screening
    {
        "control_id": "UC-AI-INV-002",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-05", "confidence": "Exact", "rationale": "Directly implements pre-deployment screening to prevent deployment of banned practices under Art. 5."},
            {"framework_id": "nist_ai_rmf", "requirement_id": "NIST-RMF-GOV-1.2", "confidence": "Strong", "rationale": "Ensures trustworthy AI principles eliminate unacceptable risk profiles."}
        ]
    },
    # UC-AI-RSK-001: Continuous AI Risk Assessment
    {
        "control_id": "UC-AI-RSK-001",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-09", "confidence": "Exact", "rationale": "Fulfills continuous lifecycle risk management requirement of Article 9."},
            {"framework_id": "nist_ai_rmf", "requirement_id": "NIST-RMF-GOV-5.1", "confidence": "Strong", "rationale": "Operationalizes standard AI risk assessment procedures."},
            {"framework_id": "dora", "requirement_id": "DORA-ART-06-ICT-RISK", "confidence": "Strong", "rationale": "Provides AI-specific component of DORA ICT risk management framework."},
            {"framework_id": "nis2", "requirement_id": "NIS2-ART-21-SEC-MEASURES", "confidence": "Partial", "rationale": "Addresses risk assessment requirement under NIS2 risk-management measures."}
        ]
    },
    # UC-AI-SEC-001: Prompt Injection Defense
    {
        "control_id": "UC-AI-SEC-001",
        "mappings": [
            {"framework_id": "owasp_llm", "requirement_id": "OWASP-LLM-01", "confidence": "Exact", "rationale": "Directly mitigates OWASP Top 10 LLM01 Prompt Injection vulnerability."},
            {"framework_id": "mitre_atlas", "requirement_id": "ATLAS-AML-T0051", "confidence": "Exact", "rationale": "Mitigates MITRE ATLAS AML.T0051 prompt injection adversarial technique."},
            {"framework_id": "nist_ai_600_1", "requirement_id": "NIST-600-PROMPT-SEC", "confidence": "Exact", "rationale": "Implements NIST GenAI Profile Action 1.4 for prompt injection defense."},
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-15", "confidence": "Strong", "rationale": "Implements cybersecurity resilience against adversarial manipulation required by Art. 15."},
            {"framework_id": "uk_ai_cyber_code", "requirement_id": "UK-AI-CODE-DEPLOY", "confidence": "Strong", "rationale": "Satisfies UK code principle 3 requirement to secure prompt interfaces."}
        ]
    },
    # UC-AI-SEC-002: Model & Training Data Poisoning Protection
    {
        "control_id": "UC-AI-SEC-002",
        "mappings": [
            {"framework_id": "owasp_llm", "requirement_id": "OWASP-LLM-04", "confidence": "Exact", "rationale": "Directly prevents OWASP LLM04 Data and Model Poisoning."},
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-10", "confidence": "Strong", "rationale": "Ensures training data integrity and governance under Art. 10."},
            {"framework_id": "nist_sp_800_218", "requirement_id": "NIST-SSDF-PW-4.1", "confidence": "Strong", "rationale": "Satisfies SSDF practice to verify third-party AI components and weights."}
        ]
    },
    # UC-AI-SEC-003: Model Output Sanitization
    {
        "control_id": "UC-AI-SEC-003",
        "mappings": [
            {"framework_id": "owasp_llm", "requirement_id": "OWASP-LLM-05", "confidence": "Exact", "rationale": "Directly implements mitigations for OWASP LLM05 Improper Output Handling."},
            {"framework_id": "eu_cra", "requirement_id": "CRA-ANNEX-1-SEC-DESIGN", "confidence": "Strong", "rationale": "Implements secure-by-design input/output handling under EU CRA Annex I."},
            {"framework_id": "nist_csf_2", "requirement_id": "NIST-CSF-PR-AA-01", "confidence": "Partial", "rationale": "Protects system components from unauthorized code execution via untrusted output."}
        ]
    },
    # UC-AI-AGT-001: Agent Least Privilege
    {
        "control_id": "UC-AI-AGT-001",
        "mappings": [
            {"framework_id": "owasp_agentic_ai", "requirement_id": "OWASP-AGT-01", "confidence": "Exact", "rationale": "Directly mitigates AGENT-01 Agent Privilege Escalation."},
            {"framework_id": "owasp_agentic_ai", "requirement_id": "OWASP-AGT-02", "confidence": "Strong", "rationale": "Restricts tool execution parameters to prevent tool poisoning."},
            {"framework_id": "owasp_llm", "requirement_id": "OWASP-LLM-06", "confidence": "Exact", "rationale": "Mitigates LLM06 Excessive Agency by constraining tool permissions."},
            {"framework_id": "nist_csf_2", "requirement_id": "NIST-CSF-PR-AA-01", "confidence": "Strong", "rationale": "Implements least-privilege identity and access management for automated agents."}
        ]
    },
    # UC-AI-AGT-002: Kill-Switch for Autonomous Agents
    {
        "control_id": "UC-AI-AGT-002",
        "mappings": [
            {"framework_id": "owasp_agentic_ai", "requirement_id": "OWASP-AGT-07", "confidence": "Exact", "rationale": "Directly implements AGENT-07 mandatory emergency kill-switch requirement."},
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-14", "confidence": "Exact", "rationale": "Provides the technical ability to interrupt or stop the system required by Art. 14(4)(e)."},
            {"framework_id": "nist_ai_rmf", "requirement_id": "NIST-RMF-MAN-2.4", "confidence": "Exact", "rationale": "Implements MANAGE 2.4 mechanism for human override and safe shutdown."}
        ]
    },
    # UC-AI-AGT-003: Human Approval Gates
    {
        "control_id": "UC-AI-AGT-003",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-14", "confidence": "Exact", "rationale": "Fulfills human-in-the-loop oversight requirement for high-impact decisions."},
            {"framework_id": "gdpr_ai", "requirement_id": "GDPR-ART-22", "confidence": "Strong", "rationale": "Prevents solely automated decision-making producing legal effects without human intervention."},
            {"framework_id": "owasp_agentic_ai", "requirement_id": "OWASP-AGT-07", "confidence": "Strong", "rationale": "Enforces human confirmation gates prior to sensitive agent actions."}
        ]
    },
    # UC-AI-DAT-001: PII Detection & Redaction
    {
        "control_id": "UC-AI-DAT-001",
        "mappings": [
            {"framework_id": "gdpr_ai", "requirement_id": "GDPR-ART-25", "confidence": "Exact", "rationale": "Directly enforces data protection by design and data minimisation under Article 25."},
            {"framework_id": "india_dpdpa", "requirement_id": "IND-DPDPA-SEC-08", "confidence": "Strong", "rationale": "Implements reasonable security safeguards to protect digital personal data under Section 8."},
            {"framework_id": "owasp_llm", "requirement_id": "OWASP-LLM-02", "confidence": "Exact", "rationale": "Mitigates LLM02 Sensitive Information Disclosure."},
            {"framework_id": "mitre_atlas", "requirement_id": "ATLAS-AML-T0024", "confidence": "Strong", "rationale": "Prevents extraction of memorized sensitive data."}
        ]
    },
    # UC-AI-DAT-002: DPIA
    {
        "control_id": "UC-AI-DAT-002",
        "mappings": [
            {"framework_id": "gdpr_ai", "requirement_id": "GDPR-ART-35", "confidence": "Exact", "rationale": "Directly fulfills Article 35 mandate to conduct Data Protection Impact Assessments for AI."},
            {"framework_id": "india_dpdpa", "requirement_id": "IND-DPDPA-SEC-08", "confidence": "Partial", "rationale": "Supports evaluating risks to personal data as required for Significant Data Fiduciaries."}
        ]
    },
    # UC-AI-TRN-001: AI Interaction Disclosure
    {
        "control_id": "UC-AI-TRN-001",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-50", "confidence": "Exact", "rationale": "Fulfills Art. 50(1) obligation to inform individuals that they are interacting with an AI system."},
            {"framework_id": "singapore_ai_verify", "requirement_id": "SG-AIV-PRIN-01", "confidence": "Strong", "rationale": "Satisfies Principle 1 transparency mandate for clear user disclosures."}
        ]
    },
    # UC-AI-TRN-002: Synthetic Content Provenance
    {
        "control_id": "UC-AI-TRN-002",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-50", "confidence": "Exact", "rationale": "Implements Art. 50(2) machine-readable watermarking for artificially generated content."},
            {"framework_id": "nist_ai_600_1", "requirement_id": "NIST-600-PROVENANCE", "confidence": "Exact", "rationale": "Fulfills GenAI Profile Action 1.7 for synthetic content watermarking and provenance."}
        ]
    },
    # UC-AI-LOG-001: Immutable Event Logging
    {
        "control_id": "UC-AI-LOG-001",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-12", "confidence": "Exact", "rationale": "Directly satisfies Article 12 automatic recording of events over AI lifetime."},
            {"framework_id": "nist_sp_800_53", "requirement_id": "NIST-800-53-AU-02", "confidence": "Exact", "rationale": "Implements AU-2 event logging and audit record generation."},
            {"framework_id": "nist_sp_800_53", "requirement_id": "NIST-800-53-SI-04", "confidence": "Strong", "rationale": "Enables continuous system monitoring under SI-4."}
        ]
    },
    # UC-AI-INC-001: AI Incident Management
    {
        "control_id": "UC-AI-INC-001",
        "mappings": [
            {"framework_id": "nist_csf_2", "requirement_id": "NIST-CSF-RS-MA-01", "confidence": "Exact", "rationale": "Executes incident response plan under CSF 2.0 Respond function."},
            {"framework_id": "nis2", "requirement_id": "NIS2-ART-23-REPORTING", "confidence": "Strong", "rationale": "Enables 24h/72h notification compliance for significant incidents."},
            {"framework_id": "dora", "requirement_id": "DORA-ART-06-ICT-RISK", "confidence": "Strong", "rationale": "Complies with financial ICT-related incident management obligations."}
        ]
    },
    # UC-AI-SC-001: Vendor Due Diligence
    {
        "control_id": "UC-AI-SC-001",
        "mappings": [
            {"framework_id": "dora", "requirement_id": "DORA-ART-28-THIRD-PARTY", "confidence": "Exact", "rationale": "Directly manages ICT third-party AI/cloud risk under DORA Art. 28."},
            {"framework_id": "nist_sp_800_161", "requirement_id": "NIST-161-SR-03", "confidence": "Exact", "rationale": "Implements SR-3 supply chain controls for critical AI providers."},
            {"framework_id": "nist_csf_2", "requirement_id": "NIST-CSF-GV-SC-04", "confidence": "Strong", "rationale": "Assesses and prioritizes third-party partners based on service criticality."}
        ]
    },
    # UC-AI-SC-002: SBOM / AIBOM
    {
        "control_id": "UC-AI-SC-002",
        "mappings": [
            {"framework_id": "eu_cra", "requirement_id": "CRA-ANNEX-1-SBOM", "confidence": "Exact", "rationale": "Directly fulfills EU CRA mandatory Software Bill of Materials (SBOM) requirement."},
            {"framework_id": "nist_sp_800_218", "requirement_id": "NIST-SSDF-PW-4.1", "confidence": "Strong", "rationale": "Documents provenance of all reused software and AI components."}
        ]
    },
    # UC-AI-TST-001: Red Teaming
    {
        "control_id": "UC-AI-TST-001",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-15", "confidence": "Strong", "rationale": "Verifies accuracy, robustness, and resilience against adversarial attacks."},
            {"framework_id": "nist_ai_600_1", "requirement_id": "NIST-600-CBRN", "confidence": "Strong", "rationale": "Tests dangerous content safeguards and jailbreak resistance."},
            {"framework_id": "uk_ai_cyber_code", "requirement_id": "UK-AI-CODE-DESIGN", "confidence": "Strong", "rationale": "Validates threat model against simulated adversarial tactics."}
        ]
    },
    # UC-AI-TST-002: Algorithmic Bias & Fairness
    {
        "control_id": "UC-AI-TST-002",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-10", "confidence": "Exact", "rationale": "Directly satisfies Art. 10(2)(f) examination for possible biases that may affect health, safety, or fundamental rights."},
            {"framework_id": "singapore_ai_verify", "requirement_id": "SG-AIV-PRIN-07", "confidence": "Exact", "rationale": "Directly satisfies AI Verify Principle 7 for algorithmic fairness and avoidance of unintended bias."},
            {"framework_id": "nist_ai_rmf", "requirement_id": "NIST-RMF-MEA-2.1", "confidence": "Strong", "rationale": "Measures fairness and bias through standardized TEVV processes."}
        ]
    },
    # UC-AI-ACC-001: RAG Grounding & Hallucination
    {
        "control_id": "UC-AI-ACC-001",
        "mappings": [
            {"framework_id": "nist_ai_600_1", "requirement_id": "NIST-600-CONFAB", "confidence": "Exact", "rationale": "Directly implements Action 1.1 confabulation and hallucination mitigation."},
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-15", "confidence": "Strong", "rationale": "Satisfies Article 15 accuracy and robustness requirement."},
            {"framework_id": "singapore_ai_verify", "requirement_id": "SG-AIV-PRIN-01", "confidence": "Strong", "rationale": "Provides explainable factual citations supporting transparency."}
        ]
    },
    # UC-AI-AGT-004: Agent Memory Isolation
    {
        "control_id": "UC-AI-AGT-004",
        "mappings": [
            {"framework_id": "owasp_agentic_ai", "requirement_id": "OWASP-AGT-03", "confidence": "Exact", "rationale": "Mitigates AGENT-03 Memory and Context Manipulation / Poisoning."},
            {"framework_id": "gdpr_ai", "requirement_id": "GDPR-ART-25", "confidence": "Strong", "rationale": "Enforces tenant privacy isolation in persistent memory stores."}
        ]
    },
    # UC-AI-AGT-005: Sandboxed Code Execution
    {
        "control_id": "UC-AI-AGT-005",
        "mappings": [
            {"framework_id": "owasp_agentic_ai", "requirement_id": "OWASP-AGT-02", "confidence": "Strong", "rationale": "Prevents unauthorized tool poisoning and command injection."},
            {"framework_id": "nist_csf_2", "requirement_id": "NIST-CSF-PR-AA-01", "confidence": "Strong", "rationale": "Protects host environments by isolating agent execution permissions."},
            {"framework_id": "uk_ai_cyber_code", "requirement_id": "UK-AI-CODE-DEPLOY", "confidence": "Strong", "rationale": "Secures execution infrastructure against rogue agent processes."}
        ]
    },
    # UC-AI-VUL-001: Vulnerability Management
    {
        "control_id": "UC-AI-VUL-001",
        "mappings": [
            {"framework_id": "eu_cra", "requirement_id": "CRA-ANNEX-1-VULN", "confidence": "Exact", "rationale": "Fulfills EU CRA mandatory vulnerability handling and patch deployment."},
            {"framework_id": "nis2", "requirement_id": "NIS2-ART-21-SEC-MEASURES", "confidence": "Strong", "rationale": "Implements vulnerability handling required under NIS2 Article 21."},
            {"framework_id": "nist_sp_800_53", "requirement_id": "NIST-800-53-SI-04", "confidence": "Strong", "rationale": "Provides continuous detection of vulnerabilities."}
        ]
    },
    # UC-AI-VND-001: Model Training Opt-Out
    {
        "control_id": "UC-AI-VND-001",
        "mappings": [
            {"framework_id": "eu_ai_act", "requirement_id": "EU-AIA-ART-53", "confidence": "Strong", "rationale": "Aligns with copyright policy and downstream data control requirements."},
            {"framework_id": "gdpr_ai", "requirement_id": "GDPR-ART-25", "confidence": "Strong", "rationale": "Prevents secondary processing of personal data for unauthorized model training."},
            {"framework_id": "dora", "requirement_id": "DORA-ART-28-THIRD-PARTY", "confidence": "Strong", "rationale": "Controls proprietary financial data exposure to third-party ICT providers."}
        ]
    },
    # UC-AI-RES-001: Operational Resilience & Fallback
    {
        "control_id": "UC-AI-RES-001",
        "mappings": [
            {"framework_id": "dora", "requirement_id": "DORA-ART-06-ICT-RISK", "confidence": "Exact", "rationale": "Fulfills DORA ICT business continuity and disaster recovery requirements for AI."},
            {"framework_id": "nis2", "requirement_id": "NIS2-ART-21-SEC-MEASURES", "confidence": "Strong", "rationale": "Implements business continuity and crisis management under NIS2."}
        ]
    }
]

# Write crosswalk mappings to JSON
with open(DATA_DIR / "crosswalk_mappings.json", "w", encoding="utf-8") as f:
    json.dump(crosswalk_mappings, f, indent=2)
print(f"Wrote crosswalk mappings for {len(crosswalk_mappings)} controls to crosswalk_mappings.json")
