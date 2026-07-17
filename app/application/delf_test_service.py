import random
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.constants import (
    DEFAULT_DELF_LEVEL_THRESHOLDS,
    CLASS_LEVELS,
    DELF_LEVELS,
    DELF_TARGETS_BY_CLASS,
    QUIZ_CATEGORIES,
)
from app.domain.entities import DelfTestConfig, DelfTestSession, ProgressData, User
from app.domain.ports import (
    IDelfTestRepository,
    ILearningPathRepository,
    IProgressRepository,
    IQuizRepository,
    IUserRepository,
)


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
        paths: ILearningPathRepository | None = None,
        users: IUserRepository | None = None,
    ) -> None:
        self._delf_tests = delf_tests
        self._quiz = quiz
        self._progress = progress
        self._paths = paths
        self._users = users

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
        normalized_thresholds = (
            self._normalize_thresholds(level_thresholds)
            if level_thresholds is not None
            else None
        )
        return self._delf_tests.update_config(
            questions_per_category=questions_per_category,
            level_thresholds=normalized_thresholds,
        )

    def start_test(self, user: User) -> dict[str, Any]:
        if not user.class_level:
            raise DelfTestError("Niveau scolaire non défini pour cet élève")
        active = self._delf_tests.get_active_session(user.id)
        if active is not None:
            raise DelfTestError("Un test DELF est déjà en cours")
        config = self._delf_tests.get_config()
        target = DELF_TARGETS_BY_CLASS.get(user.class_level, "A1")
        template = self._delf_tests.get_active_template_for_class(user.class_level)
        question_ids_by_category = (
            dict(template.question_ids_by_category)
            if template is not None
            else self._sample_questions(user.class_level, config)
        )
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
        self._assign_parcours_from_result(user, updated)
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

    def list_templates(self) -> list[dict[str, Any]]:
        return [self._build_template_out(t) for t in self._delf_tests.list_templates()]

    def get_template(self, template_id: UUID) -> dict[str, Any]:
        template = self._delf_tests.get_template(template_id)
        if template is None:
            raise DelfTestError("Modèle introuvable")
        return self._build_template_out(template, include_questions=True)

    def create_template(
        self,
        *,
        name: str,
        description: str | None,
        class_level: str,
        target_delf_level: str,
        is_active: bool,
        question_ids_by_category: dict[str, list[str]],
    ) -> dict[str, Any]:
        normalized = self._validate_template_payload(
            name=name,
            class_level=class_level,
            target_delf_level=target_delf_level,
            question_ids_by_category=question_ids_by_category,
        )
        template = self._delf_tests.create_template(
            name=name.strip(),
            description=description.strip() if description else None,
            class_level=class_level,
            target_delf_level=target_delf_level,
            is_active=is_active,
            question_ids_by_category=normalized,
        )
        return self._build_template_out(template, include_questions=True)

    def update_template(
        self,
        template_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        class_level: str | None = None,
        target_delf_level: str | None = None,
        is_active: bool | None = None,
        question_ids_by_category: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        current = self._delf_tests.get_template(template_id)
        if current is None:
            raise DelfTestError("Modèle introuvable")
        next_name = name if name is not None else current.name
        next_class = class_level if class_level is not None else current.class_level
        next_target = (
            target_delf_level
            if target_delf_level is not None
            else current.target_delf_level
        )
        next_questions = (
            question_ids_by_category
            if question_ids_by_category is not None
            else current.question_ids_by_category
        )
        normalized = self._validate_template_payload(
            name=next_name,
            class_level=next_class,
            target_delf_level=next_target,
            question_ids_by_category=next_questions,
        )
        updated = self._delf_tests.update_template(
            template_id,
            name=next_name.strip(),
            description=description.strip() if description else None,
            class_level=next_class,
            target_delf_level=next_target,
            is_active=is_active,
            question_ids_by_category=normalized,
        )
        if updated is None:
            raise DelfTestError("Modèle introuvable")
        return self._build_template_out(updated, include_questions=True)

    def disable_template(self, template_id: UUID) -> dict[str, Any]:
        updated = self._delf_tests.update_template(template_id, is_active=False)
        if updated is None:
            raise DelfTestError("Modèle introuvable")
        return self._build_template_out(updated)

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
        thresholds = self._normalize_thresholds(
            config.level_thresholds or list(DEFAULT_DELF_LEVEL_THRESHOLDS)
        )
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

    def _normalize_thresholds(
        self, thresholds: list[dict[str, int | str]]
    ) -> list[dict[str, int | str]]:
        if not thresholds:
            raise DelfTestError("Les seuils DELF ne peuvent pas être vides")
        normalized: list[dict[str, int | str]] = []
        seen: set[str] = set()
        for band in thresholds:
            level = str(band.get("level", "")).strip()
            if level not in DELF_LEVELS:
                raise DelfTestError(f"Niveau DELF invalide : {level or '—'}")
            if level in seen:
                raise DelfTestError(f"Niveau DELF dupliqué : {level}")
            min_overall = int(band.get("minOverall", 0))
            min_category = int(band.get("minCategory", 0))
            if not (0 <= min_overall <= 100 and 0 <= min_category <= 100):
                raise DelfTestError("Les seuils DELF doivent être entre 0 et 100")
            seen.add(level)
            normalized.append(
                {
                    "level": level,
                    "minOverall": min_overall,
                    "minCategory": min_category,
                }
            )
        return sorted(
            normalized,
            key=lambda band: (
                int(band["minOverall"]),
                int(band["minCategory"]),
                DELF_LEVELS.index(str(band["level"])),
            ),
            reverse=True,
        )

    def _validate_template_payload(
        self,
        *,
        name: str,
        class_level: str,
        target_delf_level: str,
        question_ids_by_category: dict[str, list[str]],
    ) -> dict[str, list[str]]:
        if not name.strip():
            raise DelfTestError("Le nom du modèle est obligatoire")
        if class_level not in CLASS_LEVELS:
            raise DelfTestError("Niveau scolaire invalide")
        if target_delf_level not in DELF_LEVELS:
            raise DelfTestError("Objectif DELF invalide")
        normalized: dict[str, list[str]] = {}
        seen_ids: set[str] = set()
        for category in QUIZ_CATEGORIES:
            raw_ids = question_ids_by_category.get(category, [])
            if not raw_ids:
                raise DelfTestError(f"La catégorie {category} doit contenir au moins une question")
            normalized[category] = []
            for question_id in raw_ids:
                question_id_str = str(question_id)
                if question_id_str in seen_ids:
                    raise DelfTestError("Une question ne peut pas être utilisée deux fois")
                try:
                    question_uuid = UUID(question_id_str)
                except ValueError as exc:
                    raise DelfTestError("Identifiant de question invalide") from exc
                question = self._quiz.get(question_uuid)
                if question is None:
                    raise DelfTestError("Question introuvable")
                if question.category != category:
                    raise DelfTestError(
                        f"La question {question_id_str} n'appartient pas à {category}"
                    )
                normalized[category].append(question_id_str)
                seen_ids.add(question_id_str)
        return normalized

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

    def _assign_parcours_from_result(
        self, user: User, session: DelfTestSession
    ) -> None:
        if self._paths is None or self._users is None:
            return
        matched = self._paths.find_match(
            class_level=session.class_level,
            delf_level=session.achieved_delf_level,
            score=session.overall_score,
        )
        if matched is not None:
            self._users.assign_learning_path(user.id, matched.id)

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

    def _build_template_out(
        self, template, *, include_questions: bool = False
    ) -> dict[str, Any]:
        sections: list[dict[str, Any]] = []
        total_questions = 0
        for category in QUIZ_CATEGORIES:
            ids = template.question_ids_by_category.get(category, [])
            total_questions += len(ids)
            section: dict[str, Any] = {
                "category": category,
                "questionIds": ids,
                "questionCount": len(ids),
            }
            if include_questions:
                section["questions"] = self._sanitize_questions(ids)
            sections.append(section)
        return {
            "id": str(template.id),
            "name": template.name,
            "description": template.description,
            "classLevel": template.class_level,
            "targetDelfLevel": template.target_delf_level,
            "isActive": template.is_active,
            "questionIdsByCategory": template.question_ids_by_category,
            "sections": sections,
            "totalQuestions": total_questions,
            "createdAt": template.created_at.isoformat(),
            "updatedAt": template.updated_at.isoformat(),
        }
