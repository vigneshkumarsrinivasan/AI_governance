"""Load and query framework_manifest.yaml."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

MANIFEST_PATH = Path(__file__).with_name("framework_manifest.yaml")

_VALID_LICENCE_STATUS = {
    "VERIFIED_REUSABLE", "VERIFIED_WITH_ATTRIBUTION", "VERIFIED_SHARE_ALIKE",
    "SOURCE_ONLY_NO_REDISTRIBUTION", "CUSTOMER_LICENCE_REQUIRED", "UNKNOWN",
}
_VALID_INGESTION_STATUS = {
    "READY_MACHINE_READABLE", "READY_FIXTURE", "SOURCE_RETRIEVAL_BLOCKED", "METADATA_ONLY",
}


@functools.lru_cache(maxsize=1)
def load_manifest() -> Dict[str, Any]:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    _validate(data)
    return data


def _validate(data: Dict[str, Any]) -> None:
    seen = set()
    for fw in data.get("frameworks", []):
        key = fw.get("framework_key")
        if not key:
            raise ValueError("manifest: framework entry missing framework_key")
        if key in seen:
            raise ValueError(f"manifest: duplicate framework_key {key!r}")
        seen.add(key)
        lic = fw.get("licence", {})
        status = lic.get("licence_status")
        if status not in _VALID_LICENCE_STATUS:
            raise ValueError(f"manifest: {key} has invalid licence_status {status!r}")
        ing = fw.get("ingestion_status")
        if ing not in _VALID_INGESTION_STATUS:
            raise ValueError(f"manifest: {key} has invalid ingestion_status {ing!r}")
        if not fw.get("documents"):
            raise ValueError(f"manifest: {key} has no documents")


def all_frameworks() -> List[Dict[str, Any]]:
    return list(load_manifest().get("frameworks", []))


def get_framework(framework_key: str) -> Optional[Dict[str, Any]]:
    for fw in all_frameworks():
        if fw["framework_key"] == framework_key:
            return fw
    return None


def redistribution_allowed(framework_key: str) -> bool:
    """Whether the platform may reproduce full official source text for this framework."""
    fw = get_framework(framework_key)
    if not fw:
        return False
    status = fw["licence"]["licence_status"]
    return status in {"VERIFIED_REUSABLE", "VERIFIED_WITH_ATTRIBUTION", "VERIFIED_SHARE_ALIKE"}


def store_source_text(framework_key: str) -> bool:
    """Whether this deployment may persist verbatim official source text.

    True when the licence permits redistribution, OR when the operator has
    explicitly supplied their own obtained copy as the primary source
    (``operator_supplied_primary_source: true``) - in that case the text lives
    only in the operator's own instance and a licence review is still tracked as
    a blocker until confirmed.
    """
    fw = get_framework(framework_key)
    if not fw:
        return False
    if redistribution_allowed(framework_key):
        return True
    return bool(fw.get("operator_supplied_primary_source"))


def attribution_statement(framework_key: str) -> str:
    fw = get_framework(framework_key)
    if not fw:
        return ""
    return fw["licence"].get("attribution_statement", "") or ""
