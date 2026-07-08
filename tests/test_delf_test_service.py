from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.delf_test_service import DelfTestError, DelfTestService
from app.domain.constants import (
    DEFAULT_DELF_LEVEL_THRESHOLDS,
    QUIZ_CATEGORIES,
)
from app.domain.entities import DelfTestConfig, DelfTestSession, ProgressData, QuizQuestion, User


def _student(class_level: str = "7ème année") -> User:
    return User(
        id=uuid4(),
        email="student@test.fr",
        first_name="Jean",
        last_name="Dupont",
        level="debutant",
        created_at=datetime.now(timezone.utc),
        role="user",
        class_level=class_level,
    )


def _question(category: str, level: str, correct: int = 0) -> QuizQuestion:
    return QuizQuestion(
        id=uuid4(),
        question=f"Question {category}",
        options=["A", "B", "C", "D"],
        correct_index=correct,
        explanation="Parce que.",
        category=category,
        level=level,
    )


@dataclass
class FakeDelfTestRepo:
    sessions: dict[UUID, DelfTestSession] = field(default_factory=dict)
    config: DelfTestConfig = field(
        default_factory=lambda: DelfTestConfig(
            id=uuid4(),
            questions_per_category=2,
            level_thresholds=list(DEFAULT_DELF_LEVEL_THRESHOLDS),
            updated_at=datetime.now(timezone.utc),
        )
    )

    def create_session(
        self,
        user_id: UUID,
        class_level: str,
        target_delf_level: str,
        question_ids_by_category: dict[str, list[str]],
    ) -> DelfTestSession:
        now = datetime.now(timezone.utc)
        session = DelfTestSession(
            id=uuid4(),
            user_id=user_id,
            class_level=class_level,
            target_delf_level=target_delf_level,
            status="in_progress",
            question_ids_by_category=dict(question_ids_by_category),
            answers=[],
            category_scores={},
            created_at=now,
            started_at=now,
        )
        self.sessions[session.id] = session
        return session

    def get_session(self, session_id: UUID) -> DelfTestSession | None:
        return self.sessions.get(session_id)

    def get_active_session(self, user_id: UUID) -> DelfTestSession | None:
        for session in self.sessions.values():
            if session.user_id == user_id and session.status == "in_progress":
                return session
        return None

    def update_session(
        self,
        session_id: UUID,
        *,
        status: str | None = None,
        answers: list | None = None,
        category_scores: dict[str, int] | None = None,
        overall_score: int | None = None,
        achieved_delf_level: str | None = None,
        finished_at: datetime | None = None,
    ) -> DelfTestSession | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        if status is not None:
            session.status = status
        if answers is not None:
            session.answers = list(answers)
        if category_scores is not None:
            session.category_scores = dict(category_scores)
        if overall_score is not None:
            session.overall_score = overall_score
        if achieved_delf_level is not None:
            session.achieved_delf_level = achieved_delf_level
        if finished_at is not None:
            session.finished_at = finished_at
        return session

    def list_sessions_for_user(self, user_id: UUID) -> list[DelfTestSession]:
        return [s for s in self.sessions.values() if s.user_id == user_id]

    def list_all_sessions(self, **kwargs) -> list[DelfTestSession]:
        return list(self.sessions.values())

    def get_config(self) -> DelfTestConfig:
        return self.config

    def update_config(self, **kwargs) -> DelfTestConfig:
        if kwargs.get("questions_per_category") is not None:
            self.config.questions_per_category = kwargs["questions_per_category"]
        if kwargs.get("level_thresholds") is not None:
            self.config.level_thresholds = list(kwargs["level_thresholds"])
        return self.config


@dataclass
class FakeQuizRepo:
    questions: list[QuizQuestion] = field(default_factory=list)

    def list_all(self) -> list[QuizQuestion]:
        return list(self.questions)

    def list_by_level(self, level: str) -> list[QuizQuestion]:
        return [q for q in self.questions if q.level == level]

    def list_by_level_and_category(
        self, level: str, category: str
    ) -> list[QuizQuestion]:
        return [
            q for q in self.questions if q.level == level and q.category == category
        ]

    def get(self, question_id: UUID) -> QuizQuestion | None:
        return next((q for q in self.questions if q.id == question_id), None)

    def create(self, **kwargs) -> QuizQuestion:
        raise NotImplementedError

    def update(self, *args, **kwargs) -> QuizQuestion | None:
        raise NotImplementedError

    def delete(self, question_id: UUID) -> bool:
        raise NotImplementedError

    def count(self) -> int:
        return len(self.questions)


@dataclass
class FakeProgressRepo:
    data: dict[UUID, ProgressData] = field(default_factory=dict)

    def get_for_user(self, user_id: UUID) -> ProgressData:
        return self.data.get(user_id, ProgressData.empty())

    def upsert_for_user(self, user_id: UUID, progress: ProgressData) -> None:
        self.data[user_id] = progress


def _build_service(
    delf_repo: FakeDelfTestRepo,
    quiz_repo: FakeQuizRepo,
    progress_repo: FakeProgressRepo | None = None,
) -> DelfTestService:
    return DelfTestService(
        delf_tests=delf_repo,
        quiz=quiz_repo,
        progress=progress_repo or FakeProgressRepo(),
    )


def _seed_questions(level: str, count: int = 3) -> list[QuizQuestion]:
    questions: list[QuizQuestion] = []
    for category in QUIZ_CATEGORIES:
        for _index in range(count):
            questions.append(_question(category, level, correct=0))
    return questions


def test_start_test_samples_all_categories() -> None:
    user = _student()
    quiz_repo = FakeQuizRepo(questions=_seed_questions(user.class_level or ""))
    service = _build_service(FakeDelfTestRepo(), quiz_repo)
    result = service.start_test(user)
    assert len(result["sections"]) == len(QUIZ_CATEGORIES)
    assert result["targetDelfLevel"] == "A2"


def test_start_test_blocks_duplicate_active_session() -> None:
    user = _student()
    quiz_repo = FakeQuizRepo(questions=_seed_questions(user.class_level or ""))
    delf_repo = FakeDelfTestRepo()
    service = _build_service(delf_repo, quiz_repo)
    service.start_test(user)
    with pytest.raises(DelfTestError, match="déjà en cours"):
        service.start_test(user)


def test_start_test_requires_class_level() -> None:
    user = _student()
    user.class_level = None
    service = _build_service(FakeDelfTestRepo(), FakeQuizRepo())
    with pytest.raises(DelfTestError, match="Niveau scolaire"):
        service.start_test(user)


def test_start_test_insufficient_questions() -> None:
    user = _student()
    service = _build_service(FakeDelfTestRepo(), FakeQuizRepo(questions=[]))
    with pytest.raises(DelfTestError, match="Pas assez de questions"):
        service.start_test(user)


def test_submit_section_grades_answers() -> None:
    user = _student()
    quiz_repo = FakeQuizRepo(questions=_seed_questions(user.class_level or ""))
    service = _build_service(FakeDelfTestRepo(), quiz_repo)
    start = service.start_test(user)
    session_id = UUID(start["sessionId"])
    category = QUIZ_CATEGORIES[0]
    section = next(s for s in start["sections"] if s["category"] == category)
    answers = [
        {"questionId": q["id"], "selectedIndex": 0, "timeMs": 1000}
        for q in section["questions"]
    ]
    result = service.submit_section(user, session_id, category, answers)
    assert result["score"] == 100
    assert result["correctCount"] == len(section["questions"])


def test_submit_section_rejects_duplicate_category() -> None:
    user = _student()
    quiz_repo = FakeQuizRepo(questions=_seed_questions(user.class_level or ""))
    service = _build_service(FakeDelfTestRepo(), quiz_repo)
    start = service.start_test(user)
    session_id = UUID(start["sessionId"])
    category = QUIZ_CATEGORIES[0]
    section = next(s for s in start["sections"] if s["category"] == category)
    answers = [
        {"questionId": q["id"], "selectedIndex": 0, "timeMs": 500}
        for q in section["questions"]
    ]
    service.submit_section(user, session_id, category, answers)
    with pytest.raises(DelfTestError, match="déjà été soumise"):
        service.submit_section(user, session_id, category, answers)


def test_finish_test_computes_delf_level() -> None:
    user = _student()
    quiz_repo = FakeQuizRepo(questions=_seed_questions(user.class_level or ""))
    service = _build_service(FakeDelfTestRepo(), quiz_repo)
    start = service.start_test(user)
    session_id = UUID(start["sessionId"])
    for section in start["sections"]:
        answers = [
            {"questionId": q["id"], "selectedIndex": 0, "timeMs": 800}
            for q in section["questions"]
        ]
        service.submit_section(user, session_id, section["category"], answers)
    results = service.finish_test(user, session_id)
    assert results["overallScore"] == 100
    assert results["achievedDelfLevel"] == "B1"
    assert results["comparisonToTarget"] == "above"


def test_finish_test_requires_all_sections() -> None:
    user = _student()
    quiz_repo = FakeQuizRepo(questions=_seed_questions(user.class_level or ""))
    service = _build_service(FakeDelfTestRepo(), quiz_repo)
    start = service.start_test(user)
    session_id = UUID(start["sessionId"])
    with pytest.raises(DelfTestError, match="Sections manquantes"):
        service.finish_test(user, session_id)
