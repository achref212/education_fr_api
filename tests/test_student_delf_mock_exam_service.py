from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.student_delf_mock_exam_service import (
    StudentDelfMockExamError,
    StudentDelfMockExamService,
)
from app.domain.entities import (
    DelfMockAttempt,
    DelfMockExam,
    DelfMockItem,
    DelfMockSection,
    User,
)


def test_student_mock_exam_visibility_scoring_and_review_creation() -> None:
    user = _user()
    published = _exam("published")
    draft = _exam("draft")
    exams = _FakeExamRepository([published, draft])
    attempts = _FakeAttemptRepository()
    reviews = _FakeReviewRepository()
    service = StudentDelfMockExamService(
        exams=exams,
        attempts=attempts,
        reviews=reviews,
    )

    visible = service.list_published_exams(user)
    assert [item["id"] for item in visible] == [str(published.id)]

    attempt = service.create_attempt(user, published.id)
    same_attempt = service.create_attempt(user, published.id)
    assert same_attempt["attemptId"] == attempt["attemptId"]

    item_ids = [
        str(item.id)
        for section in published.sections
        for item in section.items
    ]
    submitted = service.submit_attempt(
        user,
        UUID(attempt["attemptId"]),
        [
            {"itemId": item_ids[0], "selectedIndex": 0},
            {"itemId": item_ids[1], "selectedIndex": 0},
            {"itemId": item_ids[2], "text": "Une réponse complète."},
            {"itemId": item_ids[3], "text": "Je réponds clairement."},
        ],
    )

    assert submitted["status"] == "completed"
    assert submitted["overallScore"] == 75
    assert submitted["resultMessage"] == "Ton score estimé est d’environ 75/100"
    assert submitted["sectionScores"] == {
        "listening": 25,
        "reading": 0,
        "writing": 25,
        "speaking": 25,
    }
    assert len(reviews.items) == 1
    assert reviews.items[0]["source_type"] == "delf_mock_exam"


def test_student_mock_attempt_is_owned_by_current_student() -> None:
    owner = _user()
    other = _user()
    exam = _exam("published")
    attempts = _FakeAttemptRepository()
    attempt = attempts.create_attempt(user_id=owner.id, exam_id=exam.id)
    service = StudentDelfMockExamService(
        exams=_FakeExamRepository([exam]),
        attempts=attempts,
    )

    with pytest.raises(StudentDelfMockExamError):
        service.get_attempt(other, attempt.id)


class _FakeExamRepository:
    def __init__(self, exams: list[DelfMockExam]) -> None:
        self.exams = {exam.id: exam for exam in exams}

    def list_exams(self, *, track=None, level=None, status=None):
        return [
            exam
            for exam in self.exams.values()
            if (status is None or exam.status == status)
            and (track is None or exam.track == track)
            and (level is None or exam.level == level)
        ]

    def get_exam(self, exam_id):
        return self.exams.get(exam_id)


class _FakeAttemptRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, DelfMockAttempt] = {}

    def create_attempt(self, *, user_id, exam_id):
        now = datetime.now(timezone.utc)
        attempt = DelfMockAttempt(
            id=uuid4(),
            user_id=user_id,
            exam_id=exam_id,
            status="in_progress",
            answers=[],
            section_scores={},
            approximate=True,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self.items[attempt.id] = attempt
        return attempt

    def get_attempt(self, attempt_id):
        return self.items.get(attempt_id)

    def get_active_attempt(self, *, user_id, exam_id):
        return next(
            (
                attempt
                for attempt in self.items.values()
                if attempt.user_id == user_id
                and attempt.exam_id == exam_id
                and attempt.status == "in_progress"
            ),
            None,
        )

    def update_attempt(self, attempt_id, **kwargs):
        attempt = self.items.get(attempt_id)
        if attempt is None:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(attempt, key, value)
        return attempt


class _FakeReviewRepository:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def upsert_wrong_answer(self, **kwargs):
        self.items.append(kwargs)
        return None


def _user() -> User:
    return User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        first_name="Sana",
        last_name="Student",
        level="A1",
        class_level="6eme",
        created_at=datetime.now(timezone.utc),
    )


def _exam(status: str) -> DelfMockExam:
    exam_id = uuid4()
    now = datetime.now(timezone.utc)
    sections = [
        _section(exam_id, 1, "listening", True, 0),
        _section(exam_id, 2, "reading", True, 1),
        _section(exam_id, 3, "writing", False, None),
        _section(exam_id, 4, "speaking", False, None),
    ]
    return DelfMockExam(
        id=exam_id,
        track="Junior",
        level="A1",
        title="Examen blanc A1",
        description="Préparation",
        status=status,
        total_duration_minutes=60,
        total_points=100,
        source_notes=None,
        created_at=now,
        updated_at=now,
        sections=sections,
        assets=[],
    )


def _section(
    exam_id: UUID,
    order: int,
    section_type: str,
    objective: bool,
    correct_index: int | None,
) -> DelfMockSection:
    section_id = uuid4()
    item = DelfMockItem(
        id=uuid4(),
        section_id=section_id,
        item_order=1,
        title=f"{section_type} item",
        prompt="Réponds.",
        points=25,
        content={"options": ["A", "B"], "targetWords": 3} if objective else {"targetWords": 3},
        answer_key={"correctIndex": correct_index, "explanation": "La bonne réponse est B."}
        if correct_index is not None
        else {},
        rubric={},
        metadata={},
    )
    return DelfMockSection(
        id=section_id,
        exam_id=exam_id,
        section_order=order,
        section_type=section_type,
        title=section_type,
        duration_minutes=15,
        points=25,
        instructions="Consigne",
        audio_url=None,
        rubric={},
        metadata={},
        items=[item],
    )
