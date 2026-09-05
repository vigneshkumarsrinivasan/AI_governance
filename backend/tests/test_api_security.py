"""
Real HTTP-level integration and security tests against the FastAPI app
(as opposed to unit tests that call service functions directly). Covers:

  - login/signup happy path and failure modes
  - unauthenticated access is rejected
  - signup cannot self-assign a privileged role
  - RBAC: a read-only role is rejected from write endpoints; a privileged
    role is allowed
  - cross-tenant isolation through the actual API (not just an ORM query) -
    a user from Tenant A must not be able to read or modify Tenant B's
    AI system by ID
  - evidence upload/download requires a valid, tenant-bound download token
"""

import uuid
import pytest
from sqlalchemy import select

from aegis_app.core.database import AsyncSessionLocal
from aegis_app.core.security import get_password_hash
from aegis_app.models.models import User


async def _signup(client, org_name=None, email=None, password="StrongPass1!"):
    org_name = org_name or f"Test Org {uuid.uuid4().hex[:8]}"
    email = email or f"admin-{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": password,
        "full_name": "Test Admin",
        "organization_name": org_name,
        "role": "Super Admin",  # deliberately attempt privilege escalation - see test below
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _create_user_with_role(tenant_id: str, organization_id: str, role: str, email: str, password: str = "StrongPass1!"):
    async with AsyncSessionLocal() as session:
        user = User(
            tenant_id=tenant_id,
            organization_id=organization_id,
            email=email,
            hashed_password=get_password_hash(password),
            full_name=f"{role} Tester",
            role=role,
        )
        session.add(user)
        await session.commit()
    return email


@pytest.mark.asyncio
async def test_signup_login_and_me(client):
    signup = await _signup(client)
    assert signup["access_token"]
    # Privilege escalation attempt via signup role field must be ignored.
    assert signup["user"]["role"] == "Tenant Admin"

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {signup['access_token']}"})
    assert me.status_code == 200
    assert me.json()["role"] == "Tenant Admin"


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client):
    signup = await _signup(client, email=f"wrongpass-{uuid.uuid4().hex[:8]}@example.com")
    bad_login = await client.post("/api/v1/auth/login", json={
        "email": signup["user"]["email"], "password": "TotallyWrongPassword1!"
    })
    assert bad_login.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client):
    resp = await client.get("/api/v1/ai-systems")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_rbac_viewer_cannot_write_but_admin_can(client):
    signup = await _signup(client, email=f"admin-{uuid.uuid4().hex[:8]}@example.com")
    tenant_id = signup["user"]["tenant_id"]
    org_id = signup["user"]["organization_id"]
    admin_token = signup["access_token"]

    viewer_email = f"viewer-{uuid.uuid4().hex[:8]}@example.com"
    await _create_user_with_role(tenant_id, org_id, "Viewer", viewer_email)
    viewer_login = await client.post("/api/v1/auth/login", json={"email": viewer_email, "password": "StrongPass1!"})
    assert viewer_login.status_code == 200
    viewer_token = viewer_login.json()["access_token"]

    payload = {"name": "Viewer-Created System", "description": "should be rejected"}

    viewer_resp = await client.post(
        "/api/v1/ai-systems", json=payload, headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert viewer_resp.status_code == 403

    admin_resp = await client.post(
        "/api/v1/ai-systems", json=payload, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_resp.status_code == 200


@pytest.mark.asyncio
async def test_cross_tenant_isolation_via_api(client):
    """
    CRITICAL SECURITY TEST (spec #99): create two tenants through the real
    signup/login/API path, create an AI system as Tenant A, then attempt to
    read and modify it using a valid Tenant B token. Both must fail (404, not
    a data leak), proving tenant scoping holds at the HTTP layer - not just
    in a raw ORM query, which is all the previous version of this test
    actually checked.
    """
    tenant_a = await _signup(client, email=f"tenanta-{uuid.uuid4().hex[:8]}@example.com")
    tenant_b = await _signup(client, email=f"tenantb-{uuid.uuid4().hex[:8]}@example.com")

    create_resp = await client.post(
        "/api/v1/ai-systems",
        json={"name": "Tenant A Secret System", "description": "confidential"},
        headers={"Authorization": f"Bearer {tenant_a['access_token']}"},
    )
    assert create_resp.status_code == 200
    system_id = create_resp.json()["id"]

    # Tenant B must not be able to read it.
    get_as_b = await client.get(
        f"/api/v1/ai-systems/{system_id}", headers={"Authorization": f"Bearer {tenant_b['access_token']}"}
    )
    assert get_as_b.status_code == 404

    # Tenant B must not be able to modify it.
    put_as_b = await client.put(
        f"/api/v1/ai-systems/{system_id}",
        json={"name": "Hijacked"},
        headers={"Authorization": f"Bearer {tenant_b['access_token']}"},
    )
    assert put_as_b.status_code == 404

    # Tenant B's own list of AI systems must not include Tenant A's system.
    list_as_b = await client.get("/api/v1/ai-systems", headers={"Authorization": f"Bearer {tenant_b['access_token']}"})
    assert list_as_b.status_code == 200
    assert all(s["id"] != system_id for s in list_as_b.json())

    # Tenant A can still read its own system.
    get_as_a = await client.get(
        f"/api/v1/ai-systems/{system_id}", headers={"Authorization": f"Bearer {tenant_a['access_token']}"}
    )
    assert get_as_a.status_code == 200


@pytest.mark.asyncio
async def test_evidence_upload_download_requires_valid_token(client):
    signup = await _signup(client, email=f"evidence-{uuid.uuid4().hex[:8]}@example.com")
    token = signup["access_token"]

    files = {"file": ("policy.txt", b"Enterprise AI Policy v1", "text/plain")}
    data = {"title": "AI Policy", "evidence_type": "Policy", "control_ids": "[]"}
    upload = await client.post(
        "/api/v1/evidence/upload", data=data, files=files, headers={"Authorization": f"Bearer {token}"}
    )
    assert upload.status_code == 200, upload.text
    evidence_id = upload.json()["id"]

    # Downloading without a token must fail.
    no_token_dl = await client.get(f"/api/v1/evidence/{evidence_id}/download")
    assert no_token_dl.status_code in (400, 401, 422)

    # A garbage token must be rejected.
    bad_token_dl = await client.get(f"/api/v1/evidence/{evidence_id}/download", params={"token": "not-a-real-token"})
    assert bad_token_dl.status_code == 403

    # A real, tenant-bound token must succeed and return the exact bytes uploaded.
    token_resp = await client.get(
        f"/api/v1/evidence/{evidence_id}/download-token", headers={"Authorization": f"Bearer {token}"}
    )
    assert token_resp.status_code == 200
    dl_token = token_resp.json()["download_token"]

    good_dl = await client.get(f"/api/v1/evidence/{evidence_id}/download", params={"token": dl_token})
    assert good_dl.status_code == 200
    assert good_dl.content == b"Enterprise AI Policy v1"


@pytest.mark.asyncio
async def test_evidence_upload_rejects_disallowed_file_type(client):
    signup = await _signup(client, email=f"badfile-{uuid.uuid4().hex[:8]}@example.com")
    token = signup["access_token"]

    files = {"file": ("malware.exe", b"MZ\x90\x00fake-binary-content", "application/octet-stream")}
    data = {"title": "Suspicious File", "evidence_type": "Policy", "control_ids": "[]"}
    resp = await client.post(
        "/api/v1/evidence/upload", data=data, files=files, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400
