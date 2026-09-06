"""Inventory + hash every operator-supplied regulatory document in the workspace
and emit regulatory-data/manifests/regulatory-source-manifest.yaml (spec #1, #13).

The source folder is treated as immutable input - nothing here writes to it.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

from aegis_app.regulatory.manifest import all_frameworks

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "regulatory-data" / "manifests"
DOC_EXTS = {".pdf", ".docx", ".doc", ".xml", ".xlsx", ".csv", ".json", ".yaml", ".yml", ".html", ".txt", ".zip"}

# filename fragment -> framework_key
_MATCH = [
    (r"eu ai act|32024r1689|artificial intelligence act", "eu_ai_act"),
    (r"\bgdpr\b|32016r0679", "gdpr"),
    (r"\bcra\b|cyber resilience|32024r2847", "eu_cra"),
    (r"\bnis2\b|nis 2|32022l2555", "nis2"),
    (r"\bdora\b|32022r2554|digital operational resilience", "dora"),
    (r"ai\.100-1|ai rmf|ai_rmf", "nist_ai_rmf"),
    (r"ai\.600-1|generative ai profile", "nist_ai_600_1"),
    (r"cswp\.29|cybersecurity framework|csf 2", "nist_csf_2"),
    (r"800-53", "nist_sp_800_53"),
    (r"800-218a", "nist_sp_800_218a"),
    (r"800-218", "nist_sp_800_218"),
    (r"800-161", "nist_sp_800_161"),
    (r"llm.?top.?10|llm-top-10|top-10-for-large-language", "owasp_llm"),
    (r"agentic", "owasp_agentic_ai"),
    (r"atlas", "mitre_atlas"),
    (r"ai cyber security code|ai_cyber_security_code|cyber security of ai", "uk_ai_cyber_code"),
    (r"dpdp.?rules|dpdp_rules", "india_dpdp"),
    (r"dpdp.?act", "india_dpdp"),
    (r"ai verify|aiverify", "singapore_ai_verify"),
]

_AUTH = {
    "eu_ai_act": "European Union", "gdpr": "European Union", "eu_cra": "European Union",
    "nis2": "European Union", "dora": "European Union",
    "nist_ai_rmf": "NIST", "nist_ai_600_1": "NIST", "nist_csf_2": "NIST",
    "nist_sp_800_53": "NIST", "nist_sp_800_218": "NIST", "nist_sp_800_218a": "NIST",
    "nist_sp_800_161": "NIST",
    "owasp_llm": "OWASP Foundation", "owasp_agentic_ai": "OWASP Foundation",
    "mitre_atlas": "The MITRE Corporation", "uk_ai_cyber_code": "UK DSIT",
    "india_dpdp": "Government of India (MeitY)", "singapore_ai_verify": "AI Verify Foundation / IMDA",
}


def _classify(name: str) -> str:
    low = name.lower()
    for pat, key in _MATCH:
        if re.search(pat, low):
            return key
    return "UNIDENTIFIED"


_DOC_EXTS_STRICT = {".pdf", ".docx", ".doc", ".xml", ".xlsx"}


def scan(root: Path = REPO_ROOT) -> List[Dict[str, Any]]:
    """Operator-supplied regulatory documents live at the workspace root
    (spec: 'AI governance folder is same where all the frontend and backend code
    are'). We inventory root-level document files only - not source trees."""
    out: List[Dict[str, Any]] = []
    for p in sorted(root.glob("*")):
        if not p.is_file() or p.suffix.lower() not in _DOC_EXTS_STRICT:
            continue
        raw = p.read_bytes()
        fk = _classify(p.name)
        fw = next((f for f in all_frameworks() if f["framework_key"] == fk), None)
        out.append({
            "filename": p.name,
            "local_path": str(p.relative_to(root)),
            "extension": p.suffix.lower().lstrip("."),
            "size_bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "detected_framework": fk,
            "authority": _AUTH.get(fk),
            "manifest_version": (fw or {}).get("version_label"),
            "manifest_licence_status": ((fw or {}).get("licence") or {}).get("licence_status"),
            "manifest_parser": (fw or {}).get("parser"),
            "manifest_ingestion_status": (fw or {}).get("ingestion_status"),
        })
    return out


def build_manifest(root: Path = REPO_ROOT) -> Dict[str, Any]:
    docs = scan(root)
    by_fw: Dict[str, List[str]] = {}
    for d in docs:
        by_fw.setdefault(d["detected_framework"], []).append(d["filename"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(root),
        "note": "Operator-supplied source documents are immutable input. Hashes recorded "
                "here are reconciled by the ingestion pipeline; each ingested framework also "
                "stores its own SourceArtifact (URL/hash/timestamp) in the database.",
        "documents_found": len(docs),
        "unidentified": [d["filename"] for d in docs if d["detected_framework"] == "UNIDENTIFIED"],
        "by_framework": {k: sorted(v) for k, v in sorted(by_fw.items())},
        "documents": docs,
    }


def write_manifest(root: Path = REPO_ROOT) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    man = build_manifest(root)
    path = OUT_DIR / "regulatory-source-manifest.yaml"
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(man, fh, sort_keys=False, allow_unicode=True, width=100)
    return path
