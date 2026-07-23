"""delf mock attempts

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | tuple[str, str] | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delf_mock_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("section_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("approximate", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["delf_mock_exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delf_mock_attempts_user_id", "delf_mock_attempts", ["user_id"])
    op.create_index("ix_delf_mock_attempts_exam_id", "delf_mock_attempts", ["exam_id"])
    op.create_index(
        "ix_delf_mock_attempts_user_exam_status",
        "delf_mock_attempts",
        ["user_id", "exam_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_delf_mock_attempts_user_exam_status", table_name="delf_mock_attempts")
    op.drop_index("ix_delf_mock_attempts_exam_id", table_name="delf_mock_attempts")
    op.drop_index("ix_delf_mock_attempts_user_id", table_name="delf_mock_attempts")
    op.drop_table("delf_mock_attempts")
