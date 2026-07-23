"""content ownership and visibility

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | tuple[str, str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "lessons",
        sa.Column(
            "visibility",
            sa.String(length=32),
            nullable=False,
            server_default="public",
        ),
    )
    op.create_index("ix_lessons_school_id", "lessons", ["school_id"])
    op.create_foreign_key(
        "fk_lessons_school_id_schools",
        "lessons",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="SET NULL",
    )

    for table in ("quiz_questions", "stories"):
        op.add_column(
            table,
            sa.Column("professor_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.add_column(
            table,
            sa.Column(
                "visibility",
                sa.String(length=32),
                nullable=False,
                server_default="public",
            ),
        )
        op.create_index(f"ix_{table}_professor_id", table, ["professor_id"])
        op.create_index(f"ix_{table}_school_id", table, ["school_id"])
        op.create_foreign_key(
            f"fk_{table}_professor_id_users",
            table,
            "users",
            ["professor_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            f"fk_{table}_school_id_schools",
            table,
            "schools",
            ["school_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    for table in ("stories", "quiz_questions", "lessons"):
        op.drop_constraint(f"fk_{table}_school_id_schools", table, type_="foreignkey")
        if table != "lessons":
            op.drop_constraint(f"fk_{table}_professor_id_users", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_school_id", table_name=table)
        if table != "lessons":
            op.drop_index(f"ix_{table}_professor_id", table_name=table)
        op.drop_column(table, "visibility")
        op.drop_column(table, "school_id")
        if table != "lessons":
            op.drop_column(table, "professor_id")
