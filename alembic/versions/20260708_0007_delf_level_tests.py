"""delf level test sessions and config

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-08

"""
from collections.abc import Sequence
import json
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_THRESHOLDS = [
    {"level": "B1", "minOverall": 85, "minCategory": 75},
    {"level": "A2/B1", "minOverall": 75, "minCategory": 65},
    {"level": "A2", "minOverall": 65, "minCategory": 55},
    {"level": "A1+", "minOverall": 50, "minCategory": 40},
    {"level": "A1", "minOverall": 35, "minCategory": 25},
]


def upgrade() -> None:
    op.create_table(
        "delf_test_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_level", sa.String(length=32), nullable=False),
        sa.Column("target_delf_level", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column("question_ids_by_category", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("answers", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("category_scores", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("achieved_delf_level", sa.String(length=32), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delf_test_sessions_user_id", "delf_test_sessions", ["user_id"])
    op.create_index("ix_delf_test_sessions_status", "delf_test_sessions", ["status"])

    op.create_table(
        "delf_test_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("questions_per_category", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("level_thresholds", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    config_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    op.execute(
        sa.text(
            "INSERT INTO delf_test_config (id, questions_per_category, level_thresholds, updated_at) "
            "VALUES (:id, 5, CAST(:thresholds AS jsonb), :updated_at)"
        ).bindparams(
            id=config_id,
            thresholds=json.dumps(DEFAULT_THRESHOLDS),
            updated_at=now,
        )
    )


def downgrade() -> None:
    op.drop_table("delf_test_config")
    op.drop_index("ix_delf_test_sessions_status", table_name="delf_test_sessions")
    op.drop_index("ix_delf_test_sessions_user_id", table_name="delf_test_sessions")
    op.drop_table("delf_test_sessions")
