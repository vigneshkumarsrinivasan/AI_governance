"""organization memberships (multi-company) + assessment approval workflow

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-08

Additive only:
  * organization_memberships               (new table)
  * assessments.approval_status / submitted_by / submitted_at /
    approved_by / approved_at / approval_notes   (new columns, safe defaults)

Backfills one membership per existing user for their current tenant so
company-switching works for the demo users out of the box. No data deleted.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "organization_memberships" not in insp.get_table_names():
        op.create_table(
            "organization_memberships",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("organization_id", sa.String(length=36), nullable=False),
            sa.Column("role", sa.String(length=50), nullable=False, server_default="Tenant Admin"),
            sa.Column("is_default", sa.Boolean(), server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"])
        op.create_index("ix_organization_memberships_tenant_id", "organization_memberships", ["tenant_id"])

        # Backfill: every existing user gets a default membership to their tenant.
        op.execute("""
            INSERT INTO organization_memberships (id, user_id, tenant_id, organization_id, role, is_default, created_at)
            SELECT
                lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' ||
                substr(lower(hex(randomblob(2))),2) || '-' ||
                substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' ||
                lower(hex(randomblob(6))),
                u.id, u.tenant_id,
                COALESCE(u.organization_id, (SELECT o.id FROM organizations o WHERE o.tenant_id = u.tenant_id LIMIT 1)),
                u.role, 1, CURRENT_TIMESTAMP
            FROM users u
            WHERE u.tenant_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM organization_memberships m WHERE m.user_id = u.id AND m.tenant_id = u.tenant_id)
        """)

    a_cols = {c["name"] for c in insp.get_columns("assessments")}
    for col, ddl in [
        ("approval_status", sa.Column("approval_status", sa.String(length=40), nullable=False, server_default="NOT_SUBMITTED")),
        ("submitted_by", sa.Column("submitted_by", sa.String(length=255), nullable=True)),
        ("submitted_at", sa.Column("submitted_at", sa.DateTime(), nullable=True)),
        ("approved_by", sa.Column("approved_by", sa.String(length=255), nullable=True)),
        ("approved_at", sa.Column("approved_at", sa.DateTime(), nullable=True)),
        ("approval_notes", sa.Column("approval_notes", sa.Text(), nullable=True)),
    ]:
        if col not in a_cols:
            op.add_column("assessments", ddl)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    a_cols = {c["name"] for c in insp.get_columns("assessments")}
    for col in ("approval_notes", "approved_at", "approved_by", "submitted_at", "submitted_by", "approval_status"):
        if col in a_cols:
            op.drop_column("assessments", col)
    if "organization_memberships" in insp.get_table_names():
        op.drop_index("ix_organization_memberships_tenant_id", table_name="organization_memberships")
        op.drop_index("ix_organization_memberships_user_id", table_name="organization_memberships")
        op.drop_table("organization_memberships")
