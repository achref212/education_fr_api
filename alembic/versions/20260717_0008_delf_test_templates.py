"""delf test templates

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-17

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delf_test_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("class_level", sa.String(length=32), nullable=False),
        sa.Column("target_delf_level", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("question_ids_by_category", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_delf_test_templates_class_level",
        "delf_test_templates",
        ["class_level"],
    )
    op.create_index(
        "ix_delf_test_templates_active_class",
        "delf_test_templates",
        ["class_level", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_delf_test_templates_active_class", table_name="delf_test_templates")
    op.drop_index("ix_delf_test_templates_class_level", table_name="delf_test_templates")
    op.drop_table("delf_test_templates")
