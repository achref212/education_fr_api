from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.delf_test_service import DelfTestError, DelfTestService
from app.domain.constants import (
    DEFAULT_DELF_LEVEL_THRESHOLDS,
    QUIZ_CATEGORIES,
)
from app.domain.entities import (
    DelfTestConfig,
    DelfTestSession,
    DelfTestTemplate,
    LearningPath,
    ProgressData,
    QuizQuestion,
    User,
)


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
    templates: dict[UUID, DelfTestTemplate] = field(default_factory=dict)
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

    def list_templates(self) -> list[DelfTestTemplate]:
        return list(self.templates.values())

    def get_template(self, template_id: UUID) -> DelfTestTemplate | None:
        return self.templates.get(template_id)

    def get_active_template_for_class(self, class_level: str) -> DelfTestTemplate | None:
        return next(
            (t for t in self.templates.values() if t.class_level == class_level and t.is_active),
            None,
        )

    def create_template(self, **kwargs) -> DelfTestTemplate:
        now = datetime.now(timezone.utc)
        if kwargs["is_active"]:
            for template in self.templates.values():
                if template.class_level == kwargs["class_level"]:
                    template.is_active = False
        template = DelfTestTemplate(
            id=uuid4(),
            name=kwargs["name"],
            description=kwargs["description"],
            class_level=kwargs["class_level"],
            target_delf_level=kwargs["target_delf_level"],
            is_active=kwargs["is_active"],
            question_ids_by_category=dict(kwargs["question_ids_by_category"]),
            created_at=now,
            updated_at=now,
        )
        self.templates[template.id] = template
        return template

    def update_template(self, template_id: UUID, **kwargs) -> DelfTestTemplate | None:
        template = self.templates.get(template_id)
        if template is None:
            return None
        for key, value in kwargs.items():
            if value is None:
                continue
            attr = {
                "class_level": "class_level",
                "target_delf_level": "target_delf_level",
                "question_ids_by_category": "question_ids_by_category",
            }.get(key, key)
            setattr(template, attr, value)
        template.updated_at = datetime.now(timezone.utc)
        return template


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


@dataclass
class FakeLearningPathRepo:
    paths: list[LearningPath] = field(default_factory=list)

    def find_match(
        self, class_level: str, delf_level: str | None, score: int | None
    ) -> LearningPath | None:
        candidates = [p for p in self.paths if p.class_level == class_level and p.is_active]
        same_level = [p for p in candidates if delf_level and p.delf_target_level == delf_level]
        for bucket in (same_level, candidates):
            for path in bucket:
                if (
                    score is not None
                    and (path.min_score is None or score >= path.min_score)
                    and (path.max_score is None or score <= path.max_score)
                ):
                    return path
            if bucket:
                return bucket[0]
        return None


@dataclass
class FakeUserRepo:
    assigned: dict[UUID, UUID | None] = field(default_factory=dict)

    def assign_learning_path(
        self, user_id: UUID, learning_path_id: UUID | None
    ) -> User | None:
        self.assigned[user_id] = learning_path_id
        return None


def _build_service(
    delf_repo: FakeDelfTestRepo,
    quiz_repo: FakeQuizRepo,
    progress_repo: FakeProgressRepo | None = None,
    paths_repo: FakeLearningPathRepo | None = None,
    user_repo: FakeUserRepo | None = None,
) -> DelfTestService:
    return DelfTestService(
        delf_tests=delf_repo,
        quiz=quiz_repo,
        progress=progress_repo or FakeProgressRepo(),
        paths=paths_repo,
        users=user_repo,
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
    assert result["targetDelfLevel"] == "A1"


def test_start_test_uses_prime_default_for_primary_class() -> None:
    user = _student("2ème année")
    quiz_repo = FakeQuizRepo(questions=_seed_questions(user.class_level or ""))
    service = _build_service(FakeDelfTestRepo(), quiz_repo)
    result = service.start_test(user)
    assert result["targetDelfLevel"] == "A1.1"


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


def test_start_test_uses_active_template_for_class() -> None:
    user = _student()
    questions = _seed_questions(user.class_level or "", count=2)
    quiz_repo = FakeQuizRepo(questions=questions)
    delf_repo = FakeDelfTestRepo()
    service = _build_service(delf_repo, quiz_repo)
    template_questions = {
        category: [str(next(q.id for q in questions if q.category == category))]
        for category in QUIZ_CATEGORIES
    }
    service.create_template(
        name="Template 7e",
        description=None,
        class_level=user.class_level or "",
        target_delf_level="A2",
        is_active=True,
        question_ids_by_category=template_questions,
    )
    result = service.start_test(user)
    assert {
        section["category"]: [q["id"] for q in section["questions"]]
        for section in result["sections"]
    } == template_questions


def test_create_template_rejects_missing_question() -> None:
    user = _student()
    questions = _seed_questions(user.class_level or "", count=1)
    service = _build_service(FakeDelfTestRepo(), FakeQuizRepo(questions=questions))
    bad_questions = {
        category: [str(next(q.id for q in questions if q.category == category))]
        for category in QUIZ_CATEGORIES
    }
    bad_questions[QUIZ_CATEGORIES[0]] = [str(uuid4())]
    with pytest.raises(DelfTestError, match="Question introuvable"):
        service.create_template(
            name="Bad",
            description=None,
            class_level=user.class_level or "",
            target_delf_level="A2",
            is_active=True,
            question_ids_by_category=bad_questions,
        )


def test_template_accepts_new_prime_and_junior_levels() -> None:
    user = _student("9ème année")
    questions = _seed_questions(user.class_level or "", count=1)
    service = _build_service(FakeDelfTestRepo(), FakeQuizRepo(questions=questions))
    template_questions = {
        category: [str(next(q.id for q in questions if q.category == category))]
        for category in QUIZ_CATEGORIES
    }
    service.create_template(
        name="Junior B2",
        description=None,
        class_level=user.class_level or "",
        target_delf_level="B2",
        is_active=True,
        question_ids_by_category=template_questions,
    )

    prime_user = _student("2ème année")
    prime_questions = _seed_questions(prime_user.class_level or "", count=1)
    prime_service = _build_service(FakeDelfTestRepo(), FakeQuizRepo(questions=prime_questions))
    prime_template_questions = {
        category: [str(next(q.id for q in prime_questions if q.category == category))]
        for category in QUIZ_CATEGORIES
    }
    prime_service.create_template(
        name="Prime A1.1",
        description=None,
        class_level=prime_user.class_level or "",
        target_delf_level="A1.1",
        is_active=True,
        question_ids_by_category=prime_template_questions,
    )


def test_template_rejects_legacy_delf_levels() -> None:
    user = _student()
    questions = _seed_questions(user.class_level or "", count=1)
    service = _build_service(FakeDelfTestRepo(), FakeQuizRepo(questions=questions))
    template_questions = {
        category: [str(next(q.id for q in questions if q.category == category))]
        for category in QUIZ_CATEGORIES
    }
    with pytest.raises(DelfTestError, match="Objectif DELF invalide"):
        service.create_template(
            name="Legacy",
            description=None,
            class_level=user.class_level or "",
            target_delf_level="A1+",
            is_active=True,
            question_ids_by_category=template_questions,
        )


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
    assert results["achievedDelfLevel"] == "B2"
    assert results["comparisonToTarget"] == "above"


def test_finish_test_assigns_matching_learning_path() -> None:
    user = _student()
    quiz_repo = FakeQuizRepo(questions=_seed_questions(user.class_level or ""))
    path = LearningPath(
        id=uuid4(),
        class_level=user.class_level or "",
        title="B2 custom path",
        delf_target_level="B2",
        created_at=datetime.now(timezone.utc),
        min_score=90,
        max_score=100,
    )
    user_repo = FakeUserRepo()
    service = _build_service(
        FakeDelfTestRepo(),
        quiz_repo,
        paths_repo=FakeLearningPathRepo(paths=[path]),
        user_repo=user_repo,
    )
    start = service.start_test(user)
    session_id = UUID(start["sessionId"])
    for section in start["sections"]:
        answers = [
            {"questionId": q["id"], "selectedIndex": 0, "timeMs": 800}
            for q in section["questions"]
        ]
        service.submit_section(user, session_id, section["category"], answers)
    service.finish_test(user, session_id)
    assert user_repo.assigned[user.id] == path.id


def test_finish_test_sorts_thresholds_before_level_calculation() -> None:
    user = _student()
    quiz_repo = FakeQuizRepo(questions=_seed_questions(user.class_level or ""))
    delf_repo = FakeDelfTestRepo()
    delf_repo.config.level_thresholds = [
        {"level": "A1", "minOverall": 35, "minCategory": 25},
        {"level": "B1", "minOverall": 85, "minCategory": 75},
        {"level": "A2", "minOverall": 65, "minCategory": 55},
    ]
    service = _build_service(delf_repo, quiz_repo)
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


def test_config_rejects_legacy_delf_levels() -> None:
    service = _build_service(FakeDelfTestRepo(), FakeQuizRepo())
    with pytest.raises(DelfTestError, match="Niveau DELF invalide"):
        service.update_config(
            questions_per_category=5,
            level_thresholds=[{"level": "A2/B1", "minOverall": 75, "minCategory": 65}],
        )


def test_finish_test_requires_all_sections() -> None:
    user = _student()
    quiz_repo = FakeQuizRepo(questions=_seed_questions(user.class_level or ""))
    service = _build_service(FakeDelfTestRepo(), quiz_repo)
    start = service.start_test(user)
    session_id = UUID(start["sessionId"])
    with pytest.raises(DelfTestError, match="Sections manquantes"):
        service.finish_test(user, session_id)
