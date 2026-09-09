"""
Unified Control <-> regulatory requirement mapping proposer (MOAT 1 + 2).

Given the 27-control Unified Control Library and the ~3,200 source-traceable
regulatory requirements, this proposes candidate mappings by matching curated
per-control term sets against each requirement's normalized text + citation +
domain. Every proposed row is `state = "AI_SUGGESTED"`, `proposed_by = "AI"`,
`mapping_source = "ai_proposer"` - it is NOT authoritative and does not count
toward coverage until a reviewer moves it to EXPERT_REVIEWED / APPROVED.

The curated `crosswalk_mappings.json` (hand-authored) is loaded as
`mapping_source = "crosswalk_seed"`, `proposed_by = "HUMAN"`, and - because it
was authored by a person - `state = "APPROVED"` where its requirement key can be
resolved to a real ingested requirement (otherwise NEEDS_REVIEW).

This is candidate generation, not legal interpretation. It never invents
requirement text.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_app.models.regulatory import RegulatoryRequirement, RequirementControlMapping, FrameworkVersion

_DATA = Path(__file__).resolve().parent.parent / "data"

# ---------------------------------------------------------------------------
# Curated per-control matching spec. `anchor` terms are specific phrases - a
# proposal requires at least one anchor hit. `support` terms add confidence.
# `domains` are requirement-domain / citation keywords. This is domain
# knowledge about what each control addresses - it never invents requirement
# text and every proposal is AI_SUGGESTED pending review.
# ---------------------------------------------------------------------------
CONTROL_SPEC: Dict[str, Dict[str, Any]] = {
    "UC-AI-GOV-001": {"anchor": ["ai governance policy", "responsible ai", "ai policy", "ethical principle", "risk appetite", "ai management system", "code of conduct", "governance framework"], "support": ["governance", "policy", "board approval", "acceptable use", "oversight"], "domains": ["govern"]},
    "UC-AI-GOV-002": {"anchor": ["raci", "roles and responsibilit", "accountable person", "governance structure", "designated owner", "oversight function", "assign responsibilit"], "support": ["role", "accountab", "designat"], "domains": ["govern", "accountability"]},
    "UC-AI-INV-001": {"anchor": ["ai inventory", "system registry", "register of ai", "catalogue of ai", "technical documentation", "record of the ai system", "list of ai systems"], "support": ["inventory", "documentation", "architecture"], "domains": ["inventory", "documentation"]},
    "UC-AI-INV-002": {"anchor": ["prohibited practice", "unacceptable risk", "subliminal", "social scoring", "manipulative technique", "exploit vulnerabilities of", "banned use"], "support": ["prohibit", "not be placed on the market"], "domains": ["prohibited"]},
    "UC-AI-RSK-001": {"anchor": ["risk management system", "risk assessment", "risk register", "residual risk", "risk treatment", "risk analysis", "fundamental rights impact assessment", "lifecycle risk"], "support": ["risk appetite", "mitigation measure"], "domains": ["risk"]},
    "UC-AI-SEC-001": {"anchor": ["prompt injection", "prompt manipulation", "jailbreak", "adversarial input", "indirect prompt"], "support": ["context demarcation", "input validation"], "domains": ["security", "robustness"]},
    "UC-AI-SEC-002": {"anchor": ["data poisoning", "model poisoning", "training data integrity", "backdoor", "model tampering"], "support": ["poison", "integrity of training"], "domains": ["security"]},
    "UC-AI-SEC-003": {"anchor": ["insecure output", "output sanitiz", "output encoding", "downstream injection", "unvalidated output"], "support": ["output handling", "content filtering"], "domains": ["security"]},
    "UC-AI-AGT-001": {"anchor": ["least privilege", "tool permission", "excessive agency", "scope of autonomous action", "agent authoriz", "over-privileged"], "support": ["permission boundary", "capability restriction"], "domains": ["agent", "security"]},
    "UC-AI-AGT-002": {"anchor": ["kill switch", "kill-switch", "stop button", "emergency stop", "ability to shut down", "disable the system"], "support": ["deactivat", "halt operation"], "domains": ["oversight", "agent"]},
    "UC-AI-AGT-003": {"anchor": ["human-in-the-loop", "human in the loop", "human approval", "human confirmation", "approval gate", "human intervention"], "support": ["override the system", "review before action"], "domains": ["oversight", "human"]},
    "UC-AI-DAT-001": {"anchor": ["data minimis", "data minimiz", "pii redaction", "pseudonymis*", "anonymis*", "special categor", "purpose limitation", "personal data reduction"], "support": ["personal data", "sensitive data"], "domains": ["privacy", "data"]},
    "UC-AI-DAT-002": {"anchor": ["data protection impact assessment", "dpia", "impact assessment on data protection", "article 35", "prior consultation"], "support": ["risk to the rights and freedoms"], "domains": ["privacy", "impact"]},
    "UC-AI-TRN-001": {"anchor": ["inform natural persons", "interacting with an ai", "disclosure that", "made aware that", "ai interaction disclosure", "chatbot disclosure"], "support": ["transparen", "notify the user"], "domains": ["transparency"]},
    "UC-AI-TRN-002": {"anchor": ["watermark", "synthetic content", "deepfake", "deep fake", "artificially generated", "content provenance", "machine-readable mark"], "support": ["provenance", "content credentials"], "domains": ["transparency"]},
    "UC-AI-LOG-001": {"anchor": ["automatic recording of events", "logging capabilit", "record-keeping", "record keeping", "audit trail", "event logs", "retention of logs", "immutable log"], "support": ["traceability", "monitoring"], "domains": ["logging", "record"]},
    "UC-AI-INC-001": {"anchor": ["serious incident", "incident reporting", "report to the authority", "breach notification", "malfunction", "post-market monitoring", "notify without undue delay"], "support": ["incident", "escalat"], "domains": ["incident", "reporting"]},
    "UC-AI-SC-001": {"anchor": ["third-party provider", "third party provider", "supplier due diligence", "vendor assessment", "provider of the general-purpose", "upstream provider", "foundation model provider"], "support": ["due diligence", "third-party"], "domains": ["supply chain", "vendor"]},
    "UC-AI-SC-002": {"anchor": ["bill of materials", "sbom", "aibom", "software composition", "component inventory", "provenance of components"], "support": ["dependenc"], "domains": ["supply chain"]},
    "UC-AI-TST-001": {"anchor": ["red team", "red-team", "adversarial testing", "penetration test", "pre-deployment evaluation", "robustness testing", "adversarial robustness"], "support": ["testing before deployment"], "domains": ["testing", "security"]},
    "UC-AI-TST-002": {"anchor": ["bias evaluation", "fairness assessment", "discriminatory", "disparate impact", "protected characteristic", "representative training data", "measure and mitigate bias"], "support": ["bias", "fairness"], "domains": ["fairness", "bias"]},
    "UC-AI-ACC-001": {"anchor": ["hallucinat*", "confabulat*", "retrieval-augmented", "retrieval augmented", "level of accuracy", "factual accuracy", "grounding of output", "grounding in retrieved"], "support": ["accuracy metric", "reliability", "rag pipeline"], "domains": ["accuracy", "robustness"]},
    "UC-AI-AGT-004": {"anchor": ["memory poisoning", "context isolation", "cross-user contamination", "session isolation", "conversation history leakage"], "support": ["memory isolation"], "domains": ["agent", "security"]},
    "UC-AI-AGT-005": {"anchor": ["code execution sandbox", "sandbox", "arbitrary code execution", "containeris*", "isolate code execution", "unrestricted code"], "support": ["execution environment"], "domains": ["agent", "security"]},
    "UC-AI-VUL-001": {"anchor": ["vulnerability management", "coordinated disclosure", "security patch", "patch management", "cve", "remediate vulnerabilit"], "support": ["vulnerab", "security update"], "domains": ["vulnerability", "security"]},
    "UC-AI-VND-001": {"anchor": ["opt out of training", "opt-out", "not used for training", "training on customer data", "intellectual property protection", "copyright of training", "data used for model training"], "support": ["licensing of data"], "domains": ["vendor", "data"]},
    "UC-AI-RES-001": {"anchor": ["operational resilience", "business continuity", "fallback mechanism", "failover", "graceful degradation", "service continuity", "disaster recovery"], "support": ["resilien", "availab", "recover"], "domains": ["resilience", "recover"]},
}

# MITRE ATLAS is a threat knowledge base, not a governance-obligation framework;
# ATLAS<->control links come from the curated crosswalk, not the keyword proposer.
_PROPOSER_SKIP_FRAMEWORKS = {"mitre_atlas"}


_BOUNDARY_CACHE: Dict[str, "re.Pattern"] = {}


def _phrase_in(phrase: str, haystack: str) -> bool:
    """Left-boundary match so 'rag' never matches 'sto*rag*e' and 'raci' never
    matches 'racial'. Right side:
      - trailing '*'            -> explicit stem match ('hallucinat*' -> 'hallucination')
      - short single token (<5) -> require a right boundary too (blocks 'cve'/'raci'
                                   false friends)
      - everything else         -> stem match by default, since the curated terms
                                   ('accountab', 'poison', 'vulnerab', ...) are
                                   deliberately word roots.
    """
    p = _BOUNDARY_CACHE.get(phrase)
    if p is None:
        stem = phrase.endswith("*")
        core = phrase[:-1] if stem else phrase
        if stem or not (len(core) < 5 and core.isalpha()):
            right = r"[a-z]*"
        else:
            right = r"(?![a-z])"
        p = re.compile(r"(?<![a-z])" + re.escape(core) + right)
        _BOUNDARY_CACHE[phrase] = p
    return p.search(haystack) is not None


def _score(control: Dict[str, Any], haystack: str, req_domain: str) -> Tuple[float, List[str]]:
    spec = CONTROL_SPEC.get(control["code"])
    if not spec:
        return 0.0, []
    anchors = [t for t in spec["anchor"] if _phrase_in(t, haystack)]
    if not anchors:
        return 0.0, []
    support = [t for t in spec.get("support", []) if _phrase_in(t, haystack)]
    # A lone anchor with no other signal should land in PARTIAL (review candidate),
    # never STRONG - STRONG needs corroboration (a 2nd anchor, support term, or the
    # control's own domain word appearing verbatim).
    base = 0.38 + 0.14 * (len(anchors) - 1) + 0.06 * len(support)
    dom = req_domain.lower()
    if any(d in dom for d in spec["domains"]):
        base += 0.12
    if control["domain"].split()[0].lower() in haystack:
        base += 0.06
    return min(1.0, round(base, 2)), (anchors + support)


def _mtype(score: float, domain_aligned: bool) -> str:
    if score >= 0.75 and domain_aligned:
        return "EXACT"
    if score >= 0.55:
        return "STRONG"
    if score >= 0.34:
        return "PARTIAL"
    return "RELATED"


async def propose_mappings(
    db: AsyncSession, *, controls: List[Dict[str, Any]], min_score: float = 0.42,
    frameworks: List[str] | None = None,
) -> Dict[str, Any]:
    """Idempotently propose AI_SUGGESTED mappings. Returns a summary."""
    # existing (requirement_id, control_code) pairs so we never duplicate
    existing = {
        (m.requirement_id, m.control_code)
        for m in (await db.execute(select(RequirementControlMapping))).scalars().all()
    }

    q = select(RegulatoryRequirement, FrameworkVersion.framework_key).join(
        FrameworkVersion, FrameworkVersion.id == RegulatoryRequirement.framework_version_id
    )
    rows = (await db.execute(q)).all()

    created = 0
    by_control: Dict[str, int] = {}
    by_framework: Dict[str, int] = {}
    for req, fw_key in rows:
        if fw_key in _PROPOSER_SKIP_FRAMEWORKS:
            continue
        if frameworks and fw_key not in frameworks:
            continue
        hay = f"{req.normalized_requirement or ''} {req.source_reference or ''} {req.domain or ''}".lower()
        for c in controls:
            if (req.id, c["code"]) in existing:
                continue
            score, hits = _score(c, hay, req.domain or "")
            if score < min_score:
                continue
            spec = CONTROL_SPEC.get(c["code"], {})
            dom_aligned = any(d in (req.domain or "").lower() for d in spec.get("domains", []))
            db.add(RequirementControlMapping(
                requirement_id=req.id,
                control_code=c["code"],
                mapping_type=_mtype(score, dom_aligned),
                confidence=score,
                rationale=(f"AI-proposed candidate: requirement text/citation matched "
                           f"control terms [{', '.join(hits[:6])}]"
                           + (f"; requirement domain '{req.domain}' aligns with control domain '{c['domain']}'." if dom_aligned else ".")),
                proposed_by="AI",
                state="AI_SUGGESTED",
                mapping_source="ai_proposer",
                mapping_version="1.0",
            ))
            existing.add((req.id, c["code"]))
            created += 1
            by_control[c["code"]] = by_control.get(c["code"], 0) + 1
            by_framework[fw_key] = by_framework.get(fw_key, 0) + 1

    await db.commit()
    return {"created": created, "by_control": by_control, "by_framework": by_framework}


async def load_crosswalk_seed(db: AsyncSession) -> Dict[str, Any]:
    """Load the hand-authored crosswalk_mappings.json as human-authored mappings."""
    path = _DATA / "crosswalk_mappings.json"
    if not path.exists():
        return {"created": 0, "resolved": 0, "unresolved": 0}
    seed = json.loads(path.read_text(encoding="utf-8"))

    # index real requirements by a few key forms so legacy ids can resolve
    reqs = (await db.execute(
        select(RegulatoryRequirement.id, RegulatoryRequirement.requirement_key, RegulatoryRequirement.source_reference)
    )).all()
    by_key: Dict[str, str] = {}
    for rid, rkey, sref in reqs:
        by_key[rkey.upper()] = rid
        by_key[rkey.upper().replace("-", "")] = rid
        if sref:
            by_key[sref.upper().replace(" ", "").replace("(", "").replace(")", "")] = rid

    def resolve(legacy_id: str) -> str | None:
        k = (legacy_id or "").upper()
        for cand in (k, k.replace("-", ""), k.replace("ART-0", "ARTICLE-").replace("ART-", "ARTICLE-"),
                     k.replace("AML-T", "AML.T")):
            if cand in by_key:
                return by_key[cand]
        return None

    existing = {
        (m.requirement_id, m.control_code)
        for m in (await db.execute(select(RequirementControlMapping))).scalars().all()
    }
    conf_map = {"Exact": ("EXACT", 0.95), "Strong": ("STRONG", 0.8), "Partial": ("PARTIAL", 0.55), "Related": ("RELATED", 0.4)}
    created = resolved = unresolved = 0
    for row in seed:
        cc = row.get("control_id") or row.get("control_code")
        for m in row.get("mappings", []):
            rid = resolve(m.get("requirement_id", ""))
            if not rid:
                unresolved += 1
                continue
            resolved += 1
            if (rid, cc) in existing:
                continue
            mt, conf = conf_map.get(m.get("confidence", "Related"), ("RELATED", 0.4))
            db.add(RequirementControlMapping(
                requirement_id=rid, control_code=cc, mapping_type=mt, confidence=conf,
                rationale=m.get("rationale", "Hand-authored crosswalk mapping."),
                proposed_by="HUMAN", state="APPROVED", mapping_source="crosswalk_seed",
                mapping_version="1.0", legal_review_status="NOT_REVIEWED",
            ))
            existing.add((rid, cc))
            created += 1
    await db.commit()
    return {"created": created, "resolved": resolved, "unresolved": unresolved}


_AUTH_CONF = {"EXACT": 0.97, "STRONG": 0.85, "PARTIAL": 0.6, "RELATED": 0.45}


async def load_authoritative_seed(db: AsyncSession) -> Dict[str, Any]:
    """Load the expert-curated mapping file (keyed by real requirement_key) as
    state = "EXPERT_REVIEWED" mappings. Unlike the AI proposer these DO count
    toward coverage - a person reviewed each one against the primary source.
    Idempotent."""
    path = _DATA / "authoritative_control_mappings.json"
    if not path.exists():
        return {"created": 0, "resolved": 0, "unresolved": 0, "unresolved_keys": []}
    doc = json.loads(path.read_text(encoding="utf-8"))
    reviewer = doc.get("reviewer", "content-team")
    review_date = doc.get("review_date")

    # Resolve each requirement_key to the row in the *current* framework version
    # (is_current wins; otherwise newest by created_at) so a key that exists in
    # several ingested versions binds to the one coverage actually scores.
    rows = (await db.execute(
        select(RegulatoryRequirement.requirement_key, RegulatoryRequirement.id,
               FrameworkVersion.is_current, FrameworkVersion.created_at)
        .join(FrameworkVersion, FrameworkVersion.id == RegulatoryRequirement.framework_version_id)
    )).all()
    key_to_id: Dict[str, str] = {}
    _key_rank: Dict[str, tuple] = {}
    for rkey, rid, is_cur, created in rows:
        cval = created.replace(tzinfo=None) if getattr(created, "tzinfo", None) else created
        rank = (1 if is_cur else 0, cval or datetime.min)
        if rkey not in _key_rank or rank > _key_rank[rkey]:
            _key_rank[rkey] = rank
            key_to_id[rkey] = rid
    existing = {
        (m.requirement_id, m.control_code)
        for m in (await db.execute(select(RequirementControlMapping))).scalars().all()
    }

    created = resolved = unresolved = 0
    unresolved_keys: List[str] = []
    for row in doc.get("mappings", []):
        rid = key_to_id.get(row["requirement_key"])
        if not rid:
            unresolved += 1
            unresolved_keys.append(row["requirement_key"])
            continue
        resolved += 1
        cc = row["control_code"]
        if (rid, cc) in existing:
            continue
        mt = row.get("mapping_type", "STRONG").upper()
        db.add(RequirementControlMapping(
            requirement_id=rid, control_code=cc, mapping_type=mt,
            confidence=_AUTH_CONF.get(mt, 0.7),
            rationale=row.get("rationale", "Expert-curated mapping."),
            proposed_by="HUMAN", state="EXPERT_REVIEWED", mapping_source="expert_curated",
            mapping_version="1.0", legal_review_status="NOT_REVIEWED",
            expert_reviewed_by=reviewer,
            expert_reviewed_at=datetime.now(timezone.utc),
            last_reviewed_at=datetime.now(timezone.utc),
        ))
        existing.add((rid, cc))
        created += 1
    await db.commit()
    return {"created": created, "resolved": resolved, "unresolved": unresolved,
            "unresolved_keys": unresolved_keys, "reviewer": reviewer, "review_date": review_date}
