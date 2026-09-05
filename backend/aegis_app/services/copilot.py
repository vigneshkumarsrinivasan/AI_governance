"""
AI Governance Copilot Service.

IMPORTANT - what this actually is: a deterministic, rules-based Q&A responder.
It matches the query against a fixed set of keyword patterns and returns a
pre-written answer template, populated with this tenant's live data (system
counts, agent names, vendor names, etc. - fetched fresh from the database on
every call, tenant-scoped) and a hard-coded regulatory citation. There is NO
generative model, embedding search, or vector retrieval in this path - "RAG"
would be the wrong word for it, and earlier documentation/UI copy that
described it that way was inaccurate and has been corrected.

This is a legitimate design choice for a v1 (zero hallucination risk, zero
external data exposure, works with no API key), not a placeholder pretending
to be something else - CopilotQueryResponse.mode reports "rules_based" so
API consumers and the UI can be honest about it. A real generative layer can
be enabled via services/ai_provider.py (AI_PROVIDER=anthropic/openai + an API
key) without changing this file's tenant-scoped data-fetching logic - see
answer_query()'s use of get_configured_provider() below.
"""

from typing import Dict, Any, List, Optional
from aegis_app.core.config import settings
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.services.ai_provider import get_configured_provider, AIProviderError

class CopilotService:
    def answer_query(
        self,
        query: str,
        systems_context: List[Dict[str, Any]],
        controls_context: List[Dict[str, Any]],
        findings_context: List[Dict[str, Any]],
        vendors_context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        q = query.lower().strip()
        citations = []
        answer = ""
        confidence = "High"

        # Query 1: Why does EU AI Act apply?
        if "eu ai act" in q and ("apply" in q or "why" in q or "classification" in q):
            answer = (
                "The EU AI Act (Regulation (EU) 2024/1689) applies primarily based on system deployment and impact:\n\n"
                "1. **Jurisdiction Trigger**: It applies to providers placing AI systems on the EU market and deployers located in or impacting individuals in the EU (Art. 2).\n"
                "2. **Risk Classification**: Systems automating decisions on employment, creditworthiness, education, or essential private services fall under **Annex III (High-Risk)**, mandating Article 9 (Risk Management), Article 10 (Data Governance), Article 12 (Logging), and Article 14 (Human Oversight).\n"
                "3. **Transparency Obligations**: Interactive conversational agents and chatbots must disclose that the user is interacting with an AI system under **Article 50(1)**."
            )
            citations.append({
                "source": "EU Artificial Intelligence Act (Regulation (EU) 2024/1689)",
                "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",
                "reference": "Articles 2, 9-15, 50, and Annex III"
            })

        # Query 2: Which controls satisfy both NIST AI RMF and EU AI Act?
        elif ("both" in q and "nist" in q and "eu" in q) or ("crosswalk" in q and "nist" in q):
            matrix = crosswalk_service.get_crosswalk_matrix()
            overlapping = []
            for row in matrix:
                fw_ids = {m["framework_id"] for m in row["mappings"]}
                if "eu_ai_act" in fw_ids and "nist_ai_rmf" in fw_ids:
                    overlapping.append(f"• **{row['control_code']} - {row['control_title']}** ({row['domain']})")
            
            controls_list = "\n".join(overlapping[:8])
            answer = (
                f"The Unified Control Graph identifies {len(overlapping)} controls satisfying both EU AI Act and NIST AI RMF 1.0:\n\n"
                f"{controls_list}\n\n"
                "By implementing these unified controls once and attaching verified evidence, you satisfy Article 9/14/15 obligations under EU AI Act while fulfilling GOVERN 1.1, MAP 1.1, and MANAGE 2.4 under NIST AI RMF simultaneously."
            )
            citations.append({
                "source": "EU AI Act & NIST AI RMF Crosswalk Graph",
                "url": "https://airc.nist.gov/AI_RMF_Knowledge_Base/AI_RMF",
                "reference": "NIST AI 100-1 GOVERN/MAP & EU Regulation 2024/1689"
            })

        # Query 3: Which AI systems use personal data?
        elif "personal data" in q or "gdpr" in q or "privacy" in q:
            pd_systems = [s for s in systems_context if s.get("processes_personal_data")]
            if pd_systems:
                names = "\n".join([f"• **{s.get('name')}** (Unit: {s.get('business_unit')}, Risk: {s.get('risk_classification')})" for s in pd_systems])
                answer = (
                    f"There are **{len(pd_systems)} AI systems** currently processing personal data in your inventory:\n\n"
                    f"{names}\n\n"
                    "**Mandatory Actions**: Each of these systems triggers GDPR Article 25 (Privacy by Design), GDPR Article 35 (Data Protection Impact Assessment / DPIA), and India DPDPA Section 8 security safeguards."
                )
            else:
                answer = "No registered AI systems in your current inventory are flagged as processing personal data."
            citations.append({
                "source": "GDPR (Regulation (EU) 2016/679)",
                "url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
                "reference": "Articles 22, 25, 35"
            })

        # Query 4: Which agents can execute code or access databases?
        elif "agent" in q and ("code" in q or "execute" in q or "database" in q or "tool" in q):
            agentic_systems = [s for s in systems_context if s.get("is_agentic_ai")]
            if agentic_systems:
                details = []
                for s in agentic_systems:
                    details.append(
                        f"• **{s.get('name')}**: Autonomy level high. Deploys autonomous agents with code execution / DB access capabilities. "
                        f"Kill-switch status: {'Active' if s.get('kill_switch_implemented') else 'Missing'}."
                    )
                answer = (
                    f"Identified **{len(agentic_systems)} agentic AI applications** with autonomous tooling:\n\n"
                    + "\n".join(details) +
                    "\n\n**Mandatory Security Guardrails**: OWASP Agentic AI guidance (AGENT-01, AGENT-05, AGENT-07) requires sandboxed code execution, short-lived scoped tokens, and emergency kill-switches."
                )
            else:
                answer = "No active AI agents with code execution permissions are currently registered."
            citations.append({
                "source": "OWASP Agentic AI Security Guidance (2025)",
                "url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
                "reference": "AGENT-01 Privilege Escalation & AGENT-07 Kill-Switch"
            })

        # Query 5: Critical AI security findings
        elif "finding" in q or "critical" in q or "vulnerability" in q:
            crit_findings = [f for f in findings_context if f.get("severity") in ["Critical", "High"]]
            if crit_findings:
                items = "\n".join([f"• [{f.get('severity')}] **{f.get('title')}** (System: {f.get('system_name', 'Enterprise')}, Status: {f.get('status')})" for f in crit_findings[:5]])
                answer = (
                    f"Found **{len(crit_findings)} critical or high severity findings** requiring remediation:\n\n"
                    f"{items}\n\n"
                    "Immediate remediation is advised to avoid statutory audit failures and mitigate adversarial prompt injection or agent privilege risks."
                )
            else:
                answer = "There are currently zero open critical findings recorded in your AI security register."
            citations.append({
                "source": "OWASP Top 10 for LLM & MITRE ATLAS",
                "url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
                "reference": "LLM01 Prompt Injection & ATLAS Threat Matrix"
            })

        # Query 6: Vendors / Third-party risks
        elif "vendor" in q or "third party" in q or "third-party" in q:
            if vendors_context:
                v_list = "\n".join([f"• **{v.get('name')}** (Service: {v.get('service_type')}, Data Retention: {v.get('data_retention_days')}d, Risk: {v.get('risk_rating')})" for v in vendors_context])
                answer = (
                    f"You have **{len(vendors_context)} AI third-party providers** recorded:\n\n"
                    f"{v_list}\n\n"
                    "Under DORA Article 28 and NIST SP 800-161, verify that all foundation model providers have signed DPAs prohibiting model training on enterprise prompts."
                )
            else:
                answer = "No third-party AI vendors currently registered."
            citations.append({
                "source": "DORA (Regulation (EU) 2022/2554) & NIST SP 800-161",
                "url": "https://csrc.nist.gov/publications/detail/sp/800-161/rev-1/final",
                "reference": "DORA Article 28 & NIST SP 800-161 SR-3"
            })

        # Default query handler
        else:
            answer = (
                f"Regarding your query on '{query}':\n\n"
                "AegisAI's Unified Control Framework links your registered AI systems against 17 authoritative standards. "
                "You can navigate to the **Unified Controls** and **Crosswalk Matrix** modules to inspect specific requirements, "
                "view attached evidence artifacts, and check your real-time implementation score."
            )
            citations.append({
                "source": "AegisAI Authoritative Framework Library (17 Standards)",
                "url": "https://airc.nist.gov/AI_RMF_Knowledge_Base/AI_RMF",
                "reference": "Unified Control Catalog"
            })

        mode = "rules_based"
        provider = None
        try:
            provider = get_configured_provider()
        except AIProviderError:
            provider = None  # misconfigured provider must never break the rules-based fallback

        if provider is not None:
            # Generative enrichment is deliberately constrained to rephrasing
            # the already-grounded, cited answer above - it is not given
            # license to introduce new legal claims. If the call fails for
            # any reason, silently keep the rules-based answer rather than
            # erroring the whole request.
            system_prompt = (
                "You are AegisAI's compliance assistant. Rephrase the FACTUAL_ANSWER below in clearer prose "
                "for the compliance professional who asked QUESTION. Do not add, remove, or alter any legal claim, "
                "citation, article number, or figure in FACTUAL_ANSWER - only improve phrasing and readability. "
                "If FACTUAL_ANSWER says information is missing or zero, say so plainly; never invent detail."
                f"\n\nQUESTION: {query}\n\nFACTUAL_ANSWER:\n{answer}"
            )
            try:
                enriched = provider.generate(system_prompt, query)
                if enriched and enriched.strip():
                    answer = enriched.strip()
                    mode = f"generative_{settings.AI_PROVIDER}"
            except Exception:
                pass  # keep the rules-based answer

        return {
            "query": query,
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "mode": mode,
            "disclaimer": settings.LEGAL_DISCLAIMER
        }

copilot_service = CopilotService()
