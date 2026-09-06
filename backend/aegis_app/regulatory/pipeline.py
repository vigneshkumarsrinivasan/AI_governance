"""End-to-end ingestion pipeline: fetch -> archive -> hash -> parse -> persist -> validate."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from aegis_app.regulatory import PARSER_VERSION
from aegis_app.regulatory import fetch as fetchmod
from aegis_app.regulatory.manifest import get_framework
from aegis_app.regulatory.parsers import get_parser, parser_available
from aegis_app.regulatory.loader import persist, ImmutableVersionError
from aegis_app.regulatory.validate import validate_framework_version
from aegis_app.models.regulatory import (
    RegulatorySource, SourceArtifact, IngestionRun, SourceChangeEvent,
)

ARCHIVE_DIR = Path(__file__).with_name("sources_archive")
FIXTURE_DIR = Path(__file__).with_name("fixtures")
REPO_ROOT = Path(__file__).resolve().parents[3]  # backend/aegis_app/regulatory -> repo root
_EXT = {"oscal_json": "json", "json": "json", "yaml": "yaml", "formex_xml": "xml",
        "akoma_ntoso": "xml", "markdown": "json", "html": "html", "pdf": "pdf",
        "docx": "docx"}


def _now():
    return datetime.now(timezone.utc)


def _archive(framework_key: str, content: bytes, ext: str) -> tuple[str, Path]:
    sha = hashlib.sha256(content).hexdigest()
    d = ARCHIVE_DIR / framework_key
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{sha[:16]}.{ext}"
    if not path.exists():
        path.write_bytes(content)
    return sha, path


def _do_fetch(doc: Dict[str, Any], framework_key: str) -> fetchmod.FetchResult:
    retr = doc.get("retrieval") or {"mode": "single"}
    mode = retr.get("mode", "single")
    if mode == "fixture":
        fpath = FIXTURE_DIR / retr["fixture_file"]
        content = fpath.read_bytes()
        return fetchmod.FetchResult(content=content, retrieved_url=f"fixture://{retr['fixture_file']}",
                                    mime_type="application/json", file_name=retr["fixture_file"], mode="fixture")
    if mode == "local_file":
        p = Path(retr["path"])
        if not p.is_absolute():
            p = REPO_ROOT / retr["path"]
        if not p.exists():
            raise FileNotFoundError(f"local source not found: {p} (SOURCE_RETRIEVAL_BLOCKED)")
        return fetchmod.FetchResult(content=p.read_bytes(), retrieved_url=f"local://{p.name}",
                                    mime_type="application/octet-stream", file_name=p.name, mode="local")
    if mode == "github_release":
        return fetchmod.fetch_github_release_asset(retr["repo"], retr["asset_glob"])
    if mode == "github_bundle":
        return fetchmod.fetch_github_bundle(retr["repo"], retr.get("ref_mode", "main"),
                                            retr["path_prefix"], retr["files"])
    if mode == "bundle":
        base = retr["base_url"]
        files = [{"name": f, "url": base + f} for f in retr["files"]]
        return fetchmod.fetch_bundle(files)
    if mode == "cprt":
        return fetchmod.fetch_cprt(retr["framework_version_identifier"], retr.get("deep_from_type", "category"))
    url = doc.get("machine_readable_url") or doc.get("official_url")
    return fetchmod.fetch_single(url)


def _upsert_source(session: Session, manifest_entry: Dict[str, Any], doc: Dict[str, Any]) -> RegulatorySource:
    fk = manifest_entry["framework_key"]
    dk = doc["document_key"]
    src = session.execute(
        select(RegulatorySource).where(RegulatorySource.framework_key == fk,
                                       RegulatorySource.document_key == dk)
    ).scalar_one_or_none()
    lic = manifest_entry.get("licence", {})
    fields = dict(
        framework_key=fk, framework_family=manifest_entry["framework_family"], document_key=dk,
        document_name=doc["document_name"], authority=manifest_entry["authority"],
        jurisdiction=manifest_entry["jurisdiction"], document_type=manifest_entry["framework_type"],
        canonical_identifier=manifest_entry.get("canonical_identifier"),
        official_url=doc["official_url"], machine_readable_url=doc.get("machine_readable_url"),
        source_format=doc.get("source_format", "unknown"),
        copyright_owner=lic.get("copyright_owner"), licence_name=lic.get("licence_name"),
        licence_url=lic.get("licence_url"),
        commercial_reuse_allowed=lic.get("commercial_reuse_allowed"),
        redistribution_allowed=lic.get("redistribution_allowed"),
        modification_allowed=lic.get("modification_allowed"),
        attribution_required=lic.get("attribution_required"),
        share_alike_required=lic.get("share_alike_required"),
        third_party_material_present=bool(lic.get("third_party_material_present")),
        licence_status=lic.get("licence_status", "UNKNOWN"),
        licence_verified_at=_now() if lic.get("licence_status") not in (None, "UNKNOWN") else None,
        licence_evidence_url=lic.get("licence_url"),
        attribution_statement=lic.get("attribution_statement"),
        publication_date=manifest_entry.get("publication_date"),
        effective_date=manifest_entry.get("effective_date"),
        application_dates=manifest_entry.get("application_dates", {}),
        notes=manifest_entry.get("notes"),
    )
    if src:
        for k, v in fields.items():
            setattr(src, k, v)
    else:
        src = RegulatorySource(**fields)
        session.add(src)
    session.flush()
    return src


def ingest_framework(session: Session, framework_key: str, *, allow_blocked: bool = False) -> Dict[str, Any]:
    manifest_entry = get_framework(framework_key)
    if not manifest_entry:
        raise KeyError(f"{framework_key!r} not in framework_manifest.yaml")

    run = IngestionRun(framework_key=framework_key, mode="live", pipeline_stage="fetch", status="RUNNING",
                       parser_version=PARSER_VERSION, log=[])
    session.add(run)
    session.flush()

    def log(stage, level, msg):
        run.log = (run.log or []) + [{"stage": stage, "level": level, "message": msg, "ts": _now().isoformat()}]
        run.pipeline_stage = stage

    ingestion_status = manifest_entry.get("ingestion_status")
    parser_name = manifest_entry.get("parser")
    if ingestion_status in ("SOURCE_RETRIEVAL_BLOCKED", "METADATA_ONLY") or not parser_available(parser_name or ""):
        run.status = "BLOCKED"
        run.finished_at = _now()
        log("fetch", "warning",
            f"ingestion_status={ingestion_status}; parser_available={parser_available(parser_name or '')}. "
            f"Recording source/licence metadata only - no provisions ingested.")
        doc = next((d for d in manifest_entry["documents"]
                    if (d.get("retrieval") or {}).get("mode") == "local_file"),
                   manifest_entry["documents"][0])
        src = _upsert_source(session, manifest_entry, doc)
        archived = None
        # still archive + hash an operator-supplied local file so it is inventoried
        if (doc.get("retrieval") or {}).get("mode") == "local_file":
            try:
                fr = _do_fetch(doc, framework_key)
                sha, path = _archive(framework_key, fr.content,
                                     _EXT.get(doc.get("source_format", ""), "bin"))
                session.add(SourceArtifact(
                    source_id=src.id, retrieved_url=fr.retrieved_url, retrieved_at=_now(),
                    mime_type=fr.mime_type, file_name=fr.file_name, byte_size=len(fr.content),
                    sha256=sha, storage_path=str(path), parser_version=PARSER_VERSION,
                    retrieval_status="RETRIEVED", fixture_backed=False))
                archived = {"sha256": sha, "archive_path": str(path)}
                log("archive", "info", f"archived operator source sha256={sha[:16]} (parser pending)")
            except Exception as e:  # noqa: BLE001
                log("archive", "warning", f"could not archive local source: {e}")
        session.flush()
        return {"framework_key": framework_key, "status": "BLOCKED",
                "reason": f"ingestion_status={ingestion_status}; parser={parser_name} "
                          f"available={parser_available(parser_name or '')}",
                "required_source": doc.get("official_url"),
                "archived_source": archived, "run_id": run.id}

    doc = next((d for d in manifest_entry["documents"] if d.get("retrieval") or d.get("machine_readable_url")),
               manifest_entry["documents"][0])
    src = _upsert_source(session, manifest_entry, doc)

    try:
        log("fetch", "info", f"retrieving via {(doc.get('retrieval') or {}).get('mode', 'single')}")
        fr = _do_fetch(doc, framework_key)
    except Exception as e:  # noqa: BLE001
        run.status = "FAILED"
        run.error = f"{type(e).__name__}: {e}"
        run.finished_at = _now()
        log("fetch", "error", run.error)
        return {"framework_key": framework_key, "status": "SOURCE_RETRIEVAL_BLOCKED", "error": run.error,
                "required_source": doc.get("machine_readable_url") or doc.get("official_url"), "run_id": run.id}

    ext = _EXT.get(doc.get("source_format", ""), "bin")
    if fr.mode in ("bundle", "cprt", "fixture"):
        ext = "json"
    sha, path = _archive(framework_key, fr.content, ext)
    log("archive", "info", f"archived {len(fr.content)} bytes sha256={sha[:16]}... -> {path.name}")

    prev = session.execute(
        select(SourceArtifact).where(SourceArtifact.source_id == src.id)
        .order_by(SourceArtifact.retrieved_at.desc())
    ).scalars().first()
    prev_sha = prev.sha256 if prev else None
    if prev_sha and prev_sha != sha:
        session.add(SourceChangeEvent(source_id=src.id, previous_sha256=prev_sha, new_sha256=sha,
                                      previous_artifact_id=prev.id,
                                      change_kind="REGULATORY_SOURCE_CHANGE_DETECTED"))
        log("hash", "warning", f"source hash changed vs previous artifact ({prev_sha[:12]} -> {sha[:12]}); "
                               f"change event raised - not auto-publishing.")

    artifact = SourceArtifact(
        source_id=src.id, retrieved_url=fr.retrieved_url, retrieved_at=_now(),
        http_status=fr.http_status, http_headers=fr.headers, mime_type=fr.mime_type,
        file_name=fr.file_name, byte_size=len(fr.content), sha256=sha, previous_sha256=prev_sha,
        storage_path=str(path), parser_version=PARSER_VERSION,
        retrieval_status="HASH_CHANGED" if (prev_sha and prev_sha != sha) else "RETRIEVED",
        fixture_backed=(fr.mode == "fixture"),
    )
    session.add(artifact)
    session.flush()

    log("parse", "info", f"parser={parser_name}")
    parse = get_parser(parser_name)
    pf = parse(fr.content, manifest_entry)
    problems = pf.sanity_check()
    for p in problems:
        log("parse", "warning", f"sanity: {p}")
    for note in pf.parser_notes:
        log("parse", "info", note)

    try:
        fv = persist(session, pf, source=src, artifact=artifact, manifest_entry=manifest_entry)
    except ImmutableVersionError as e:
        run.status = "FAILED"
        run.error = str(e)
        run.finished_at = _now()
        log("persist", "error", str(e))
        return {"framework_key": framework_key, "status": "IMMUTABLE", "error": str(e), "run_id": run.id}

    log("validate", "info", "running 3-layer validation")
    report = validate_framework_version(session, fv)
    fv.published_status = "DRAFT"
    run.framework_version_id = fv.id
    run.status = "SUCCESS"
    run.finished_at = _now()
    log("validate", "info", f"status={report['status']} coverage={report['coverage']}")

    return {
        "framework_key": framework_key,
        "version_label": fv.version_label,
        "status": report["status"],
        "coverage": report["coverage"],
        "counts": report["counts"],
        "expected_counts": fv.expected_counts,
        "critical_failures": report["critical_failures"],
        "error_failures": report["error_failures"],
        "blocking_reasons": report["blocking_reasons"],
        "sanity_problems": problems,
        "source_sha256": sha,
        "archive_path": str(path),
        "run_id": run.id,
    }


def ingest_all(session: Session) -> Dict[str, Any]:
    from aegis_app.regulatory.manifest import all_frameworks
    out = {}
    for fw in all_frameworks():
        try:
            out[fw["framework_key"]] = ingest_framework(session, fw["framework_key"])
        except Exception as e:  # noqa: BLE001
            out[fw["framework_key"]] = {"status": "ERROR", "error": f"{type(e).__name__}: {e}"}
    return out
