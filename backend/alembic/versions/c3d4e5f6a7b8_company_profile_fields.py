"""company profile fields: legal_name, website, company_type, employee_range,
deployment/customer countries, vendor + personal-data flags, governance contacts

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-08

Additive only - all columns nullable / defaulted. No data changed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLS = [
    ("legal_name", sa.Column("legal_name", sa.String(length=255), nullable=True)),
    ("website", sa.Column("website", sa.String(length=255), nullable=True)),
    ("company_type", sa.Column("company_type", sa.String(length=40), nullable=True)),
    ("ai_deployment_countries", sa.Column("ai_deployment_countries", sa.JSON(), nullable=True)),
    ("customer_countries", sa.Column("customer_countries", sa.JSON(), nullable=True)),
    ("employee_range", sa.Column("employee_range", sa.String(length=20), nullable=True)),
    ("is_software_vendor", sa.Column("is_software_vendor", sa.Boolean(), server_default=sa.text("0"))),
    ("processes_personal_data", sa.Column("processes_personal_data", sa.Boolean(), server_default=sa.text("1"))),
    ("governance_contacts", sa.Column("governance_contacts", sa.JSON(), nullable=True)),
]


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("organizations")}
    for name, col in _COLS:
        if name not in existing:
            op.add_column("organizations", col)


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("organizations")}
    for name, _ in reversed(_COLS):
        if name in existing:
            op.drop_column("organizations", name)
