"""parcours and multiplayer games tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-08

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_paths",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_level", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("delf_target_level", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_level", name="uq_learning_paths_class_level"),
    )
    op.create_index("ix_learning_paths_class_level", "learning_paths", ["class_level"])

    op.create_table(
        "learning_path_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("quiz_category", sa.String(length=128), nullable=True),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("required_step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["path_id"], ["learning_paths.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["required_step_id"], ["learning_path_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_path_steps_path_id", "learning_path_steps", ["path_id"])

    op.create_table(
        "student_stats",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_date", sa.Date(), nullable=True),
        sa.Column("preferred_difficulty", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "student_step_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="locked"),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["step_id"], ["learning_path_steps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "step_id", name="uq_student_step_progress"),
    )
    op.create_index("ix_student_step_progress_user_id", "student_step_progress", ["user_id"])
    op.create_index("ix_student_step_progress_step_id", "student_step_progress", ["step_id"])

    op.create_table(
        "games",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("min_players", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("max_players", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("default_question_count", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_games_slug", "games", ["slug"])

    op.create_table(
        "game_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("class_level", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="waiting"),
        sa.Column("question_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("current_round", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_rounds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_id"], ["multiplayer_rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_game_sessions_room_id", "game_sessions", ["room_id"])
    op.create_index("ix_game_sessions_game_id", "game_sessions", ["game_id"])

    op.create_table(
        "game_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "user_id", name="uq_game_participants"),
    )
    op.create_index("ix_game_participants_session_id", "game_participants", ["session_id"])
    op.create_index("ix_game_participants_user_id", "game_participants", ["user_id"])

    op.add_column(
        "multiplayer_rooms",
        sa.Column("class_level", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "multiplayer_rooms",
        sa.Column("active_session_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_multiplayer_rooms_active_session_id",
        "multiplayer_rooms",
        "game_sessions",
        ["active_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_multiplayer_rooms_class_level", "multiplayer_rooms", ["class_level"])


def downgrade() -> None:
    op.drop_index("ix_multiplayer_rooms_class_level", table_name="multiplayer_rooms")
    op.drop_constraint("fk_multiplayer_rooms_active_session_id", "multiplayer_rooms", type_="foreignkey")
    op.drop_column("multiplayer_rooms", "active_session_id")
    op.drop_column("multiplayer_rooms", "class_level")
    op.drop_index("ix_game_participants_user_id", table_name="game_participants")
    op.drop_index("ix_game_participants_session_id", table_name="game_participants")
    op.drop_table("game_participants")
    op.drop_index("ix_game_sessions_game_id", table_name="game_sessions")
    op.drop_index("ix_game_sessions_room_id", table_name="game_sessions")
    op.drop_table("game_sessions")
    op.drop_index("ix_games_slug", table_name="games")
    op.drop_table("games")
    op.drop_index("ix_student_step_progress_step_id", table_name="student_step_progress")
    op.drop_index("ix_student_step_progress_user_id", table_name="student_step_progress")
    op.drop_table("student_step_progress")
    op.drop_table("student_stats")
    op.drop_index("ix_learning_path_steps_path_id", table_name="learning_path_steps")
    op.drop_table("learning_path_steps")
    op.drop_index("ix_learning_paths_class_level", table_name="learning_paths")
    op.drop_table("learning_paths")
