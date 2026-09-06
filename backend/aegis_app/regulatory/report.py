"""Framework validation & production-readiness reporting (spec sections 57, 92)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from aegis_app.regulatory.manifest import all_frameworks
from aegis_app.models.regulatory import (
    FrameworkVersion, FrameworkNode, RegulatoryRequirement, RegulatorySource,
    SourceArtifact, FrameworkValidation, RequirementControlMapping, ApplicabilityRule,
)


def _latest_version(session: Session, framework_key: str) -> FrameworkVersion | None:
    return session.execute(
        select(FrameworkVersion).where(FrameworkVersion.framework_key == framework_key)
        .order_by(FrameworkVersion.created_at.desc())
    ).scalars().first()


def framework_reconciliation(session: Session, fv: FrameworkVersion) -> Dict[str, Any]:
    nodes = session.execute(
        select(FrameworkNode).where(FrameworkNode.framework_version_id == fv.id)
    ).scalars().all()
    reqs = session.execute(
        select(RegulatoryRequirement).where(RegulatoryRequirement.framework_version_id == fv.id)
    ).scalars().all()
    artifact = session.execute(
        select(SourceArtifact).join(RegulatorySource)
        .where(RegulatorySource.framework_key == fv.framework_key)
        .order_by(SourceArtifact.retrieved_at.desc())
    ).scalars().first()
    checks = session.execute(
        select(FrameworkValidation).where(FrameworkValidation.framework_version_id == fv.id)
    ).scalars().all()
    latest_run = max((c.run_id for c in checks), default=None)
    checks = [c for c in checks if c.run_id == latest_run]

    return {
        "official_node_count": fv.expected_counts.get("hierarchy_nodes"),
        "ingested_node_count": len(nodes),
        "official_requirement_count": fv.expected_counts.get("requirements"),
        "ingested_requirement_count": len(reqs),
        "verified_requirement_count": sum(1 for r in reqs if r.review_status in ("VERIFIED", "APPROVED")),
        "source_sha256": artifact.sha256 if artifact else None,
        "source_retrieved_at": artifact.retrieved_at.isoformat() if artifact else None,
        "source_url": artifact.retrieved_url if artifact else None,
        "validation_failures": [
            {"layer": c.layer, "check": c.check_key, "severity": c.severity, "detail": c.detail}
            for c in checks if c.status == "FAIL"
        ],
        "validation_warnings": [c.check_key for c in checks if c.status == "FAIL" and c.severity == "WARNING"],
        "expected_counts": fv.expected_counts,
        "ingested_counts": fv.ingested_counts,
    }


def build_readiness_report(session: Session) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for fw in all_frameworks():
        key = fw["framework_key"]
        lic = fw.get("licence", {})
        fv = _latest_version(session, key)
        entry: Dict[str, Any] = {
            "framework": fw["framework_name"],
            "framework_key": key,
            "authority": fw["authority"],
            "jurisdiction": fw["jurisdiction"],
            "version": fw["version_label"],
            "canonical_identifier": fw.get("canonical_identifier"),
            "official_source": fw["documents"][0]["official_url"],
            "licence": lic.get("licence_name"),
            "licence_status": lic.get("licence_status"),
            "attribution": lic.get("attribution_statement"),
            "manifest_ingestion_status": fw.get("ingestion_status"),
            "publication_date": fw.get("publication_date"),
        }
        if not fv:
            entry.update({
                "production_status": "NOT_INGESTED",
                "requirements": 0, "hierarchy_nodes": 0,
                "coverage": {}, "blocking_reasons": ["not ingested"],
                "required_source_for_next_step": fw["documents"][0].get("machine_readable_url")
                or fw["documents"][0]["official_url"],
            })
        else:
            recon = framework_reconciliation(session, fv)
            n_map = session.execute(
                select(RequirementControlMapping).join(RegulatoryRequirement)
                .where(RegulatoryRequirement.framework_version_id == fv.id)
            ).scalars().all()
            n_rules = session.execute(
                select(ApplicabilityRule).where(ApplicabilityRule.framework_version_id == fv.id)
            ).scalars().all()
            entry.update({
                "production_status": fv.validation_status,
                "published_status": fv.published_status,
                "version_ingested": fv.version_label,
                "source_sha256": recon["source_sha256"],
                "source_retrieved_at": recon["source_retrieved_at"],
                "hierarchy_nodes": recon["ingested_node_count"],
                "requirements": recon["ingested_requirement_count"],
                "verified_requirements": recon["verified_requirement_count"],
                "control_mappings": len(n_map),
                "applicability_rules": len(n_rules),
                "coverage": fv.coverage,
                "reconciliation": recon,
                "blocking_reasons": fv.blocking_reasons,
            })
        rows.append(entry)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frameworks_total": len(rows),
        "ingested": sum(1 for r in rows if r["production_status"] != "NOT_INGESTED"),
        "production_ready": sum(1 for r in rows if r["production_status"] == "PRODUCTION_READY"),
        "validated": sum(1 for r in rows if r["production_status"] == "VALIDATED"),
        "verified": sum(1 for r in rows if r["production_status"] == "VERIFIED"),
        "partial": sum(1 for r in rows if r["production_status"] == "PARTIAL"),
        "blocked_or_not_ingested": sum(1 for r in rows if r["production_status"] in ("NOT_INGESTED", "UNVERIFIED")),
        "licence_unknown": sum(1 for r in rows if r["licence_status"] == "UNKNOWN"),
    }
    return {"summary": summary, "frameworks": rows}
