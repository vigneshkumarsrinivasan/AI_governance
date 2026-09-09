"""unified control graph: mapping provenance + effectiveness history +
compliance inheritance + governance decisions & snapshots

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-09

Additive only. No existing table or column removed. The
regulatory_requirement_control_maps table already exists (rev 36606e944171);
this only adds provenance columns to it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MAP_COLS = [
    ("mapping_source", sa.Column("mapping_source", sa.String(length=32), server_default="ai_proposer")),
    ("mapping_version", sa.Column("mapping_version", sa.String(length=16), server_default="1.0")),
    ("effective_date", sa.Column("effective_date", sa.String(length=32), nullable=True)),
    ("superseded_by_id", sa.Column("superseded_by_id", sa.String(length=36), nullable=True)),
    ("legal_review_status", sa.Column("legal_review_status", sa.String(length=32), server_default="NOT_REVIEWED")),
    ("expert_reviewed_by", sa.Column("expert_reviewed_by", sa.String(length=255), nullable=True)),
    ("expert_reviewed_at", sa.Column("expert_reviewed_at", sa.DateTime(), nullable=True)),
    ("last_reviewed_at", sa.Column("last_reviewed_at", sa.DateTime(), nullable=True)),
]


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "regulatory_requirement_control_maps" in tables:
        existing = {c["name"] for c in insp.get_columns("regulatory_requirement_control_maps")}
        for name, col in _MAP_COLS:
            if name not in existing:
                op.add_column("regulatory_requirement_control_maps", col)

    if "control_effectiveness_events" not in tables:
        op.create_table(
            "control_effectiveness_events",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("organization_id", sa.String(length=36), nullable=True),
            sa.Column("control_code", sa.String(length=64), nullable=False),
            sa.Column("system_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("effectiveness", sa.String(length=50), nullable=True),
            sa.Column("lifecycle_state", sa.String(length=40), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("changed_by", sa.String(length=255), nullable=True),
            sa.Column("changed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_ctrl_eff_tenant", "control_effectiveness_events", ["tenant_id"])
        op.create_index("ix_ctrl_eff_code", "control_effectiveness_events", ["control_code"])
        op.create_index("ix_ctrl_eff_changed", "control_effectiveness_events", ["changed_at"])

    if "compliance_inheritance" not in tables:
        op.create_table(
            "compliance_inheritance",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("control_code", sa.String(length=64), nullable=False),
            sa.Column("source_scope", sa.String(length=32), nullable=False),
            sa.Column("source_ref", sa.String(length=255), nullable=True),
            sa.Column("applies_to_system_id", sa.String(length=36), nullable=True),
            sa.Column("applicability_note", sa.Text(), nullable=True),
            sa.Column("exceptions", sa.JSON(), nullable=True),
            sa.Column("verified_state", sa.String(length=32), server_default="ASSERTED"),
            sa.Column("evidence_ids", sa.JSON(), nullable=True),
            sa.Column("created_by", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_inherit_tenant", "compliance_inheritance", ["tenant_id"])
        op.create_index("ix_inherit_code", "compliance_inheritance", ["control_code"])

    if "governance_decisions" not in tables:
        op.create_table(
            "governance_decisions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("decision", sa.String(length=120), nullable=False),
            sa.Column("subject_type", sa.String(length=48), nullable=False),
            sa.Column("subject_id", sa.String(length=36), nullable=False),
            sa.Column("decided_by", sa.String(length=255), nullable=True),
            sa.Column("decided_by_role", sa.String(length=64), nullable=True),
            sa.Column("rationale", sa.Text(), nullable=True),
            sa.Column("context", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_gov_dec_tenant", "governance_decisions", ["tenant_id"])
        op.create_index("ix_gov_dec_subject", "governance_decisions", ["subject_id"])

    if "governance_snapshots" not in tables:
        op.create_table(
            "governance_snapshots",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("kind", sa.String(length=48), nullable=False),
            sa.Column("subject_type", sa.String(length=48), nullable=False),
            sa.Column("subject_id", sa.String(length=36), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("content_hash", sa.String(length=64), nullable=True),
            sa.Column("created_by", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_gov_snap_tenant", "governance_snapshots", ["tenant_id"])
        op.create_index("ix_gov_snap_subject", "governance_snapshots", ["subject_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    for t in ("governance_snapshots", "governance_decisions", "compliance_inheritance", "control_effectiveness_events"):
        if t in tables:
            op.drop_table(t)
    if "regulatory_requirement_control_maps" in tables:
        existing = {c["name"] for c in insp.get_columns("regulatory_requirement_control_maps")}
        for name, _ in reversed(_MAP_COLS):
            if name in existing:
                op.drop_column("regulatory_requirement_control_maps", name)
