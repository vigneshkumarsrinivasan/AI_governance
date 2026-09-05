"""
Configurable Applicability Rule Engine (spec #8).

Legal classification logic lives here as versioned, inspectable data
(data/applicability_rules.json) rather than hard-coded Python if/else chains.
Adding, correcting, or retiring a regulatory trigger means editing that JSON
file and bumping its ruleset_version - not shipping a code change - and every
past decision remains reproducible because ApplicabilityDecision records
(models.py) store which ruleset_version and which specific rule_ids fired.

This module intentionally supports only the operators actually needed by the
current ruleset (is_true/is_false/contains/not_contains/intersects/equals),
in nested all/any groups. Extending it (date-effective windows, exceptions,
jurisdiction filters beyond the simple ones used today) is straightforward
because conditions are plain data, not code.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

RULES_FILE = Path(__file__).resolve().parent.parent / "data" / "applicability_rules.json"


class RuleEngineError(ValueError):
    pass


def _get_field(facts: Dict[str, Any], field: str) -> Any:
    if field not in facts:
        raise RuleEngineError(f"Rule references unknown fact field '{field}'")
    return facts[field]


def _eval_condition(cond: Dict[str, Any], facts: Dict[str, Any]) -> bool:
    if "all" in cond:
        return all(_eval_condition(c, facts) for c in cond["all"])
    if "any" in cond:
        return any(_eval_condition(c, facts) for c in cond["any"])

    field = cond["field"]
    op = cond["op"]
    value = _get_field(facts, field)

    if op == "is_true":
        return bool(value)
    if op == "is_false":
        return not bool(value)
    if op == "equals":
        return value == cond.get("value")
    if op == "contains":
        target = cond.get("value")
        if isinstance(value, str):
            return target in value
        if isinstance(value, (list, set, tuple)):
            return target in value
        return False
    if op == "not_contains":
        target = cond.get("value")
        if isinstance(value, str):
            return target not in value
        if isinstance(value, (list, set, tuple)):
            return target not in value
        return True
    if op == "intersects":
        target = set(cond.get("value", []))
        if not isinstance(value, (list, set, tuple)):
            return False
        return len(set(value) & target) > 0

    raise RuleEngineError(f"Unknown condition operator '{op}'")


class RuleEngine:
    def __init__(self, rules_path: Optional[Path] = None):
        path = rules_path or RULES_FILE
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.ruleset_version: str = data["ruleset_version"]
        self.categories: Dict[str, Dict[str, Any]] = data["categories"]
        self.rules: List[Dict[str, Any]] = data["rules"]

    def evaluate(self, facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates every rule against `facts`. Returns the resolved risk
        category/classification (highest-priority fired classification rule,
        falling back to "minimal_risk" if none fired) plus the union of all
        additive frameworks/controls, with full rule-level provenance so the
        caller can persist exactly which rules produced this outcome.
        """
        fired: List[Dict[str, Any]] = []
        classification_candidates: List[Dict[str, Any]] = []
        frameworks_added: List[str] = []
        controls_added: List[str] = []
        privacy_regulations: List[str] = []
        privacy_reasons: List[str] = []
        agent_security_required = False

        for rule in self.rules:
            if not _eval_condition(rule["conditions"], facts):
                continue

            fired.append({
                "rule_id": rule["rule_id"],
                "framework": rule.get("framework"),
                "requirement_id": rule.get("requirement_id"),
                "version": rule.get("version"),
            })

            category = rule["category"]
            if category in self.categories and category != "additive":
                reason = (rule.get("reason_template") or "").replace(
                    "{{high_risk_domain_intersection}}",
                    ", ".join(sorted(facts.get("high_risk_domain_intersection", [])))
                )
                classification_candidates.append({
                    "category": category,
                    "priority": self.categories[category]["priority"],
                    "reason": reason,
                    "rule_id": rule["rule_id"],
                })

            frameworks_added.extend(rule.get("frameworks_added", []))
            controls_added.extend(rule.get("controls_added", []))
            if rule.get("agent_security_flag"):
                agent_security_required = True
            if rule.get("privacy_regulation"):
                privacy_regulations.append(rule["privacy_regulation"])
            if category == "additive" and rule.get("reason_template") and rule.get("privacy_regulation"):
                privacy_reasons.append(rule["reason_template"])

        if classification_candidates:
            best = max(classification_candidates, key=lambda c: c["priority"])
            best_category = best["category"]
            reasons_in_category = [
                c["reason"] for c in classification_candidates
                if c["category"] == best_category and c["reason"]
            ]
        else:
            best_category = "minimal_risk"
            reasons_in_category = []

        cat_meta = self.categories[best_category]
        prefix = cat_meta["rationale_prefix"]
        rationale = f"{prefix} " + " ".join(reasons_in_category) if reasons_in_category else prefix

        return {
            "ruleset_version": self.ruleset_version,
            "risk_level": cat_meta["risk_level"],
            "eu_ai_act_classification": cat_meta["eu_ai_act_classification"],
            "eu_ai_act_rationale": rationale.strip(),
            "requires_legal_review": cat_meta["legal_review_required"],
            "recommended_frameworks": list(dict.fromkeys(frameworks_added)),
            "required_unified_controls": list(dict.fromkeys(controls_added)),
            "privacy_regulations_applicable": list(dict.fromkeys(privacy_regulations)),
            "privacy_rationale": " ".join(privacy_reasons) if privacy_reasons else "No personal data declared in processing pipeline, or no privacy-triggering jurisdiction matched.",
            "agent_security_required": agent_security_required,
            "rules_fired": fired,
        }


rule_engine = RuleEngine()
