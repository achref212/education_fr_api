"""delf mock exams

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-22

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delf_mock_exams",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track", sa.String(length=32), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("total_points", sa.Integer(), nullable=False),
        sa.Column("source_notes", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delf_mock_exams_track", "delf_mock_exams", ["track"])
    op.create_index("ix_delf_mock_exams_level", "delf_mock_exams", ["level"])
    op.create_index("ix_delf_mock_exams_status", "delf_mock_exams", ["status"])
    op.create_index(
        "ix_delf_mock_exams_track_level_status",
        "delf_mock_exams",
        ["track", "level", "status"],
    )

    op.create_table(
        "delf_mock_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_order", sa.Integer(), nullable=False),
        sa.Column("section_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("rubric", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["exam_id"], ["delf_mock_exams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delf_mock_sections_exam_id", "delf_mock_sections", ["exam_id"])

    op.create_table(
        "delf_mock_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("answer_key", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("rubric", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["section_id"], ["delf_mock_sections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delf_mock_items_section_id", "delf_mock_items", ["section_id"])

    op.create_table(
        "delf_mock_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["delf_mock_exams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delf_mock_assets_exam_id", "delf_mock_assets", ["exam_id"])


def downgrade() -> None:
    op.drop_index("ix_delf_mock_assets_exam_id", table_name="delf_mock_assets")
    op.drop_table("delf_mock_assets")
    op.drop_index("ix_delf_mock_items_section_id", table_name="delf_mock_items")
    op.drop_table("delf_mock_items")
    op.drop_index("ix_delf_mock_sections_exam_id", table_name="delf_mock_sections")
    op.drop_table("delf_mock_sections")
    op.drop_index("ix_delf_mock_exams_track_level_status", table_name="delf_mock_exams")
    op.drop_index("ix_delf_mock_exams_status", table_name="delf_mock_exams")
    op.drop_index("ix_delf_mock_exams_level", table_name="delf_mock_exams")
    op.drop_index("ix_delf_mock_exams_track", table_name="delf_mock_exams")
    op.drop_table("delf_mock_exams")
