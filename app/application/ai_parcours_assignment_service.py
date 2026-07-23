from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.api.schemas.ai_content import AIContentGenerateIn, AILearningPathOut
from app.application.ai_content_service import AIContentError, AIContentService
from app.domain.constants import QUIZ_CATEGORIES
from app.domain.entities import DelfTestSession, User
from app.domain.ports import (
    ILearningPathRepository,
    ILessonRepository,
    IQuizRepository,
    IStoryRepository,
    IUserRepository,
)


class AIParcoursAssignmentError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class AIParcoursAssignmentResult:
    path_id: UUID
    generated_by_ai: bool
    status: str


class AIParcoursAssignmentService:
    def __init__(
        self,
        *,
        ai: AIContentService,
        paths: ILearningPathRepository,
        lessons: ILessonRepository,
        stories: IStoryRepository,
        quizzes: IQuizRepository,
        users: IUserRepository,
    ) -> None:
        self._ai = ai
        self._paths = paths
        self._lessons = lessons
        self._stories = stories
        self._quizzes = quizzes
        self._users = users

    def assign_for_completed_test(
        self,
        user: User,
        session: DelfTestSession,
    ) -> AIParcoursAssignmentResult:
        if session.status != "completed":
            raise AIParcoursAssignmentError("Le test DELF doit être terminé.")
        profile = self._student_profile(session)
        weak_categories = profile["weakCategories"]
        body = AIContentGenerateIn(
            classLevel=session.class_level,
            targetDelfLevel=session.achieved_delf_level or session.target_delf_level,
            category=weak_categories[0] if weak_categories else QUIZ_CATEGORIES[0],
            count=6,
            difficulty=self._difficulty_for_score(session.overall_score),
        )
        try:
            draft = self._ai.generate_learning_path(
                body,
                reference_context=self._reference_context(session),
                student_profile=profile,
            )
        except AIContentError as exc:
            raise AIParcoursAssignmentError(exc.message) from exc
        path_id = self._persist_draft(draft)
        self._users.assign_learning_path(user.id, path_id)
        return AIParcoursAssignmentResult(
            path_id=path_id,
            generated_by_ai=True,
            status="ai_generated",
        )

    def _persist_draft(self, draft: AILearningPathOut) -> UUID:
        path = self._paths.create_path(
            class_level=draft.path.classLevel,
            title=draft.path.title,
            description=draft.path.description,
            delf_target_level=draft.path.delfTargetLevel,
            min_score=draft.path.minScore,
            max_score=draft.path.maxScore,
            is_default=False,
        )
        lesson_ids: dict[str, UUID] = {}
        for lesson in draft.generatedLessons:
            saved = self._lessons.create(
                title=lesson.title,
                content=lesson.content,
                category=lesson.category,
                level=lesson.level,
                sort_order=lesson.sortOrder,
            )
            lesson_ids[lesson.key] = saved.id

        story_ids: dict[str, UUID] = {}
        for story in draft.generatedStories:
            saved = self._stories.create(
                title=story.title,
                content=story.content,
                level=story.level,
                audio_url=story.audioUrl,
            )
            story_ids[story.key] = saved.id

        for question in draft.generatedQuestions:
            self._quizzes.create(
                question=question.question,
                options=question.options,
                correct_index=question.correctIndex,
                explanation=question.explanation,
                category=question.category,
                level=question.level,
            )

        for step in sorted(draft.steps, key=lambda item: item.stepOrder):
            self._paths.create_step(
                path_id=path.id,
                step_order=step.stepOrder,
                step_type=step.stepType,
                title=step.title,
                xp_reward=step.xpReward,
                quiz_category=step.quizCategory if step.stepType == "quiz" else None,
                lesson_id=lesson_ids.get(step.generatedLessonKey or ""),
                story_id=story_ids.get(step.generatedStoryKey or ""),
                required_step_id=None,
            )
        return path.id

    def _student_profile(self, session: DelfTestSession) -> dict:
        ordered = sorted(
            session.category_scores.items(),
            key=lambda item: item[1],
        )
        return {
            "classLevel": session.class_level,
            "targetDelfLevel": session.target_delf_level,
            "achievedDelfLevel": session.achieved_delf_level,
            "overallScore": session.overall_score,
            "categoryScores": dict(session.category_scores),
            "weakCategories": [category for category, _ in ordered[:2]],
            "strongCategories": [category for category, _ in ordered[-2:]][::-1],
        }

    def _reference_context(self, session: DelfTestSession) -> str:
        weak = {
            category
            for category, _score in sorted(
                session.category_scores.items(),
                key=lambda item: item[1],
            )[:2]
        }
        lessons = [
            lesson
            for lesson in self._lessons.list_all()
            if lesson.level == session.class_level and lesson.category in weak
        ][:4]
        stories = [
            story
            for story in self._stories.list_all()
            if story.level == session.class_level
        ][:3]
        questions = [
            question
            for question in self._quizzes.list_all()
            if question.level == session.class_level and question.category in weak
        ][:6]
        parts: list[str] = []
        if lessons:
            parts.append(
                "Leçons existantes: "
                + " | ".join(f"{lesson.category}: {lesson.title}" for lesson in lessons)
            )
        if stories:
            parts.append(
                "Histoires existantes: "
                + " | ".join(story.title for story in stories)
            )
        if questions:
            parts.append(
                "Questions existantes: "
                + " | ".join(f"{question.category}: {question.question}" for question in questions)
            )
        return " ".join(parts)

    def _difficulty_for_score(self, score: int | None) -> str:
        if score is None or score < 50:
            return "easy"
        if score < 80:
            return "medium"
        return "hard"
