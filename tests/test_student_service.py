from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.application.student_service import StudentService
from app.application.student_stats_service import StudentStatsService
from app.domain.entities import StudentReviewItem, StudentStats, User


def test_student_review_completion_is_idempotent_and_hint_falls_back() -> None:
    user = _user()
    item = StudentReviewItem(
        id=uuid4(),
        user_id=user.id,
        source_type="parcours",
        source_id="step-1",
        question_id="question-1",
        category="Grammaire",
        question="Choisis la phrase correcte.",
        options=["Je va", "Je vais"],
        selected_index=0,
        correct_index=1,
        explanation="Avec je, on utilise vais.",
        status="open",
        times_reviewed=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    reviews = _FakeReviewRepository(item)
    progress = _FakeProgressRepository(user.id)
    service = StudentService(
        reviews=reviews,
        progress=progress,
        stats=StudentStatsService(progress),
        parcours=_FakeParcoursService(),
        delf_tests=_FakeDelfRepository(),
        delf_service=object(),
        ai=None,
    )

    review = service.get_review(user)
    assert review["totalOpen"] == 1
    assert review["weakCategories"] == [{"category": "Grammaire", "count": 1}]

    first = service.complete_review_item(user, item.id)
    second = service.complete_review_item(user, item.id)

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert second["timesReviewed"] == 1

    hint = service.get_hint(user, item.id)
    assert hint["source"] == "fallback"
    assert hint["hint"] == "Avec je, on utilise vais."


class _FakeReviewRepository:
    def __init__(self, item: StudentReviewItem) -> None:
        self.item = item

    def list_for_user(self, user_id, *, status=None):
        if self.item.user_id != user_id:
            return []
        if status is not None and self.item.status != status:
            return []
        return [self.item]

    def get_for_user(self, user_id, item_id):
        if self.item.user_id == user_id and self.item.id == item_id:
            return self.item
        return None

    def mark_completed(self, user_id, item_id):
        item = self.get_for_user(user_id, item_id)
        if item is None:
            return None
        if item.status != "completed":
            item.status = "completed"
            item.times_reviewed += 1
        return item


class _FakeProgressRepository:
    def __init__(self, user_id) -> None:
        self.stats = StudentStats(
            user_id=user_id,
            total_xp=120,
            current_streak=3,
            longest_streak=5,
            preferred_difficulty="medium",
            updated_at=datetime.now(timezone.utc),
        )

    def get_stats(self, user_id):
        return self.stats if self.stats.user_id == user_id else None

    def upsert_stats(self, stats):
        self.stats = stats
        return stats

    def list_leaderboard(self, *, school_id=None, class_level=None):
        return []


class _FakeParcoursService:
    def get_summary(self, user):
        return SimpleNamespace(
            completion_percent=40,
            total_steps=10,
            completed_steps=4,
            next_step_id=uuid4(),
            next_step_title="Réviser les accords",
        )


class _FakeDelfRepository:
    def list_sessions_for_user(self, user_id):
        return []


def _user() -> User:
    return User(
        id=uuid4(),
        email="student@example.com",
        first_name="Sana",
        last_name="Student",
        level="A1",
        class_level="6eme",
        created_at=datetime.now(timezone.utc),
    )
