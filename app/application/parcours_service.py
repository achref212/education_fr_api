from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.application.difficulty_service import DifficultyService
from app.application.progress_service import ProgressService
from app.application.student_stats_service import StudentStatsService
from app.domain.constants import MIN_STEP_SCORE_TO_UNLOCK
from app.domain.entities import (
    LearningPathStep,
    ParcoursSummary,
    ProgressData,
    StudentStepProgress,
    User,
)
from app.domain.ports import (
    IDelfTestRepository,
    ILearningPathRepository,
    IStudentProgressRepository,
    IUserRepository,
)


class ParcoursError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ParcoursService:
    def __init__(
        self,
        paths: ILearningPathRepository,
        student_progress: IStudentProgressRepository,
        stats_service: StudentStatsService,
        progress_service: ProgressService,
        difficulty_service: DifficultyService,
        delf_tests: IDelfTestRepository | None = None,
        users: IUserRepository | None = None,
    ) -> None:
        self._paths = paths
        self._student_progress = student_progress
        self._stats = stats_service
        self._progress = progress_service
        self._difficulty = difficulty_service
        self._delf_tests = delf_tests
        self._users = users

    def _resolve_class_level(self, user: User) -> str:
        if user.class_level:
            return user.class_level
        raise ParcoursError("L'élève n'a pas de niveau scolaire défini")

    def get_parcours_for_user(self, user: User) -> dict:
        class_level = self._resolve_class_level(user)
        path = self._resolve_learning_path(user, class_level)
        if path is None:
            raise ParcoursError(
                f"Aucun parcours disponible pour {class_level}"
            )
        steps = self._paths.list_steps(path.id)
        progress_map = {
            p.step_id: p
            for p in self._student_progress.list_step_progress(user.id)
        }
        resolved_steps = self._resolve_step_statuses(steps, progress_map, user.id)
        stats = self._stats.get_or_create(user.id)
        return {
            "path": path,
            "steps": resolved_steps,
            "stats": stats,
        }

    def get_summary(self, user: User) -> ParcoursSummary:
        data = self.get_parcours_for_user(user)
        path = data["path"]
        steps: list[dict] = data["steps"]
        stats = data["stats"]
        total_steps = len(steps)
        completed_steps = sum(
            1 for s in steps if s["status"] == "completed"
        )
        completion_percent = (
            (completed_steps / total_steps * 100) if total_steps else 0.0
        )
        next_step = next(
            (s for s in steps if s["status"] in ("available", "in_progress")),
            None,
        )
        return ParcoursSummary(
            class_level=path.class_level,
            delf_target_level=path.delf_target_level,
            completion_percent=round(completion_percent, 1),
            total_steps=total_steps,
            completed_steps=completed_steps,
            total_xp=stats.total_xp,
            current_streak=stats.current_streak,
            preferred_difficulty=stats.preferred_difficulty,
            next_step_id=next_step["step"].id if next_step else None,
            next_step_title=next_step["step"].title if next_step else None,
        )

    def start_step(self, user: User, step_id: UUID) -> StudentStepProgress:
        step = self._paths.get_step(step_id)
        if step is None:
            raise ParcoursError("Étape introuvable")
        parcours = self.get_parcours_for_user(user)
        step_entry = next(
            (s for s in parcours["steps"] if s["step"].id == step_id),
            None,
        )
        if step_entry is None:
            raise ParcoursError("Étape hors parcours de l'élève")
        if step_entry["status"] == "locked":
            raise ParcoursError("Étape verrouillée")
        if step_entry["status"] == "completed":
            raise ParcoursError("Étape déjà terminée")
        now = datetime.now(timezone.utc)
        existing = step_entry["progress"]
        progress = StudentStepProgress(
            id=existing.id if existing else uuid4(),
            user_id=user.id,
            step_id=step_id,
            status="in_progress",
            score=existing.score if existing else None,
            attempts=(existing.attempts if existing else 0) + 1,
            completed_at=None,
            updated_at=now,
        )
        return self._student_progress.upsert_step_progress(progress)

    def complete_step(
        self, user: User, step_id: UUID, score: int
    ) -> dict:
        if score < 0 or score > 100:
            raise ParcoursError("Le score doit être entre 0 et 100")
        step = self._paths.get_step(step_id)
        if step is None:
            raise ParcoursError("Étape introuvable")
        parcours = self.get_parcours_for_user(user)
        step_entry = next(
            (s for s in parcours["steps"] if s["step"].id == step_id),
            None,
        )
        if step_entry is None:
            raise ParcoursError("Étape hors parcours de l'élève")
        if step_entry["status"] == "locked":
            raise ParcoursError("Étape verrouillée")
        now = datetime.now(timezone.utc)
        passed = score >= MIN_STEP_SCORE_TO_UNLOCK
        status = "completed" if passed else "available"
        existing = step_entry["progress"]
        progress = StudentStepProgress(
            id=existing.id if existing else uuid4(),
            user_id=user.id,
            step_id=step_id,
            status=status,
            score=score,
            attempts=(existing.attempts if existing else 0) + 1,
            completed_at=now if passed else None,
            updated_at=now,
        )
        saved = self._student_progress.upsert_step_progress(progress)
        xp_earned = 0
        if passed:
            xp_earned = self._stats.calculate_step_xp(step.xp_reward, score)
            self._stats.record_activity(user.id, xp_earned)
            self._sync_legacy_progress(user.id, step, score)
        summary = self.get_summary(user)
        next_step_id = None
        if passed:
            steps = self._paths.list_steps(step.path_id)
            ordered = sorted(steps, key=lambda s: s.step_order)
            current_index = next(
                i for i, s in enumerate(ordered) if s.id == step_id
            )
            if current_index + 1 < len(ordered):
                next_step_id = ordered[current_index + 1].id
        return {
            "progress": saved,
            "score": score,
            "xpEarned": xp_earned,
            "passed": passed,
            "nextStepId": next_step_id,
            "parcoursPercent": summary.completion_percent,
        }

    def set_difficulty(self, user: User, difficulty: str) -> dict:
        stats = self._stats.set_preferred_difficulty(user.id, difficulty)
        return {"preferredDifficulty": stats.preferred_difficulty}

    def _resolve_learning_path(self, user: User, class_level: str):
        if user.assigned_learning_path_id is not None:
            assigned = self._paths.get(user.assigned_learning_path_id)
            if assigned is not None and assigned.is_active:
                return assigned

        if self._delf_tests is not None:
            latest = next(
                (
                    session
                    for session in self._delf_tests.list_sessions_for_user(user.id)
                    if session.status == "completed"
                ),
                None,
            )
            if latest is not None:
                matched = self._paths.find_match(
                    class_level=class_level,
                    delf_level=latest.achieved_delf_level,
                    score=latest.overall_score,
                )
                if matched is not None:
                    if self._users is not None:
                        self._users.assign_learning_path(user.id, matched.id)
                    return matched

        return self._paths.get_default_for_class_level(class_level)

    def _resolve_step_statuses(
        self,
        steps: list[LearningPathStep],
        progress_map: dict[UUID, StudentStepProgress],
        user_id: UUID,
    ) -> list[dict]:
        ordered = sorted(steps, key=lambda s: s.step_order)
        result: list[dict] = []
        previous_completed = True
        for step in ordered:
            progress = progress_map.get(step.id)
            if progress and progress.status == "completed":
                status = "completed"
            elif progress and progress.status == "in_progress":
                status = "in_progress"
            elif previous_completed:
                status = "available"
            else:
                status = "locked"
            if step.required_step_id is not None:
                required = progress_map.get(step.required_step_id)
                if required is None or required.status != "completed":
                    status = "locked"
                elif required.score is not None and required.score < MIN_STEP_SCORE_TO_UNLOCK:
                    status = "locked"
            if status == "available" and progress is None:
                now = datetime.now(timezone.utc)
                progress = StudentStepProgress(
                    id=uuid4(),
                    user_id=user_id,
                    step_id=step.id,
                    status="available",
                    score=None,
                    attempts=0,
                    completed_at=None,
                    updated_at=now,
                )
                progress = self._student_progress.upsert_step_progress(progress)
                progress_map[step.id] = progress
            result.append(
                {
                    "step": step,
                    "status": status,
                    "progress": progress_map.get(step.id),
                }
            )
            previous_completed = status == "completed"
        return result

    def _sync_legacy_progress(
        self, user_id: UUID, step: LearningPathStep, score: int
    ) -> None:
        data = self._progress.get(user_id)
        if step.step_type == "lesson" and step.lesson_id:
            lesson_id = str(step.lesson_id)
            if lesson_id not in data.lessons_completed:
                data.lessons_completed.append(lesson_id)
        elif step.step_type == "quiz" and step.quiz_category:
            category = step.quiz_category
            if category not in data.quiz_scores:
                data.quiz_scores[category] = []
            data.quiz_scores[category].append(score)
        self._progress.put(user_id, data)
