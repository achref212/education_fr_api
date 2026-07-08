from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.difficulty_service import DifficultyService
from app.application.parcours_service import ParcoursError, ParcoursService
from app.application.progress_service import ProgressService
from app.application.student_stats_service import StudentStatsService
from app.domain.entities import (
    LearningPath,
    LearningPathStep,
    ProgressData,
    StudentStats,
    StudentStepProgress,
    User,
)


@dataclass
class FakeLearningPathRepo:
    path: LearningPath | None = None
    steps: list[LearningPathStep] = field(default_factory=list)

    def get_by_class_level(self, class_level: str) -> LearningPath | None:
        if self.path and self.path.class_level == class_level:
            return self.path
        return None

    def get(self, path_id: UUID) -> LearningPath | None:
        return self.path if self.path and self.path.id == path_id else None

    def list_all(self) -> list[LearningPath]:
        return [self.path] if self.path else []

    def list_steps(self, path_id: UUID) -> list[LearningPathStep]:
        return [s for s in self.steps if s.path_id == path_id]

    def get_step(self, step_id: UUID) -> LearningPathStep | None:
        return next((s for s in self.steps if s.id == step_id), None)

    def create_path(self, **kwargs) -> LearningPath:
        raise NotImplementedError

    def update_path(self, *args, **kwargs) -> LearningPath | None:
        raise NotImplementedError

    def delete_path(self, path_id: UUID) -> bool:
        raise NotImplementedError

    def create_step(self, **kwargs) -> LearningPathStep:
        raise NotImplementedError

    def update_step(self, *args, **kwargs) -> LearningPathStep | None:
        raise NotImplementedError

    def delete_step(self, step_id: UUID) -> bool:
        raise NotImplementedError


@dataclass
class FakeStudentProgressRepo:
    stats: dict[UUID, StudentStats] = field(default_factory=dict)
    step_progress: dict[tuple[UUID, UUID], StudentStepProgress] = field(default_factory=dict)

    def get_stats(self, user_id: UUID) -> StudentStats | None:
        return self.stats.get(user_id)

    def upsert_stats(self, stats: StudentStats) -> StudentStats:
        self.stats[stats.user_id] = stats
        return stats

    def get_step_progress(
        self, user_id: UUID, step_id: UUID
    ) -> StudentStepProgress | None:
        return self.step_progress.get((user_id, step_id))

    def list_step_progress(self, user_id: UUID) -> list[StudentStepProgress]:
        return [p for (uid, _), p in self.step_progress.items() if uid == user_id]

    def upsert_step_progress(
        self, progress: StudentStepProgress
    ) -> StudentStepProgress:
        self.step_progress[(progress.user_id, progress.step_id)] = progress
        return progress


@dataclass
class FakeProgressRepo:
    data: dict[UUID, ProgressData] = field(default_factory=dict)

    def get_for_user(self, user_id: UUID) -> ProgressData:
        return self.data.get(user_id, ProgressData.empty())

    def upsert_for_user(self, user_id: UUID, data: ProgressData) -> None:
        self.data[user_id] = data


def _student(class_level: str = "5ème année") -> User:
    return User(
        id=uuid4(),
        email="student@test.com",
        first_name="Test",
        last_name="Student",
        level="debutant",
        created_at=datetime.now(timezone.utc),
        class_level=class_level,
    )


def _build_service(
    path_repo: FakeLearningPathRepo,
    progress_repo: FakeStudentProgressRepo,
    legacy_repo: FakeProgressRepo,
) -> ParcoursService:
    stats_service = StudentStatsService(progress_repo)
    return ParcoursService(
        paths=path_repo,
        student_progress=progress_repo,
        stats_service=stats_service,
        progress_service=ProgressService(legacy_repo),
        difficulty_service=DifficultyService(),
    )


def test_parcours_unlocks_first_step() -> None:
    now = datetime.now(timezone.utc)
    path_id = uuid4()
    step1_id = uuid4()
    step2_id = uuid4()
    path = LearningPath(
        id=path_id,
        class_level="5ème année",
        title="Parcours",
        delf_target_level="A1+",
        created_at=now,
    )
    steps = [
        LearningPathStep(
            id=step1_id,
            path_id=path_id,
            step_order=1,
            step_type="lesson",
            title="Step 1",
            xp_reward=10,
            created_at=now,
        ),
        LearningPathStep(
            id=step2_id,
            path_id=path_id,
            step_order=2,
            step_type="quiz",
            title="Step 2",
            xp_reward=15,
            created_at=now,
            quiz_category="Grammaire",
            required_step_id=step1_id,
        ),
    ]
    path_repo = FakeLearningPathRepo(path=path, steps=steps)
    student_progress_repo = FakeStudentProgressRepo()
    legacy_repo = FakeProgressRepo()
    svc = _build_service(path_repo, student_progress_repo, legacy_repo)
    student = _student()
    data = svc.get_parcours_for_user(student)
    statuses = {s["step"].id: s["status"] for s in data["steps"]}
    assert statuses[step1_id] == "available"
    assert statuses[step2_id] == "locked"


def test_complete_step_unlocks_next_and_syncs_progress() -> None:
    now = datetime.now(timezone.utc)
    path_id = uuid4()
    step1_id = uuid4()
    lesson_id = uuid4()
    path = LearningPath(
        id=path_id,
        class_level="5ème année",
        title="Parcours",
        delf_target_level="A1+",
        created_at=now,
    )
    steps = [
        LearningPathStep(
            id=step1_id,
            path_id=path_id,
            step_order=1,
            step_type="lesson",
            title="Step 1",
            xp_reward=10,
            created_at=now,
            lesson_id=lesson_id,
        ),
    ]
    path_repo = FakeLearningPathRepo(path=path, steps=steps)
    student_progress_repo = FakeStudentProgressRepo()
    legacy_repo = FakeProgressRepo()
    svc = _build_service(path_repo, student_progress_repo, legacy_repo)
    student = _student()
    svc.start_step(student, step1_id)
    result = svc.complete_step(student, step1_id, 80)
    assert result["passed"] is True
    assert result["xpEarned"] > 0
    assert str(lesson_id) in legacy_repo.data[student.id].lessons_completed
    stats = student_progress_repo.stats[student.id]
    assert stats.total_xp > 0


def test_complete_step_fails_below_threshold() -> None:
    now = datetime.now(timezone.utc)
    path_id = uuid4()
    step1_id = uuid4()
    path = LearningPath(
        id=path_id,
        class_level="5ème année",
        title="Parcours",
        delf_target_level="A1+",
        created_at=now,
    )
    steps = [
        LearningPathStep(
            id=step1_id,
            path_id=path_id,
            step_order=1,
            step_type="lesson",
            title="Step 1",
            xp_reward=10,
            created_at=now,
        ),
    ]
    path_repo = FakeLearningPathRepo(path=path, steps=steps)
    student_progress_repo = FakeStudentProgressRepo()
    legacy_repo = FakeProgressRepo()
    svc = _build_service(path_repo, student_progress_repo, legacy_repo)
    student = _student()
    svc.start_step(student, step1_id)
    result = svc.complete_step(student, step1_id, 40)
    assert result["passed"] is False
    assert result["xpEarned"] == 0
    stats = student_progress_repo.stats.get(student.id)
    assert stats is None or stats.total_xp == 0


def test_missing_class_level_raises() -> None:
    path_repo = FakeLearningPathRepo()
    student_progress_repo = FakeStudentProgressRepo()
    legacy_repo = FakeProgressRepo()
    svc = _build_service(path_repo, student_progress_repo, legacy_repo)
    student = _student()
    student.class_level = None
    with pytest.raises(ParcoursError):
        svc.get_parcours_for_user(student)
