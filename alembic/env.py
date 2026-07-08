import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Ensure "app" is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings
from app.infrastructure.db.base import Base
from app.infrastructure.models import (  # noqa: F401
    contact_message as contact_message_model,
    delf_test as delf_test_model,
    game as game_model,
    game_participant as game_participant_model,
    game_session as game_session_model,
    learning_path as learning_path_model,
    learning_path_step as learning_path_step_model,
    lesson as lesson_model,
    multiplayer_room as multiplayer_room_model,
    quiz_question as quiz_question_model,
    story as story_model,
    student_stats as student_stats_model,
    student_step_progress as student_step_progress_model,
    user as user_model,
    user_progress as user_progress_model,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()


def get_url() -> str:
    return settings.database_url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
