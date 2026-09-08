"""SME onboarding profile, company applicability scope, UI mode

Revision ID: a1b2c3d4e5f6
Revises: 36606e944171
Create Date: 2026-09-08

Purely additive:
  * users.ui_mode                          (default 'advanced' - existing users unchanged)
  * organization_profiles                  (new table, 1:1 with organizations)
  * applicability_decisions.scope          (default 'system' - existing rows unchanged)
  * applicability_decisions.framework_exposure / open_questions (nullable JSON)

No existing column is dropped or retyped. No data is deleted.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "36606e944171"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    user_cols = {c["name"] for c in insp.get_columns("users")}
    if "ui_mode" not in user_cols:
        op.add_column(
            "users",
            sa.Column("ui_mode", sa.String(length=20), nullable=False, server_default="advanced"),
        )

    ad_cols = {c["name"] for c in insp.get_columns("applicability_decisions")}
    if "scope" not in ad_cols:
        op.add_column(
            "applicability_decisions",
            sa.Column("scope", sa.String(length=20), nullable=False, server_default="system"),
        )
    if "framework_exposure" not in ad_cols:
        op.add_column("applicability_decisions", sa.Column("framework_exposure", sa.JSON(), nullable=True))
    if "open_questions" not in ad_cols:
        op.add_column("applicability_decisions", sa.Column("open_questions", sa.JSON(), nullable=True))

    if "organization_profiles" not in insp.get_table_names():
        op.create_table(
            "organization_profiles",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("organization_id", sa.String(length=36), nullable=False),
            sa.Column("answers", sa.JSON(), nullable=True),
            sa.Column("headquarters_country", sa.String(length=8), nullable=True),
            sa.Column("operating_countries", sa.JSON(), nullable=True),
            sa.Column("employee_count", sa.Integer(), nullable=True),
            sa.Column("industry", sa.String(length=80), nullable=True),
            sa.Column("sells_to_enterprises", sa.Boolean(), nullable=True),
            sa.Column("sells_to_government", sa.Boolean(), nullable=True),
            sa.Column("sells_to_financial_institutions", sa.Boolean(), nullable=True),
            sa.Column("sells_to_healthcare", sa.Boolean(), nullable=True),
            sa.Column("develops_ai_products", sa.Boolean(), nullable=True),
            sa.Column("deploys_ai_internally", sa.Boolean(), nullable=True),
            sa.Column("uses_generative_ai", sa.Boolean(), nullable=True),
            sa.Column("builds_ai_agents", sa.Boolean(), nullable=True),
            sa.Column("uses_rag", sa.Boolean(), nullable=True),
            sa.Column("uses_third_party_models", sa.Boolean(), nullable=True),
            sa.Column("makes_decisions_about_people", sa.Boolean(), nullable=True),
            sa.Column("decision_domains", sa.JSON(), nullable=True),
            sa.Column("uses_biometrics", sa.Boolean(), nullable=True),
            sa.Column("ai_providers", sa.JSON(), nullable=True),
            sa.Column("data_types", sa.JSON(), nullable=True),
            sa.Column("sells_software", sa.Boolean(), nullable=True),
            sa.Column("is_saas", sa.Boolean(), nullable=True),
            sa.Column("sells_connected_hardware", sa.Boolean(), nullable=True),
            sa.Column("is_iot", sa.Boolean(), nullable=True),
            sa.Column("has_embedded_software", sa.Boolean(), nullable=True),
            sa.Column("is_cybersecurity_product", sa.Boolean(), nullable=True),
            sa.Column("product_marketed_in_eu", sa.Boolean(), nullable=True),
            sa.Column("soc2_required", sa.Boolean(), nullable=True),
            sa.Column("iso27001_required", sa.Boolean(), nullable=True),
            sa.Column("gets_security_questionnaires", sa.Boolean(), nullable=True),
            sa.Column("existing_certifications", sa.JSON(), nullable=True),
            sa.Column("has_compliance_staff", sa.Boolean(), nullable=True),
            sa.Column("has_security_staff", sa.Boolean(), nullable=True),
            sa.Column("starter_pack", sa.String(length=40), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id"),
        )
        op.create_index("ix_organization_profiles_tenant_id", "organization_profiles", ["tenant_id"])
        op.create_index("ix_organization_profiles_organization_id", "organization_profiles", ["organization_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "organization_profiles" in insp.get_table_names():
        op.drop_index("ix_organization_profiles_organization_id", table_name="organization_profiles")
        op.drop_index("ix_organization_profiles_tenant_id", table_name="organization_profiles")
        op.drop_table("organization_profiles")
    ad_cols = {c["name"] for c in insp.get_columns("applicability_decisions")}
    for col in ("open_questions", "framework_exposure", "scope"):
        if col in ad_cols:
            op.drop_column("applicability_decisions", col)
    user_cols = {c["name"] for c in insp.get_columns("users")}
    if "ui_mode" in user_cols:
        op.drop_column("users", "ui_mode")
