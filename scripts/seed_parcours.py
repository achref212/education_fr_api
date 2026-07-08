#!/usr/bin/env python3
"""Seed learning paths, steps, and game catalog for DELFy parcours."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select

from app.domain.constants import (
    CLASS_LEVELS,
    DELF_TARGETS_BY_CLASS,
    LESSON_CATEGORIES,
    QUIZ_CATEGORIES,
)
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.models.game import GameORM
from app.infrastructure.models.learning_path import LearningPathORM
from app.infrastructure.models.learning_path_step import LearningPathStepORM
from app.infrastructure.models.lesson import LessonORM
from app.infrastructure.models.story import StoryORM


def seed_games(session) -> None:
    existing = session.scalar(select(GameORM).limit(1))
    if existing is not None:
        print("Games already seeded, skipping.")
        return
    now = datetime.now(timezone.utc)
    games = [
        GameORM(
            slug="quiz_duel",
            name="Quiz Duel",
            description="Défiez vos amis avec des questions DELF",
            min_players=2,
            max_players=8,
            default_question_count=10,
            is_active=True,
            created_at=now,
        ),
        GameORM(
            slug="friend_challenge",
            name="Défi entre amis",
            description="Apprenez le français en jouant avec vos camarades",
            min_players=2,
            max_players=4,
            default_question_count=8,
            is_active=True,
            created_at=now,
        ),
    ]
    session.add_all(games)
    print(f"Seeded {len(games)} games.")


def seed_learning_paths(session) -> None:
    existing = session.scalar(select(LearningPathORM).limit(1))
    if existing is not None:
        print("Learning paths already seeded, skipping.")
        return
    now = datetime.now(timezone.utc)
    for class_level in CLASS_LEVELS:
        path = LearningPathORM(
            class_level=class_level,
            title=f"Parcours DELF — {class_level}",
            description=f"Parcours d'apprentissage du français pour la {class_level}",
            delf_target_level=DELF_TARGETS_BY_CLASS[class_level],
            is_active=True,
            created_at=now,
        )
        session.add(path)
        session.flush()
        previous_step_id = None
        step_order = 1
        for category in LESSON_CATEGORIES:
            lesson = session.scalar(
                select(LessonORM)
                .where(
                    LessonORM.level == class_level,
                    LessonORM.category == category,
                )
                .order_by(LessonORM.sort_order)
                .limit(1)
            )
            if lesson is not None:
                lesson_step = LearningPathStepORM(
                    path_id=path.id,
                    step_order=step_order,
                    step_type="lesson",
                    title=f"Leçon — {category}",
                    xp_reward=10,
                    lesson_id=lesson.id,
                    required_step_id=previous_step_id,
                    created_at=now,
                )
                session.add(lesson_step)
                session.flush()
                previous_step_id = lesson_step.id
                step_order += 1
            if category in QUIZ_CATEGORIES:
                quiz_step = LearningPathStepORM(
                    path_id=path.id,
                    step_order=step_order,
                    step_type="quiz",
                    title=f"Quiz — {category}",
                    xp_reward=15,
                    quiz_category=category,
                    required_step_id=previous_step_id,
                    created_at=now,
                )
                session.add(quiz_step)
                session.flush()
                previous_step_id = quiz_step.id
                step_order += 1
        story = session.scalar(
            select(StoryORM)
            .where(StoryORM.level == class_level)
            .limit(1)
        )
        if story is not None:
            story_step = LearningPathStepORM(
                path_id=path.id,
                step_order=step_order,
                step_type="story",
                title=f"Histoire — {class_level}",
                xp_reward=20,
                story_id=story.id,
                required_step_id=previous_step_id,
                created_at=now,
            )
            session.add(story_step)
        print(f"Seeded parcours for {class_level}.")


def main() -> None:
    session = SessionLocal()
    try:
        seed_games(session)
        seed_learning_paths(session)
        session.commit()
        print("Seed completed successfully.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
