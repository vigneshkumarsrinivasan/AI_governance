"""AI Verify technical-test adapter (scaffold).

Architecture (spec sections 8-10):

    AegisAI platform
      -> AIEvaluationJob (per AI system + model + dataset)
        -> AIVerifyAdapter
          -> AI Verify test engine / stock algorithm plugin
            -> raw result
              -> normalized EvaluationResult
                -> Evidence  ->  Unified Control  ->  Requirement  ->  Assessment

This module currently provides:
  * a registry of AI Verify stock technical-test plugins discovered from the
    official repo (name, algorithm, principle, cid), and
  * ``import_result()`` - ingest an operator-run AI Verify result JSON and turn
    it into a normalized evaluation record.

It does NOT bundle or execute the AI Verify engine (that needs the aiverify
toolkit + its own runtime). Running tests in-process is a follow-up: shell out
to ``aiverify-test-engine`` or call its REST API, then feed the output here.

Customer datasets / models used for AI Verify tests are tenant-isolated and are
never promoted to shared reference content (spec section 60).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

AIVERIFY_REPO = "aiverify-foundation/aiverify"

# Stock technical-test plugins in aiverify-foundation/aiverify (Apache-2.0).
# `principle` links a passed/failed result back to the AI Verify Testing
# Framework principle ingested by parsers/aiverify.py, and thence to requirements.
STOCK_TESTS: List[Dict[str, str]] = [
    {"plugin": "aiverify.stock.fairness-metrics-toolbox-for-classification",
     "capability": "fairness", "principle": "Fairness",
     "algorithm": "fairness_metrics_toolbox_for_classification",
     "description": "Group fairness metrics for classification models (parity metrics)."},
    {"plugin": "aiverify.stock.fairness-metrics-toolbox-for-regression",
     "capability": "fairness", "principle": "Fairness",
     "algorithm": "fairness_metrics_toolbox_for_regression",
     "description": "Group fairness metrics for regression models."},
    {"plugin": "aiverify.stock.robustness-toolbox", "capability": "robustness", "principle": "Robustness",
     "algorithm": "robustness_toolbox",
     "description": "Boundary-attack robustness evaluation (perturbation sensitivity)."},
    {"plugin": "aiverify.stock.shap-toolbox", "capability": "explainability", "principle": "Explainability",
     "algorithm": "shap_toolbox", "description": "SHAP global/local feature-contribution explainability."},
    {"plugin": "aiverify.stock.accumulated-local-effect", "capability": "explainability",
     "principle": "Explainability", "algorithm": "accumulated_local_effect",
     "description": "Accumulated Local Effects plots for feature influence."},
    {"plugin": "aiverify.stock.partial-dependence-plot", "capability": "explainability",
     "principle": "Explainability", "algorithm": "partial_dependence_plot",
     "description": "Partial Dependence Plots for feature influence."},
    {"plugin": "aiverify.stock.image-corruption-toolbox", "capability": "robustness",
     "principle": "Robustness", "algorithm": "image_corruption_toolbox",
     "description": "Robustness of vision models to common image corruptions."},
    {"plugin": "aiverify.stock.veritas", "capability": "fairness", "principle": "Fairness",
     "algorithm": "veritas", "description": "MAS Veritas fairness assessment methodology toolkit."},
    {"plugin": "aiverify.stock.process-checklist", "capability": "process_checklist", "principle": "*",
     "algorithm": "process_checklist",
     "description": "Governance process checklist (documentary evidence, all 11 principles)."},
]


def capabilities() -> List[str]:
    return sorted({t["capability"] for t in STOCK_TESTS})


def tests_for_capability(capability: str) -> List[Dict[str, str]]:
    return [t for t in STOCK_TESTS if t["capability"] == capability]


@dataclass
class NormalizedEvaluationResult:
    system_id: str
    model_ref: str
    dataset_ref: Optional[str]
    capability: str
    algorithm: str
    test_engine_version: Optional[str]
    aiverify_repo_ref: Optional[str]
    executed_at: str
    outcome: str                       # PASSED_CONFIGURED_TESTS | FAILED | INCONCLUSIVE | NOT_RUN
    thresholds: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    raw_result: Dict[str, Any] = field(default_factory=dict)
    principle: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def as_evidence_payload(self) -> Dict[str, Any]:
        """Shape for creating an Evidence record + EvidenceControlMap entries."""
        return {
            "title": f"AI Verify {self.algorithm} result - {self.outcome}",
            "evidence_type": "Test Report",
            "description": (f"AI Verify {self.capability} evaluation ({self.algorithm}) for system "
                            f"{self.system_id} / model {self.model_ref}. Outcome: {self.outcome}."),
            "metadata": {
                "source": "ai_verify_adapter", "capability": self.capability,
                "algorithm": self.algorithm, "principle": self.principle,
                "test_engine_version": self.test_engine_version,
                "aiverify_repo_ref": self.aiverify_repo_ref,
                "executed_at": self.executed_at, "thresholds": self.thresholds,
                "metrics": self.metrics,
            },
        }


def import_result(*, system_id: str, model_ref: str, capability: str,
                  result_json: Dict[str, Any], dataset_ref: Optional[str] = None,
                  test_engine_version: Optional[str] = None,
                  aiverify_repo_ref: Optional[str] = None) -> NormalizedEvaluationResult:
    """Normalize an operator-supplied AI Verify result document.

    AI Verify result JSON shapes vary by plugin/version; this reads the common
    fields and keeps the full document under ``raw_result``. It never asserts
    the AI system is "safe" - only that it passed the tests as configured.
    """
    algo = (result_json.get("algorithmId") or result_json.get("algorithm")
            or result_json.get("gid") or capability)
    output = result_json.get("output") or result_json.get("results") or result_json
    metrics = {k: v for k, v in output.items() if isinstance(v, (int, float, str, bool))} \
        if isinstance(output, dict) else {}

    passed = result_json.get("passed")
    if passed is None:
        passed = result_json.get("test_status") in ("success", "pass", "passed")
    outcome = "PASSED_CONFIGURED_TESTS" if passed else (
        "FAILED" if passed is False else "INCONCLUSIVE")

    principle = next((t["principle"] for t in STOCK_TESTS
                      if t["capability"] == capability and t["principle"] != "*"), None)

    return NormalizedEvaluationResult(
        system_id=system_id, model_ref=model_ref, dataset_ref=dataset_ref,
        capability=capability, algorithm=str(algo), test_engine_version=test_engine_version,
        aiverify_repo_ref=aiverify_repo_ref,
        executed_at=result_json.get("timeStamp") or datetime.now(timezone.utc).isoformat(),
        outcome=outcome,
        thresholds=result_json.get("thresholds") or {},
        metrics=metrics, raw_result=result_json, principle=principle,
        notes=["Outcome reflects configured test thresholds only - not a safety guarantee."],
    )
