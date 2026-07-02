"""add schools, recommendations, class_level, school relations

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-02

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create the schools table (FK to users which already exists)
    op.create_table(
        "schools",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("address", sa.String(length=512), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("postal_code", sa.String(length=32), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("director_name", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_schools_email"), "schools", ["email"], unique=True
    )

    # 2. Alter users table — add new columns (nullable so existing rows are safe)
    op.add_column(
        "users",
        sa.Column("class_level", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "school_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "teacher_school_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )

    # 3. Add FK constraints on users → schools (after both tables exist)
    op.create_foreign_key(
        "fk_users_school_id",
        "users",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_users_teacher_school_id",
        "users",
        "schools",
        ["teacher_school_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_school_id", "users", ["school_id"])
    op.create_index("ix_users_teacher_school_id", "users", ["teacher_school_id"])

    # 4. Create the recommendations table
    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["professor_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_student_id", "recommendations", ["student_id"])
    op.create_index("ix_recommendations_professor_id", "recommendations", ["professor_id"])

    # 5. Alter multiplayer_rooms — add professor_id and school_id
    op.add_column(
        "multiplayer_rooms",
        sa.Column("professor_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "multiplayer_rooms",
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_multiplayer_rooms_professor_id",
        "multiplayer_rooms",
        "users",
        ["professor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_multiplayer_rooms_school_id",
        "multiplayer_rooms",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_multiplayer_rooms_professor_id", "multiplayer_rooms", ["professor_id"]
    )
    op.create_index(
        "ix_multiplayer_rooms_school_id", "multiplayer_rooms", ["school_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_multiplayer_rooms_school_id", table_name="multiplayer_rooms")
    op.drop_index("ix_multiplayer_rooms_professor_id", table_name="multiplayer_rooms")
    op.drop_constraint(
        "fk_multiplayer_rooms_school_id", "multiplayer_rooms", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_multiplayer_rooms_professor_id", "multiplayer_rooms", type_="foreignkey"
    )
    op.drop_column("multiplayer_rooms", "school_id")
    op.drop_column("multiplayer_rooms", "professor_id")

    op.drop_index("ix_recommendations_professor_id", table_name="recommendations")
    op.drop_index("ix_recommendations_student_id", table_name="recommendations")
    op.drop_table("recommendations")

    op.drop_index("ix_users_teacher_school_id", table_name="users")
    op.drop_index("ix_users_school_id", table_name="users")
    op.drop_constraint("fk_users_teacher_school_id", "users", type_="foreignkey")
    op.drop_constraint("fk_users_school_id", "users", type_="foreignkey")
    op.drop_column("users", "teacher_school_id")
    op.drop_column("users", "school_id")
    op.drop_column("users", "class_level")

    op.drop_index(op.f("ix_schools_email"), table_name="schools")
    op.drop_table("schools")
