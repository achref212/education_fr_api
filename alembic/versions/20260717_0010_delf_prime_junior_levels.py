"""delf prime junior levels

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-17

"""
from collections.abc import Sequence
import json

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_THRESHOLDS = [
    {"level": "B2", "minOverall": 90, "minCategory": 85},
    {"level": "B1", "minOverall": 80, "minCategory": 70},
    {"level": "A2", "minOverall": 65, "minCategory": 55},
    {"level": "A1", "minOverall": 50, "minCategory": 40},
    {"level": "A1.1", "minOverall": 35, "minCategory": 25},
]

OLD_THRESHOLDS = [
    {"level": "B1", "minOverall": 85, "minCategory": 75},
    {"level": "A2/B1", "minOverall": 75, "minCategory": 65},
    {"level": "A2", "minOverall": 65, "minCategory": 55},
    {"level": "A1+", "minOverall": 50, "minCategory": 40},
    {"level": "A1", "minOverall": 35, "minCategory": 25},
]


def _normalize_column(table: str, column: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET {column} = CASE {column}
                WHEN 'A1+' THEN 'A1'
                WHEN 'A2/B1' THEN 'B1'
                ELSE {column}
            END
            WHERE {column} IN ('A1+', 'A2/B1')
            """
        )
    )


def _downgrade_column(table: str, column: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET {column} = CASE {column}
                WHEN 'A1.1' THEN 'A1'
                WHEN 'B2' THEN 'B1'
                ELSE {column}
            END
            WHERE {column} IN ('A1.1', 'B2')
            """
        )
    )


def upgrade() -> None:
    _normalize_column("learning_paths", "delf_target_level")
    _normalize_column("delf_test_templates", "target_delf_level")
    _normalize_column("delf_test_sessions", "target_delf_level")
    _normalize_column("delf_test_sessions", "achieved_delf_level")

    op.execute(
        sa.text(
            """
            UPDATE delf_test_config
            SET level_thresholds = CAST(:thresholds AS jsonb)
            """
        ).bindparams(thresholds=json.dumps(NEW_THRESHOLDS))
    )


def downgrade() -> None:
    _downgrade_column("learning_paths", "delf_target_level")
    _downgrade_column("delf_test_templates", "target_delf_level")
    _downgrade_column("delf_test_sessions", "target_delf_level")
    _downgrade_column("delf_test_sessions", "achieved_delf_level")

    op.execute(
        sa.text(
            """
            UPDATE delf_test_config
            SET level_thresholds = CAST(:thresholds AS jsonb)
            """
        ).bindparams(thresholds=json.dumps(OLD_THRESHOLDS))
    )
