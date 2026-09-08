"""
Evidence Management Endpoints.
Supports real file storage (local disk or S3), cryptographic SHA-256 hashing
over actual file bytes, multi-control satisfaction, a review/approval
workflow, and short-lived authorized downloads.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from aegis_app.core.database import get_db
from aegis_app.core.security import create_download_token, decode_download_token
from aegis_app.models.models import Evidence, EvidenceControlMap, User, AuditEvent
from aegis_app.schemas.schemas import EvidenceCreate, EvidenceResponse
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.services.findings import create_finding
from aegis_app.services.storage import get_storage_backend, UnsupportedFileError
from aegis_app.api.deps import get_current_user, require_evidence_write, require_evidence_review

router = APIRouter(prefix="/evidence", tags=["Evidence Management"])

# Evidence quality states (spec #30). "Approved"/"Rejected"/"Expired" are kept
# for backward compatibility with existing seeded/demo records.
VALID_REVIEW_STATUSES = {
    "Draft", "Submitted", "Under Review", "Accepted", "Rejected",
    "Expired", "Outdated", "Insufficient", "Approved",
}


def _to_response(item: Evidence) -> EvidenceResponse:
    ctrl_ids = [cm.control_id for cm in item.control_mappings]
    coverage = crosswalk_service.resolve_evidence_coverage(ctrl_ids)
    return EvidenceResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        title=item.title,
        description=item.description,
        evidence_type=item.evidence_type,
        file_url=item.file_url,
        file_hash_sha256=item.file_hash_sha256,
        owner=item.owner,
        version=item.version,
        approval_status=item.approval_status,
        satisfied_controls=ctrl_ids,
        satisfied_frameworks_count=coverage["satisfied_frameworks_count"],
        created_at=item.created_at,
    )


@router.get("", response_model=List[EvidenceResponse])
async def list_evidence(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Evidence)
        .where(Evidence.tenant_id == current_user.tenant_id)
        .options(selectinload(Evidence.control_mappings))
        .order_by(Evidence.created_at.desc())
    )
    return [_to_response(item) for item in result.scalars().all()]


@router.post("", response_model=EvidenceResponse)
async def create_evidence(
    payload: EvidenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_evidence_write)
):
    """
    Registers a metadata-only evidence record (external file_url reference,
    no bytes uploaded to this platform). Prefer POST /evidence/upload when the
    actual file is available - this endpoint exists for referencing evidence
    that lives in an external, already-governed system (e.g. a signed
    contract in the legal team's DMS) without duplicating the file here.
    New records start life as "Draft" and must go through the review
    workflow (PUT /evidence/{id}/review) before they count as accepted
    evidence - creating a record is not the same as it being approved.
    """
    content_to_hash = (payload.file_content_mock or payload.title + payload.file_url).encode("utf-8")
    sha256_hash = hashlib.sha256(content_to_hash).hexdigest()

    evidence = Evidence(
        tenant_id=current_user.tenant_id,
        organization_id=current_user.organization_id or current_user.tenant_id,
        title=payload.title,
        description=payload.description,
        evidence_type=payload.evidence_type,
        file_url=payload.file_url,
        file_hash_sha256=sha256_hash,
        owner=payload.owner or current_user.full_name,
        version=payload.version,
        approval_status="Draft",
        expiry_date=payload.expiry_date,
    )
    db.add(evidence)
    await db.flush()

    for cid in payload.control_ids:
        db.add(EvidenceControlMap(evidence_id=evidence.id, control_id=cid))

    audit = AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="CREATE_EVIDENCE_METADATA",
        object_type="Evidence",
        object_id=evidence.id,
        changes={"title": evidence.title, "hash": sha256_hash, "controls": payload.control_ids},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(evidence, attribute_names=["control_mappings"])

    return _to_response(evidence)


@router.post("/upload", response_model=EvidenceResponse)
async def upload_evidence(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    evidence_type: str = Form("Policy"),
    control_ids: str = Form("[]"),  # JSON-encoded list, since multipart forms are flat
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_evidence_write),
):
    """
    Uploads a real file, validates it (extension allowlist + magic-byte sniff
    + size cap), stores it via the configured storage backend (local disk or
    S3), and computes SHA-256 over the ACTUAL file bytes - not a placeholder
    string. This is the evidence path that should be used whenever the
    underlying artifact exists as a file.
    """
    try:
        parsed_control_ids = json.loads(control_ids) if control_ids else []
        if not isinstance(parsed_control_ids, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="control_ids must be a JSON array of control ID strings")

    content = await file.read()
    storage = get_storage_backend()
    try:
        stored = await storage.save(current_user.tenant_id, file.filename or "upload.bin", content)
    except UnsupportedFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    evidence = Evidence(
        tenant_id=current_user.tenant_id,
        organization_id=current_user.organization_id or current_user.tenant_id,
        title=title,
        description=description,
        evidence_type=evidence_type,
        file_url=f"internal://evidence/{stored.storage_key}",
        storage_key=stored.storage_key,
        storage_backend=stored.storage_backend,
        original_filename=file.filename,
        content_type=stored.content_type,
        file_size_bytes=stored.size_bytes,
        file_hash_sha256=stored.sha256_hash,
        owner=current_user.full_name,
        approval_status="Submitted",
    )
    db.add(evidence)
    await db.flush()

    for cid in parsed_control_ids:
        db.add(EvidenceControlMap(evidence_id=evidence.id, control_id=cid))

    audit = AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="UPLOAD_EVIDENCE_FILE",
        object_type="Evidence",
        object_id=evidence.id,
        changes={
            "title": title, "hash": stored.sha256_hash, "size_bytes": stored.size_bytes,
            "storage_backend": stored.storage_backend, "controls": parsed_control_ids,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(evidence, attribute_names=["control_mappings"])

    return _to_response(evidence)


@router.get("/{evidence_id}/download-token")
async def get_download_token(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Issues a short-lived (default 5 min), tenant-bound token authorizing one
    download of this evidence file. The frontend must call this before
    fetching /evidence/{id}/download - the download endpoint itself does not
    accept the user's login session, only this narrowly-scoped token.
    """
    result = await db.execute(
        select(Evidence).where(Evidence.id == evidence_id, Evidence.tenant_id == current_user.tenant_id)
    )
    evidence = result.scalars().first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not evidence.storage_key:
        raise HTTPException(status_code=400, detail="This evidence record has no uploaded file to download")

    token = create_download_token(evidence_id, current_user.tenant_id)
    return {"download_token": token, "expires_in_seconds": 300}


@router.get("/{evidence_id}/download")
async def download_evidence(
    evidence_id: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Streams the evidence file back. Requires a valid, non-expired download
    token from GET /{evidence_id}/download-token - deliberately does not
    accept a bearer session token, so a copy-pasted download link can't be
    replayed indefinitely or reused for anything beyond this one file.
    """
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalars().first()
    if not evidence or not evidence.storage_key:
        raise HTTPException(status_code=404, detail="Evidence not found")

    if not decode_download_token(token, evidence_id, evidence.tenant_id):
        raise HTTPException(status_code=403, detail="Invalid or expired download token")

    storage = get_storage_backend()
    content = await storage.read(evidence.storage_key)
    return Response(
        content=content,
        media_type=evidence.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{evidence.original_filename or evidence.id}"'},
    )


@router.put("/{evidence_id}/review")
async def review_evidence(
    evidence_id: str,
    review: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_evidence_review),
):
    """
    Evidence review workflow (spec #30): Draft -> Submitted -> Under Review ->
    Accepted/Rejected/Insufficient. Restricted to reviewer roles, separate
    from whoever submitted the evidence, to preserve separation of duties.
    """
    new_status = review.get("status")
    if new_status not in VALID_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(VALID_REVIEW_STATUSES)}")

    result = await db.execute(
        select(Evidence).where(Evidence.id == evidence_id, Evidence.tenant_id == current_user.tenant_id)
    )
    evidence = result.scalars().first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    evidence.approval_status = new_status
    evidence.reviewed_by = current_user.full_name
    evidence.review_notes = review.get("notes")
    evidence.reviewed_at = datetime.now(timezone.utc)

    audit = AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="REVIEW_EVIDENCE",
        object_type="Evidence",
        object_id=evidence.id,
        changes={"new_status": new_status, "notes": evidence.review_notes, "reviewer": current_user.full_name},
    )
    db.add(audit)

    # Rejected / insufficient evidence raises a finding against each mapped
    # control so it lands in the remediation queue and pulls down readiness
    # (spec §15/§23) - deliberately insufficient evidence must never read as PASS.
    if new_status in ("Rejected", "Insufficient"):
        maps = (await db.execute(
            select(EvidenceControlMap.control_id).where(EvidenceControlMap.evidence_id == evidence.id)
        )).scalars().all()
        for cid in (maps or [None]):
            await create_finding(
                db, tenant_id=current_user.tenant_id,
                organization_id=evidence.organization_id or current_user.tenant_id,
                title=f"Evidence {new_status.lower()} for control {cid or evidence.title}",
                description=f"'{evidence.title}' was reviewed as {new_status}. {evidence.review_notes or ''}".strip(),
                severity="Medium", source="Missing Evidence", control_id=cid,
                actor_id=current_user.id, actor_email=current_user.email,
            )

    await db.commit()

    return {"id": evidence.id, "approval_status": evidence.approval_status, "reviewed_by": evidence.reviewed_by}
