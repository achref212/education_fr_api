import random
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.constants import (
    DEFAULT_DELF_LEVEL_THRESHOLDS,
    DELF_LEVELS,
    DELF_TARGETS_BY_CLASS,
    QUIZ_CATEGORIES,
)
from app.domain.entities import DelfTestConfig, DelfTestSession, ProgressData, User
from app.domain.ports import IDelfTestRepository, IProgressRepository, IQuizRepository


class DelfTestError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DelfTestService:
    def __init__(
        self,
        delf_tests: IDelfTestRepository,
        quiz: IQuizRepository,
        progress: IProgressRepository,
    ) -> None:
        self._delf_tests = delf_tests
        self._quiz = quiz
        self._progress = progress

    def get_config(self) -> DelfTestConfig:
        return self._delf_tests.get_config()

    def update_config(
        self,
        *,
        questions_per_category: int | None = None,
        level_thresholds: list[dict[str, int | str]] | None = None,
    ) -> DelfTestConfig:
        if questions_per_category is not None and questions_per_category < 1:
            raise DelfTestError("Le nombre de questions par catégorie doit être au moins 1")
        if level_thresholds is not None and not level_thresholds:
            raise DelfTestError("Les seuils DELF ne peuvent pas être vides")
        return self._delf_tests.update_config(
            questions_per_category=questions_per_category,
            level_thresholds=level_thresholds,
        )

    def start_test(self, user: User) -> dict[str, Any]:
        if not user.class_level:
            raise DelfTestError("Niveau scolaire non défini pour cet élève")
        active = self._delf_tests.get_active_session(user.id)
        if active is not None:
            raise DelfTestError("Un test DELF est déjà en cours")
        config = self._delf_tests.get_config()
        target = DELF_TARGETS_BY_CLASS.get(user.class_level, "A1")
        question_ids_by_category = self._sample_questions(user.class_level, config)
        session = self._delf_tests.create_session(
            user_id=user.id,
            class_level=user.class_level,
            target_delf_level=target,
            question_ids_by_category=question_ids_by_category,
        )
        return self._build_start_response(session)

    def get_active_test(self, user: User) -> dict[str, Any] | None:
        session = self._delf_tests.get_active_session(user.id)
        if session is None:
            return None
        return self._build_start_response(session)

    def get_session(self, user: User, session_id: UUID) -> dict[str, Any]:
        session = self._require_session(user, session_id)
        return self._build_session_state(session)

    def submit_section(
        self,
        user: User,
        session_id: UUID,
        category: str,
        answers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if category not in QUIZ_CATEGORIES:
            raise DelfTestError("Catégorie invalide")
        session = self._require_session(user, session_id)
        if session.status != "in_progress":
            raise DelfTestError("Ce test n'est plus actif")
        if category in session.category_scores:
            raise DelfTestError(f"La section {category} a déjà été soumise")
        expected_ids = set(session.question_ids_by_category.get(category, []))
        if not expected_ids:
            raise DelfTestError(f"Aucune question pour la catégorie {category}")
        if len(answers) != len(expected_ids):
            raise DelfTestError("Nombre de réponses incorrect pour cette section")
        existing_ids = {a.get("questionId") for a in session.answers}
        graded: list[dict[str, Any]] = []
        correct_count = 0
        for item in answers:
            question_id_str = str(item.get("questionId", ""))
            if question_id_str not in expected_ids:
                raise DelfTestError("Question hors section")
            if question_id_str in existing_ids:
                raise DelfTestError("Question déjà répondue")
            question = self._quiz.get(UUID(question_id_str))
            if question is None:
                raise DelfTestError("Question introuvable")
            selected_index = int(item.get("selectedIndex", -1))
            time_ms = int(item.get("timeMs", 0))
            is_correct = selected_index == question.correct_index
            if is_correct:
                correct_count += 1
            graded.append(
                {
                    "questionId": question_id_str,
                    "category": category,
                    "selectedIndex": selected_index,
                    "isCorrect": is_correct,
                    "timeMs": time_ms,
                }
            )
        category_score = int(round(correct_count / len(expected_ids) * 100))
        all_answers = list(session.answers) + graded
        category_scores = dict(session.category_scores)
        category_scores[category] = category_score
        updated = self._delf_tests.update_session(
            session_id,
            answers=all_answers,
            category_scores=category_scores,
        )
        if updated is None:
            raise DelfTestError("Session introuvable")
        return {
            "sessionId": str(updated.id),
            "category": category,
            "score": category_score,
            "correctCount": correct_count,
            "totalQuestions": len(expected_ids),
            "submittedCategories": list(category_scores.keys()),
            "remainingCategories": [
                c for c in QUIZ_CATEGORIES if c not in category_scores
            ],
        }

    def finish_test(self, user: User, session_id: UUID) -> dict[str, Any]:
        session = self._require_session(user, session_id)
        if session.status != "in_progress":
            raise DelfTestError("Ce test n'est plus actif")
        missing = [c for c in QUIZ_CATEGORIES if c not in session.category_scores]
        if missing:
            raise DelfTestError(
                f"Sections manquantes : {', '.join(missing)}"
            )
        overall, achieved = self._compute_levels(session)
        now = datetime.now(timezone.utc)
        updated = self._delf_tests.update_session(
            session_id,
            status="completed",
            overall_score=overall,
            achieved_delf_level=achieved,
            finished_at=now,
        )
        if updated is None:
            raise DelfTestError("Session introuvable")
        self._sync_progress(user.id, updated)
        return self.get_results(user, session_id)

    def get_results(self, user: User, session_id: UUID) -> dict[str, Any]:
        session = self._require_session(user, session_id)
        if session.status != "completed":
            raise DelfTestError("Les résultats ne sont disponibles qu'après la fin du test")
        return self._build_results(session, include_explanations=True)

    def list_history(self, user: User) -> list[dict[str, Any]]:
        sessions = self._delf_tests.list_sessions_for_user(user.id)
        return [
            self._build_history_item(s)
            for s in sessions
            if s.status == "completed"
        ]

    def list_student_history(self, student_id: UUID) -> list[dict[str, Any]]:
        sessions = self._delf_tests.list_sessions_for_user(student_id)
        return [
            self._build_history_item(s)
            for s in sessions
            if s.status == "completed"
        ]

    def list_all_sessions(
        self,
        *,
        user_id: UUID | None = None,
        class_level: str | None = None,
        status: str | None = None,
    ) -> list[DelfTestSession]:
        return self._delf_tests.list_all_sessions(
            user_id=user_id,
            class_level=class_level,
            status=status,
        )

    def get_admin_session(self, session_id: UUID) -> dict[str, Any]:
        session = self._delf_tests.get_session(session_id)
        if session is None:
            raise DelfTestError("Session introuvable")
        if session.status == "completed":
            return self._build_results(session, include_explanations=True)
        return self._build_session_state(session)

    def _sample_questions(
        self, class_level: str, config: DelfTestConfig
    ) -> dict[str, list[str]]:
        count = config.questions_per_category
        result: dict[str, list[str]] = {}
        for category in QUIZ_CATEGORIES:
            pool = self._quiz.list_by_level_and_category(class_level, category)
            if len(pool) < count:
                raise DelfTestError(
                    f"Pas assez de questions {category} pour {class_level} "
                    f"({len(pool)}/{count} requis)"
                )
            selected = random.sample(pool, count)
            result[category] = [str(q.id) for q in selected]
        return result

    def _compute_levels(self, session: DelfTestSession) -> tuple[int, str]:
        config = self._delf_tests.get_config()
        thresholds = config.level_thresholds or list(DEFAULT_DELF_LEVEL_THRESHOLDS)
        scores = list(session.category_scores.values())
        overall = int(round(sum(scores) / len(scores))) if scores else 0
        achieved = "A1"
        for band in thresholds:
            min_overall = int(band.get("minOverall", 0))
            min_category = int(band.get("minCategory", 0))
            level = str(band.get("level", "A1"))
            if overall >= min_overall and all(s >= min_category for s in scores):
                achieved = level
                break
        return overall, achieved

    def _compare_to_target(self, target: str, achieved: str) -> str:
        order = {level: index for index, level in enumerate(DELF_LEVELS)}
        target_idx = order.get(target, 0)
        achieved_idx = order.get(achieved, 0)
        if achieved_idx > target_idx:
            return "above"
        if achieved_idx < target_idx:
            return "below"
        return "on_track"

    def _sync_progress(self, user_id: UUID, session: DelfTestSession) -> None:
        data = self._progress.get_for_user(user_id)
        quiz_scores = dict(data.quiz_scores)
        for category, score in session.category_scores.items():
            existing = list(quiz_scores.get(category, []))
            existing.append(score)
            quiz_scores[category] = existing
        updated = ProgressData(
            lessons_completed=list(data.lessons_completed),
            quiz_scores=quiz_scores,
            exercise_scores=dict(data.exercise_scores),
        )
        self._progress.upsert_for_user(user_id, updated)

    def _require_session(self, user: User, session_id: UUID) -> DelfTestSession:
        session = self._delf_tests.get_session(session_id)
        if session is None:
            raise DelfTestError("Session introuvable")
        if session.user_id != user.id and user.role not in ("admin", "prof", "school"):
            raise DelfTestError("Accès refusé")
        return session

    def _sanitize_questions(self, question_ids: list[str]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for question_id in question_ids:
            question = self._quiz.get(UUID(question_id))
            if question is None:
                continue
            result.append(
                {
                    "id": str(question.id),
                    "question": question.question,
                    "options": question.options,
                    "category": question.category,
                    "level": question.level,
                }
            )
        return result

    def _build_start_response(self, session: DelfTestSession) -> dict[str, Any]:
        sections = []
        for category in QUIZ_CATEGORIES:
            ids = session.question_ids_by_category.get(category, [])
            sections.append(
                {
                    "category": category,
                    "questions": self._sanitize_questions(ids),
                    "submitted": category in session.category_scores,
                    "score": session.category_scores.get(category),
                }
            )
        return {
            "sessionId": str(session.id),
            "classLevel": session.class_level,
            "targetDelfLevel": session.target_delf_level,
            "status": session.status,
            "sections": sections,
            "submittedCategories": list(session.category_scores.keys()),
        }

    def _build_session_state(self, session: DelfTestSession) -> dict[str, Any]:
        base = self._build_start_response(session)
        base["overallScore"] = session.overall_score
        base["achievedDelfLevel"] = session.achieved_delf_level
        base["startedAt"] = session.started_at.isoformat() if session.started_at else None
        base["finishedAt"] = session.finished_at.isoformat() if session.finished_at else None
        return base

    def _build_history_item(self, session: DelfTestSession) -> dict[str, Any]:
        comparison = self._compare_to_target(
            session.target_delf_level,
            session.achieved_delf_level or "A1",
        )
        return {
            "sessionId": str(session.id),
            "classLevel": session.class_level,
            "targetDelfLevel": session.target_delf_level,
            "achievedDelfLevel": session.achieved_delf_level,
            "overallScore": session.overall_score,
            "categoryScores": session.category_scores,
            "comparisonToTarget": comparison,
            "finishedAt": session.finished_at.isoformat() if session.finished_at else None,
        }

    def _build_results(
        self, session: DelfTestSession, *, include_explanations: bool
    ) -> dict[str, Any]:
        sections: list[dict[str, Any]] = []
        answers_by_question = {a["questionId"]: a for a in session.answers}
        for category in QUIZ_CATEGORIES:
            question_results: list[dict[str, Any]] = []
            for question_id in session.question_ids_by_category.get(category, []):
                question = self._quiz.get(UUID(question_id))
                answer = answers_by_question.get(question_id)
                if question is None:
                    continue
                item: dict[str, Any] = {
                    "questionId": question_id,
                    "question": question.question,
                    "options": question.options,
                    "category": category,
                    "selectedIndex": answer.get("selectedIndex") if answer else None,
                    "isCorrect": answer.get("isCorrect") if answer else False,
                    "correctIndex": question.correct_index if include_explanations else None,
                }
                if include_explanations:
                    item["explanation"] = question.explanation
                question_results.append(item)
            sections.append(
                {
                    "category": category,
                    "score": session.category_scores.get(category, 0),
                    "questions": question_results,
                }
            )
        comparison = self._compare_to_target(
            session.target_delf_level,
            session.achieved_delf_level or "A1",
        )
        return {
            "sessionId": str(session.id),
            "classLevel": session.class_level,
            "targetDelfLevel": session.target_delf_level,
            "achievedDelfLevel": session.achieved_delf_level,
            "overallScore": session.overall_score,
            "categoryScores": session.category_scores,
            "comparisonToTarget": comparison,
            "status": session.status,
            "sections": sections,
            "finishedAt": session.finished_at.isoformat() if session.finished_at else None,
        }
