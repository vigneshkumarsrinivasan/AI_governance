"""
Crosswalk and Compliance Knowledge Graph Service.
Manages authoritative framework catalogs, unified control library,
and cross-framework mappings.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FRAMEWORKS_DIR = DATA_DIR / "frameworks"

class CrosswalkService:
    def __init__(self):
        self._frameworks_cache: Dict[str, Any] = {}
        self._controls_cache: List[Dict[str, Any]] = []
        self._crosswalk_cache: List[Dict[str, Any]] = []
        self._load_data()

    def _load_data(self):
        # Load Frameworks
        if FRAMEWORKS_DIR.exists():
            for fw_file in FRAMEWORKS_DIR.glob("*.json"):
                try:
                    with open(fw_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self._frameworks_cache[data["id"]] = data
                except Exception as e:
                    print(f"Error loading framework {fw_file}: {e}")

        # Load Unified Controls
        controls_file = DATA_DIR / "unified_controls.json"
        if controls_file.exists():
            with open(controls_file, "r", encoding="utf-8") as f:
                self._controls_cache = json.load(f)

        # Load Crosswalk Mappings
        crosswalk_file = DATA_DIR / "crosswalk_mappings.json"
        if crosswalk_file.exists():
            with open(crosswalk_file, "r", encoding="utf-8") as f:
                self._crosswalk_cache = json.load(f)

    def get_frameworks_summary(self) -> List[Dict[str, Any]]:
        summaries = []
        for fw in self._frameworks_cache.values():
            req_count = 0
            for ch in fw.get("chapters", []):
                req_count += len(ch.get("requirements", []))
            summaries.append({
                "id": fw["id"],
                "name": fw["name"],
                "short_name": fw["short_name"],
                "official_reference": fw["official_reference"],
                "jurisdiction": fw["jurisdiction"],
                "type": fw["type"],
                "version": fw["version"],
                "publication_date": fw["publication_date"],
                "effective_date": fw["effective_date"],
                "official_url": fw["official_url"],
                "status": fw["status"],
                "description": fw["description"],
                "requirement_count": req_count
            })
        return summaries

    def get_framework(self, framework_id: str) -> Optional[Dict[str, Any]]:
        return self._frameworks_cache.get(framework_id)

    def get_all_frameworks_raw(self) -> List[Dict[str, Any]]:
        """Full framework documents (chapters/requirements included), for graph traversal queries."""
        return list(self._frameworks_cache.values())

    def get_unified_controls(self) -> List[Dict[str, Any]]:
        return self._controls_cache

    def get_crosswalk_matrix(self) -> List[Dict[str, Any]]:
        """
        Builds matrix joining Unified Controls with their mappings across all 17 frameworks.
        """
        mapping_dict = {item["control_id"]: item["mappings"] for item in self._crosswalk_cache}
        matrix = []

        for ctrl in self._controls_cache:
            ctrl_id = ctrl["id"]
            raw_mappings = mapping_dict.get(ctrl_id, [])
            enriched_mappings = []

            for m in raw_mappings:
                fw = self._frameworks_cache.get(m["framework_id"])
                fw_name = fw["short_name"] if fw else m["framework_id"]
                
                # Locate requirement metadata
                article = ""
                req_title = ""
                if fw:
                    for ch in fw.get("chapters", []):
                        for req in ch.get("requirements", []):
                            if req["id"] == m["requirement_id"]:
                                article = req.get("article", "")
                                req_title = req.get("title", "")
                                break

                enriched_mappings.append({
                    "framework_id": m["framework_id"],
                    "framework_name": fw_name,
                    "requirement_id": m["requirement_id"],
                    "article": article,
                    "requirement_title": req_title,
                    "confidence": m.get("confidence", "Strong"),
                    "rationale": m.get("rationale", "")
                })

            matrix.append({
                "control_id": ctrl["id"],
                "control_code": ctrl["code"],
                "control_title": ctrl["title"],
                "domain": ctrl["domain"],
                "mappings": enriched_mappings
            })

        return matrix

    def resolve_evidence_coverage(self, control_ids: List[str]) -> Dict[str, Any]:
        """
        Calculates all frameworks, chapters, and requirements satisfied
        when one piece of evidence is linked to a set of control IDs.
        """
        satisfied_requirements = []
        framework_ids = set()

        mapping_dict = {item["control_id"]: item["mappings"] for item in self._crosswalk_cache}
        for cid in control_ids:
            mappings = mapping_dict.get(cid, [])
            for m in mappings:
                framework_ids.add(m["framework_id"])
                fw = self._frameworks_cache.get(m["framework_id"])
                fw_name = fw["short_name"] if fw else m["framework_id"]
                satisfied_requirements.append({
                    "framework_id": m["framework_id"],
                    "framework_name": fw_name,
                    "requirement_id": m["requirement_id"],
                    "confidence": m.get("confidence", "Strong"),
                    "control_id": cid
                })

        return {
            "satisfied_frameworks_count": len(framework_ids),
            "satisfied_framework_ids": list(framework_ids),
            "satisfied_requirements_count": len(satisfied_requirements),
            "satisfied_requirements": satisfied_requirements
        }

crosswalk_service = CrosswalkService()
