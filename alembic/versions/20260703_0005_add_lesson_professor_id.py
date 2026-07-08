"""add professor_id to lessons

Revision ID: 0005
Revises: bdff83c8b7ae
Create Date: 2026-07-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "bdff83c8b7ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column("professor_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_lessons_professor_id",
        "lessons",
        "users",
        ["professor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_lessons_professor_id", "lessons", ["professor_id"])


def downgrade() -> None:
    op.drop_index("ix_lessons_professor_id", table_name="lessons")
    op.drop_constraint("fk_lessons_professor_id", "lessons", type_="foreignkey")
    op.drop_column("lessons", "professor_id")
