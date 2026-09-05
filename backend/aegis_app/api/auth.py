"""
Authentication & RBAC endpoints: login, signup, me.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_app.core.database import get_db
from aegis_app.core.security import verify_password, get_password_hash, create_access_token
from aegis_app.core.permissions import SELF_SIGNUP_ALLOWED_ROLES
from aegis_app.models.models import User, Tenant, Organization
from aegis_app.schemas.schemas import Token, UserLogin, UserSignup, UserResponse
from aegis_app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_payload(user: User, organization_name: str = None, is_demo_tenant: bool = False) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "organization_id": user.organization_id,
        "organization_name": organization_name,
        "is_demo_tenant": is_demo_tenant,
    }


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalars().first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    org = None
    if user.organization_id:
        org_result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
        org = org_result.scalars().first()

    access_token = create_access_token(
        data={"sub": user.id, "tenant_id": user.tenant_id, "role": user.role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _user_payload(user, org.name if org else None, org.is_demo if org else False),
    }


@router.post("/signup", response_model=Token)
async def signup(payload: UserSignup, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists"
        )

    # Create tenant and organization
    tenant = Tenant(name=payload.organization_name)
    db.add(tenant)
    await db.flush()

    org = Organization(
        tenant_id=tenant.id,
        name=payload.organization_name,
        industry="Technology"
    )
    db.add(org)
    await db.flush()

    # Self-signup always creates the founding admin of a brand-new tenant.
    # The caller-supplied role is intentionally ignored for anything other than
    # the allowed self-signup roles - otherwise an unauthenticated caller could
    # mint themselves "Super Admin" or "Auditor" via the public signup endpoint.
    # Additional users/roles must be provisioned by a Tenant Admin after signup.
    signup_role = payload.role if payload.role in SELF_SIGNUP_ALLOWED_ROLES else SELF_SIGNUP_ALLOWED_ROLES[0]

    # Create user
    user = User(
        tenant_id=tenant.id,
        organization_id=org.id,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=signup_role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(
        data={"sub": user.id, "tenant_id": tenant.id, "role": user.role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _user_payload(user, org.name, org.is_demo),
    }


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = None
    if current_user.organization_id:
        org_result = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
        org = org_result.scalars().first()

    return UserResponse(
        id=current_user.id,
        tenant_id=current_user.tenant_id,
        organization_id=current_user.organization_id,
        organization_name=org.name if org else None,
        is_demo_tenant=org.is_demo if org else False,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
