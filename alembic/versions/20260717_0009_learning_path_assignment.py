"""learning path assignment and matching

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-17

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_learning_paths_class_level",
        "learning_paths",
        type_="unique",
    )
    op.add_column("learning_paths", sa.Column("min_score", sa.Integer(), nullable=True))
    op.add_column("learning_paths", sa.Column("max_score", sa.Integer(), nullable=True))
    op.add_column(
        "learning_paths",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_learning_paths_match",
        "learning_paths",
        ["class_level", "delf_target_level", "is_active"],
    )
    op.add_column(
        "users",
        sa.Column("assigned_learning_path_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_users_assigned_learning_path_id",
        "users",
        ["assigned_learning_path_id"],
    )
    op.create_foreign_key(
        "fk_users_assigned_learning_path_id",
        "users",
        "learning_paths",
        ["assigned_learning_path_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_users_assigned_learning_path_id",
        "users",
        type_="foreignkey",
    )
    op.drop_index("ix_users_assigned_learning_path_id", table_name="users")
    op.drop_column("users", "assigned_learning_path_id")
    op.drop_index("ix_learning_paths_match", table_name="learning_paths")
    op.drop_column("learning_paths", "is_default")
    op.drop_column("learning_paths", "max_score")
    op.drop_column("learning_paths", "min_score")
    op.create_unique_constraint(
        "uq_learning_paths_class_level",
        "learning_paths",
        ["class_level"],
    )
