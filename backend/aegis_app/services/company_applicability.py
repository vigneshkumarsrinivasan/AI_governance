"""
Company-level (organisation-wide) applicability engine (spec sections 6, 23, 24).

Complements the existing per-AI-system rule engine (services/rule_engine.py).
Where that engine answers "what is the regulatory classification of THIS AI
system", this one answers "which frameworks does THIS COMPANY need to care
about, and why" from the onboarding questionnaire.

Design constraints from the brief:
  * Never show every framework to every customer - each result is a reasoned
    exposure, not a blanket "applies".
  * Never assert legal certainty where scope depends on interpretation - those
    rules carry confidence == "LEGAL_REVIEW_REQUIRED" and the response flags
    `legal_review_recommended`.
  * Every determination shows: conclusion, confidence, reasoning, jurisdiction,
    the business facts that triggered it, the source/scope citation, and the
    questions still open.
  * Legal / regulatory vs certification vs voluntary framework vs best practice
    is always distinguished (spec section 23).

The ruleset lives in data/company_applicability_rules.json as versioned data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from aegis_app.services.rule_engine import _eval_condition, RuleEngineError

RULES_FILE = Path(__file__).resolve().parent.parent / "data" / "company_applicability_rules.json"

# exposure -> ApplicabilityDecision.decision_status vocabulary (models.py)
_STATUS_MAP = {
    "DIRECTLY_APPLICABLE": "APPLICABLE",
    "POTENTIALLY_APPLICABLE": "POTENTIALLY_APPLICABLE",
    "SUPPLY_CHAIN_INDIRECT": "LIKELY_APPLICABLE",
    "CONTRACTUALLY_REQUIRED": "LIKELY_APPLICABLE",
    "RECOMMENDED_BEST_PRACTICE": "POTENTIALLY_APPLICABLE",
    "NOT_APPLICABLE": "NOT_APPLICABLE",
    "INSUFFICIENT_INFORMATION": "UNKNOWN",
}

_EU_CODES = {"EU", "DE", "FR", "ES", "IT", "NL", "IE", "PL", "SE", "BE", "AT", "DK", "FI", "PT", "CZ", "GR", "RO", "HU"}

# more cautious (higher number) wins when two rules land on the same framework
# at the same exposure priority - we never want a "HIGH confidence, no review"
# rule to mask a "LEGAL_REVIEW_REQUIRED" one.
_CONFIDENCE_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "LEGAL_REVIEW_REQUIRED": 3}


class CompanyApplicabilityEngine:
    def __init__(self, rules_path: Optional[Path] = None):
        with open(rules_path or RULES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.ruleset_version: str = data["ruleset_version"]
        self.exposure_categories: Dict[str, Any] = data["exposure_categories"]
        self.rules: List[Dict[str, Any]] = data["rules"]

    # -- fact construction -------------------------------------------------
    @staticmethod
    def build_facts(profile: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise a stored OrganizationProfile (or raw questionnaire dict)
        into the flat fact dict the rules consume. Missing keys get safe
        defaults so a partially-completed questionnaire still evaluates."""
        g = profile.get
        countries = [str(c).upper() for c in (g("operating_countries") or [])]
        hq = str(g("headquarters_country") or "US").upper()
        facts = {
            "headquarters_country": hq,
            "operating_countries": countries,
            "employee_count": int(g("employee_count") or 0),
            "industry": g("industry") or "b2b_saas",
            "sells_to_enterprises": bool(g("sells_to_enterprises")),
            "sells_to_government": bool(g("sells_to_government")),
            "sells_to_financial_institutions": bool(g("sells_to_financial_institutions")),
            "sells_to_healthcare": bool(g("sells_to_healthcare")),
            "develops_ai_products": bool(g("develops_ai_products")),
            "deploys_ai_internally": bool(g("deploys_ai_internally")),
            "uses_generative_ai": bool(g("uses_generative_ai")),
            "builds_ai_agents": bool(g("builds_ai_agents")),
            "uses_rag": bool(g("uses_rag")),
            "uses_third_party_models": bool(g("uses_third_party_models")),
            "makes_decisions_about_people": bool(g("makes_decisions_about_people")),
            "decision_domains": list(g("decision_domains") or []),
            "uses_biometrics": bool(g("uses_biometrics")),
            "ai_providers": list(g("ai_providers") or []),
            "data_types": list(g("data_types") or []),
            "sells_software": bool(g("sells_software")),
            "is_saas": bool(g("is_saas")),
            "sells_connected_hardware": bool(g("sells_connected_hardware")),
            "is_iot": bool(g("is_iot")),
            "has_embedded_software": bool(g("has_embedded_software")),
            "is_cybersecurity_product": bool(g("is_cybersecurity_product")),
            "product_marketed_in_eu": bool(g("product_marketed_in_eu")),
            "soc2_required": bool(g("soc2_required")),
            "iso27001_required": bool(g("iso27001_required")),
            "gets_security_questionnaires": bool(g("gets_security_questionnaires")),
            "existing_certifications": [str(c).lower() for c in (g("existing_certifications") or [])],
            "has_compliance_staff": bool(g("has_compliance_staff")),
            "has_security_staff": bool(g("has_security_staff")),
        }
        # small derived fact used by several rules / the UI
        facts["eu_exposed"] = bool(set(countries) & _EU_CODES) or facts["product_marketed_in_eu"]
        return facts

    # -- evaluation ------------------------------------------------------
    def evaluate(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        facts = self.build_facts(profile)
        by_framework: Dict[str, Dict[str, Any]] = {}
        rules_fired: List[Dict[str, Any]] = []

        for rule in self.rules:
            try:
                hit = _eval_condition(rule["conditions"], facts)
            except RuleEngineError:
                # a rule referencing a fact we don't have is treated as "not fired"
                # rather than crashing the whole evaluation.
                hit = False
            if not hit:
                continue

            rules_fired.append({
                "rule_id": rule["rule_id"],
                "framework_key": rule["framework_key"],
                "exposure": rule["exposure"],
                "confidence": rule["confidence"],
                "ruleset_version": self.ruleset_version,
            })

            fk = rule["framework_key"]
            prio = self.exposure_categories.get(rule["exposure"], {}).get("priority", 0)
            triggering = _explain_triggering_facts(rule["conditions"], facts)
            reasoning = rule["reasoning_template"].replace(
                "{decision_domains}", ", ".join(facts["decision_domains"]) or "the declared domains"
            )
            candidate = {
                "framework_key": fk,
                "framework_name": rule["framework_name"],
                "regulation_type": rule["regulation_type"],
                "exposure": rule["exposure"],
                "exposure_label": self.exposure_categories.get(rule["exposure"], {}).get("label", rule["exposure"]),
                "confidence": rule["confidence"],
                "jurisdiction": rule["jurisdiction"],
                "reasoning": reasoning,
                "source_reference": rule["source_reference"],
                "triggering_facts": triggering,
                "open_questions": list(rule.get("open_questions") or []),
                "decision_status": _STATUS_MAP.get(rule["exposure"], "UNKNOWN"),
                "rule_id": rule["rule_id"],
                "_priority": prio,
            }
            existing = by_framework.get(fk)
            if existing is None or prio > existing["_priority"]:
                if existing:
                    candidate["open_questions"] = list(dict.fromkeys(
                        existing["open_questions"] + candidate["open_questions"]
                    ))
                by_framework[fk] = candidate
            elif prio == existing["_priority"]:
                # same exposure from another rule: merge - take the more cautious
                # confidence, keep both reasons and both citations, union the
                # open questions and triggering facts.
                existing["open_questions"] = list(dict.fromkeys(
                    existing["open_questions"] + candidate["open_questions"]
                ))
                existing["triggering_facts"] = list(dict.fromkeys(
                    existing["triggering_facts"] + candidate["triggering_facts"]
                ))
                if _CONFIDENCE_RANK.get(candidate["confidence"], 0) > _CONFIDENCE_RANK.get(existing["confidence"], 0):
                    existing["confidence"] = candidate["confidence"]
                if candidate["reasoning"] not in existing["reasoning"]:
                    existing["reasoning"] = existing["reasoning"].rstrip() + "  " + candidate["reasoning"]
                if candidate["source_reference"] not in existing["source_reference"]:
                    existing["source_reference"] = existing["source_reference"].rstrip() + "  |  " + candidate["source_reference"]
                existing.setdefault("contributing_rule_ids", [existing["rule_id"]])
                existing["contributing_rule_ids"].append(candidate["rule_id"])
            else:
                existing["open_questions"] = list(dict.fromkeys(
                    existing["open_questions"] + candidate["open_questions"]
                ))

        exposures = []
        for v in by_framework.values():
            v.pop("_priority", None)
            v.setdefault("contributing_rule_ids", [v["rule_id"]])
            exposures.append(v)
        exposures.sort(key=lambda e: (
            -self.exposure_categories.get(e["exposure"], {}).get("priority", 0),
            e["framework_name"],
        ))

        legal_review = [e for e in exposures if e["confidence"] == "LEGAL_REVIEW_REQUIRED"]
        all_open_questions = sorted({q for e in exposures for q in e["open_questions"]})

        return {
            "ruleset_version": self.ruleset_version,
            "facts": facts,
            "exposures": exposures,
            "rules_fired": rules_fired,
            "legal_review_recommended": bool(legal_review),
            "legal_review_frameworks": [e["framework_key"] for e in legal_review],
            "open_questions": all_open_questions,
            "summary": _summarise(exposures),
        }


def _explain_triggering_facts(cond: Dict[str, Any], facts: Dict[str, Any]) -> List[str]:
    """Best-effort human list of which declared facts made a rule fire."""
    out: List[str] = []

    def walk(c: Dict[str, Any]):
        if "all" in c:
            for x in c["all"]:
                walk(x)
            return
        if "any" in c:
            for x in c["any"]:
                try:
                    if _eval_condition(x, facts):
                        walk(x)
                        return
                except RuleEngineError:
                    continue
            return
        field = c.get("field")
        if not field:
            return
        val = facts.get(field)
        if isinstance(val, bool) and val:
            out.append(field.replace("_", " "))
        elif isinstance(val, list) and val:
            out.append(f"{field.replace('_', ' ')}: {', '.join(map(str, val))}")
        elif isinstance(val, (int, float)) and c.get("op") in ("gte", "gt", "lte", "lt"):
            out.append(f"{field.replace('_', ' ')} = {val}")
        elif isinstance(val, str) and val:
            out.append(f"{field.replace('_', ' ')} = {val}")

    try:
        walk(cond)
    except Exception:
        pass
    return list(dict.fromkeys(out))


def _summarise(exposures: List[Dict[str, Any]]) -> Dict[str, int]:
    s: Dict[str, int] = {}
    for e in exposures:
        s[e["exposure"]] = s.get(e["exposure"], 0) + 1
    return s


company_applicability_engine = CompanyApplicabilityEngine()
