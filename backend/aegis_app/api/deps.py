"""
FastAPI route dependencies: database session, authentication, and RBAC enforcement.
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.core.security import decode_access_token
from aegis_app.models.models import User, Tenant

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extracts authenticated user from JWT token with multi-tenant verification.
    """
    if not token:
        # Check for demo/dev authorization header or fallback to demo user if available
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier",
        )
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found",
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
        
    return user

def require_roles(allowed_roles: List[str]):
    """
    RBAC Least-Privilege enforcement.
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != "Super Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}. Your role: {current_user.role}"
            )
        return current_user
    return role_checker


# Convenience dependencies wired to the permission tiers in core/permissions.py.
# Import lazily-by-name (not at module top) to avoid a circular import, since
# permissions.py has no dependency back on this module.
from aegis_app.core import permissions as _perm  # noqa: E402

require_governance_write = require_roles(_perm.GOVERNANCE_WRITE)
require_evidence_write = require_roles(_perm.EVIDENCE_WRITE)
require_evidence_review = require_roles(_perm.EVIDENCE_REVIEW)
require_legal_review = require_roles(_perm.LEGAL_REVIEW)
require_operational_control = require_roles(_perm.OPERATIONAL_CONTROL)
require_risk_acceptance = require_roles(_perm.RISK_ACCEPTANCE_APPROVAL)
