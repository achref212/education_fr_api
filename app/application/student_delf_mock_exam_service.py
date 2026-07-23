from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.entities import DelfMockExam, DelfMockItem, DelfMockSection, User
from app.domain.ports import (
    IDelfMockAttemptRepository,
    IDelfMockExamRepository,
    IStudentReviewRepository,
)


class StudentDelfMockExamError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class StudentDelfMockExamService:
    def __init__(
        self,
        *,
        exams: IDelfMockExamRepository,
        attempts: IDelfMockAttemptRepository,
        reviews: IStudentReviewRepository | None = None,
    ) -> None:
        self._exams = exams
        self._attempts = attempts
        self._reviews = reviews

    def list_published_exams(self, user: User) -> list[dict[str, Any]]:
        exams = self._exams.list_exams(status="published")
        preferred_levels = _preferred_levels(user.class_level)
        if preferred_levels:
            ranked = sorted(
                exams,
                key=lambda exam: (
                    0 if exam.level in preferred_levels else 1,
                    preferred_levels.index(exam.level)
                    if exam.level in preferred_levels
                    else 99,
                    exam.track,
                    exam.updated_at,
                ),
            )
        else:
            ranked = exams
        return [self._exam_out(exam, include_sections=False) for exam in ranked]

    def get_published_exam(self, exam_id: UUID) -> dict[str, Any]:
        exam = self._require_published_exam(exam_id)
        return self._exam_out(exam, include_sections=True)

    def create_attempt(self, user: User, exam_id: UUID) -> dict[str, Any]:
        exam = self._require_published_exam(exam_id)
        attempt = self._attempts.get_active_attempt(user_id=user.id, exam_id=exam.id)
        if attempt is None:
            attempt = self._attempts.create_attempt(user_id=user.id, exam_id=exam.id)
        return self._attempt_out(attempt, exam)

    def get_attempt(self, user: User, attempt_id: UUID) -> dict[str, Any]:
        attempt = self._attempts.get_attempt(attempt_id)
        if attempt is None or attempt.user_id != user.id:
            raise StudentDelfMockExamError("Tentative d'examen blanc introuvable")
        exam = self._require_published_exam(attempt.exam_id)
        return self._attempt_out(attempt, exam)

    def submit_attempt(
        self,
        user: User,
        attempt_id: UUID,
        answers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        attempt = self._attempts.get_attempt(attempt_id)
        if attempt is None or attempt.user_id != user.id:
            raise StudentDelfMockExamError("Tentative d'examen blanc introuvable")
        exam = self._require_published_exam(attempt.exam_id)
        if attempt.status == "completed":
            return self._attempt_out(attempt, exam)
        normalized_answers = self._normalize_answers(exam, answers)
        section_scores, overall_score, wrong_items = self._score(exam, normalized_answers)
        updated = self._attempts.update_attempt(
            attempt.id,
            status="completed",
            answers=normalized_answers,
            section_scores=section_scores,
            overall_score=overall_score,
            approximate=True,
            finished_at=datetime.now(timezone.utc),
        )
        if updated is None:
            raise StudentDelfMockExamError("Tentative d'examen blanc introuvable")
        self._store_review_items(user, attempt.id, wrong_items)
        return self._attempt_out(updated, exam)

    def _require_published_exam(self, exam_id: UUID) -> DelfMockExam:
        exam = self._exams.get_exam(exam_id)
        if exam is None or exam.status != "published":
            raise StudentDelfMockExamError("Examen blanc introuvable")
        return exam

    def _normalize_answers(
        self,
        exam: DelfMockExam,
        answers: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        item_ids = {str(item.id) for section in exam.sections for item in section.items}
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for answer in answers:
            item_id = str(answer.get("itemId") or "").strip()
            if item_id not in item_ids or item_id in seen:
                continue
            selected_index = answer.get("selectedIndex")
            normalized.append(
                {
                    "itemId": item_id,
                    "selectedIndex": int(selected_index)
                    if selected_index is not None
                    else None,
                    "text": str(answer.get("text") or "").strip(),
                }
            )
            seen.add(item_id)
        return normalized

    def _score(
        self,
        exam: DelfMockExam,
        answers: list[dict[str, Any]],
    ) -> tuple[dict[str, int], int, list[tuple[DelfMockSection, DelfMockItem, dict[str, Any]]]]:
        answer_map = {answer["itemId"]: answer for answer in answers}
        section_scores: dict[str, int] = {}
        wrong_items: list[tuple[DelfMockSection, DelfMockItem, dict[str, Any]]] = []
        for section in sorted(exam.sections, key=lambda item: item.section_order):
            score = 0.0
            for item in section.items:
                answer = answer_map.get(str(item.id), {"selectedIndex": None, "text": ""})
                item_score, is_wrong_objective = self._score_item(section, item, answer)
                score += item_score
                if is_wrong_objective:
                    wrong_items.append((section, item, answer))
            section_scores[section.section_type] = int(round(min(score, section.points)))
        overall = int(round(sum(section_scores.values())))
        return section_scores, min(overall, exam.total_points), wrong_items

    def _score_item(
        self,
        section: DelfMockSection,
        item: DelfMockItem,
        answer: dict[str, Any],
    ) -> tuple[float, bool]:
        correct_index = _correct_index(item)
        options = _options(item)
        if correct_index is not None and options:
            selected = answer.get("selectedIndex")
            return (float(item.points), False) if selected == correct_index else (0.0, True)
        text = str(answer.get("text") or "").strip()
        if not text:
            return 0.0, False
        words = len([part for part in text.split() if part.strip()])
        target_words = _target_words(section, item)
        completion = min(1.0, words / target_words)
        structure_bonus = 0.15 if any(mark in text for mark in (".", "?", "!")) else 0.0
        return float(item.points) * min(1.0, completion + structure_bonus), False

    def _store_review_items(
        self,
        user: User,
        attempt_id: UUID,
        wrong_items: list[tuple[DelfMockSection, DelfMockItem, dict[str, Any]]],
    ) -> None:
        if self._reviews is None:
            return
        for section, item, answer in wrong_items:
            options = _options(item)
            correct_index = _correct_index(item)
            self._reviews.upsert_wrong_answer(
                user_id=user.id,
                source_type="delf_mock_exam",
                source_id=str(attempt_id),
                question_id=str(item.id),
                category=section.title or section.section_type,
                question=item.prompt,
                options=options,
                selected_index=answer.get("selectedIndex"),
                correct_index=correct_index,
                explanation=str(item.answer_key.get("explanation") or item.rubric.get("explanation") or ""),
            )

    def _attempt_out(self, attempt, exam: DelfMockExam) -> dict[str, Any]:
        return {
            "attemptId": str(attempt.id),
            "examId": str(attempt.exam_id),
            "status": attempt.status,
            "answers": attempt.answers,
            "sectionScores": attempt.section_scores,
            "overallScore": attempt.overall_score,
            "approximate": attempt.approximate,
            "resultMessage": (
                f"Ton score estimé est d’environ {attempt.overall_score}/100"
                if attempt.overall_score is not None
                else None
            ),
            "startedAt": attempt.started_at.isoformat(),
            "finishedAt": attempt.finished_at.isoformat() if attempt.finished_at else None,
            "exam": self._exam_out(exam, include_sections=True),
        }

    def _exam_out(self, exam: DelfMockExam, *, include_sections: bool) -> dict[str, Any]:
        return {
            "id": str(exam.id),
            "track": exam.track,
            "level": exam.level,
            "title": exam.title,
            "description": exam.description,
            "status": exam.status,
            "totalDurationMinutes": exam.total_duration_minutes,
            "totalPoints": exam.total_points,
            "sourceNotes": exam.source_notes,
            "sections": [
                {
                    "id": str(section.id),
                    "examId": str(section.exam_id),
                    "sectionOrder": section.section_order,
                    "sectionType": section.section_type,
                    "title": section.title,
                    "durationMinutes": section.duration_minutes,
                    "points": section.points,
                    "instructions": section.instructions,
                    "audioUrl": section.audio_url,
                    "rubric": section.rubric,
                    "metadata": section.metadata,
                    "items": [
                        {
                            "id": str(item.id),
                            "sectionId": str(item.section_id),
                            "itemOrder": item.item_order,
                            "title": item.title,
                            "prompt": item.prompt,
                            "points": item.points,
                            "content": item.content,
                            "answerKey": item.answer_key,
                            "rubric": item.rubric,
                            "metadata": item.metadata,
                        }
                        for item in section.items
                    ],
                }
                for section in exam.sections
            ]
            if include_sections
            else [],
            "assets": [
                {
                    "id": str(asset.id),
                    "examId": str(asset.exam_id),
                    "assetType": asset.asset_type,
                    "title": asset.title,
                    "url": asset.url,
                    "metadata": asset.metadata,
                    "createdAt": asset.created_at.isoformat(),
                }
                for asset in exam.assets
            ],
            "createdAt": exam.created_at.isoformat(),
            "updatedAt": exam.updated_at.isoformat(),
        }


def _options(item: DelfMockItem) -> list[str]:
    raw = item.content.get("options") or item.metadata.get("options") or []
    if isinstance(raw, list):
        return [str(option) for option in raw]
    return []


def _correct_index(item: DelfMockItem) -> int | None:
    for key in ("correctIndex", "correct_index"):
        value = item.answer_key.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def _target_words(section: DelfMockSection, item: DelfMockItem) -> int:
    for source in (item.rubric, item.metadata, item.content, section.rubric, section.metadata):
        for key in ("targetWords", "minWords", "minimumWords"):
            value = source.get(key)
            if value is not None:
                try:
                    return max(1, int(value))
                except (TypeError, ValueError):
                    pass
    return 60 if section.section_type == "writing" else 35 if section.section_type == "speaking" else 20


def _preferred_levels(class_level: str | None) -> list[str]:
    if not class_level:
        return []
    lower = class_level.lower()
    if any(value in lower for value in ("1", "2", "3", "4", "5")):
        return ["A1.1", "A1"]
    if any(value in lower for value in ("6", "7", "8", "9")):
        return ["A1", "A2"]
    return ["A2", "B1", "B2"]
