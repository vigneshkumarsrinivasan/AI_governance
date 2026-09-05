"""
Compliance Audit Trail Endpoints.
Provides immutable, tamper-evident audit logs for all security and compliance actions.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.models.models import AuditEvent, User
from aegis_app.api.deps import get_current_user

router = APIRouter(prefix="/audit", tags=["Audit Trail"])

@router.get("", response_model=List[Dict[str, Any]])
async def list_audit_events(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.tenant_id == current_user.tenant_id)
        .order_by(AuditEvent.timestamp.desc())
        .limit(100)
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "actor_id": e.actor_id,
            "actor_email": e.actor_email,
            "action": e.action,
            "object_type": e.object_type,
            "object_id": e.object_id,
            "changes": e.changes or {},
            "ip_address": e.ip_address,
            "timestamp": e.timestamp
        }
        for e in events
    ]
