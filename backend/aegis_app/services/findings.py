"""
Finding lifecycle helpers.

Findings can originate from many places (spec: assessment gap, failed control,
missing/rejected evidence, red-team, vendor assessment, runtime violation,
regulatory change, manual review). Rather than duplicating the "create a
Finding, don't double-create if one is already open for the same cause" logic
in each router, it lives here.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_app.models.models import Finding, AuditEvent

# default SLA windows by severity (days) - used when a caller does not set due_date
_SLA_DAYS = {"Critical": 7, "High": 30, "Medium": 90, "Low": 180}


async def open_finding_exists(db: AsyncSession, tenant_id: str, *, source: str,
                              control_id: Optional[str] = None, system_id: Optional[str] = None,
                              title: Optional[str] = None) -> Optional[Finding]:
    q = select(Finding).where(
        Finding.tenant_id == tenant_id,
        Finding.source == source,
        Finding.status.notin_(("Resolved", "Accepted Risk")),
    )
    if control_id is not None:
        q = q.where(Finding.control_id == control_id)
    if system_id is not None:
        q = q.where(Finding.system_id == system_id)
    if title is not None:
        q = q.where(Finding.title == title)
    return (await db.execute(q)).scalars().first()


async def create_finding(
    db: AsyncSession, *, tenant_id: str, organization_id: str, title: str,
    description: str = "", severity: str = "High", source: str = "Manual Review",
    system_id: Optional[str] = None, control_id: Optional[str] = None,
    risk_id: Optional[str] = None, due_date: Optional[datetime] = None,
    actor_id: Optional[str] = None, actor_email: str = "system@aegis",
    dedupe: bool = True,
) -> Finding:
    """Create a Finding (+ audit event). If ``dedupe`` and an open finding for
    the same (source, control_id, system_id) already exists, return it instead
    of creating a duplicate."""
    if dedupe:
        existing = await open_finding_exists(
            db, tenant_id, source=source, control_id=control_id, system_id=system_id
        )
        if existing:
            return existing

    if due_date is None:
        due_date = datetime.now(timezone.utc) + timedelta(days=_SLA_DAYS.get(severity, 30))

    finding = Finding(
        tenant_id=tenant_id, organization_id=organization_id,
        system_id=system_id, control_id=control_id, risk_id=risk_id,
        title=title, description=description or title, severity=severity,
        source=source, status="Open", due_date=due_date,
    )
    db.add(finding)
    await db.flush()
    db.add(AuditEvent(
        tenant_id=tenant_id, actor_id=actor_id, actor_email=actor_email,
        action="CREATE_FINDING", object_type="Finding", object_id=finding.id,
        changes={"title": title, "severity": severity, "source": source,
                 "control_id": control_id, "system_id": system_id},
    ))
    return finding
