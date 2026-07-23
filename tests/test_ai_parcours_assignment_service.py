from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.api.schemas.ai_content import (
    AIContentGenerateIn,
    AIGeneratedLessonDraft,
    AIGeneratedStoryDraft,
    AILearningPathDraft,
    AILearningPathOut,
    AILearningPathStepDraft,
    AIProviderInfo,
    AIQuizQuestionDraft,
)
from app.application.ai_parcours_assignment_service import AIParcoursAssignmentService
from app.domain.entities import DelfTestSession, LearningPath, LearningPathStep, Lesson, QuizQuestion, Story, User


class StubAIContentService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate_learning_path(
        self,
        body: AIContentGenerateIn,
        reference_context: str | None = None,
        student_profile: dict | None = None,
    ) -> AILearningPathOut:
        self.calls.append(
            {
                "body": body,
                "reference_context": reference_context,
                "student_profile": student_profile,
            }
        )
        return AILearningPathOut(
            provider=AIProviderInfo(provider="stub", model="local"),
            path=AILearningPathDraft(
                title="Parcours personnalisé",
                description="Parcours généré après diagnostic.",
                classLevel=body.classLevel,
                delfTargetLevel=body.targetDelfLevel,
                minScore=0,
                maxScore=100,
                isDefault=False,
            ),
            generatedLessons=[
                AIGeneratedLessonDraft(
                    key="lesson-1",
                    title="Revoir la grammaire",
                    content="Règle, exemple 1, exemple 2, mini-activité.",
                    category="Grammaire",
                    level=body.classLevel,
                    sortOrder=0,
                )
            ],
            generatedStories=[
                AIGeneratedStoryDraft(
                    key="story-1",
                    title="Une lecture courte",
                    content="Lina lit une consigne simple et répond.",
                    level=body.classLevel,
                    audioUrl=None,
                )
            ],
            generatedQuestions=[
                AIQuizQuestionDraft(
                    question="Quelle phrase utilise le bon accord ?",
                    options=[
                        "Les amis parlent.",
                        "Les ami parlent.",
                        "Le amis parle.",
                        "Les amis parle.",
                    ],
                    correctIndex=0,
                    explanation="Le pluriel demande les et un s final.",
                    category="Grammaire",
                    level=body.classLevel,
                )
            ],
            steps=[
                AILearningPathStepDraft(
                    stepOrder=1,
                    stepType="lesson",
                    title="Leçon grammaire",
                    xpReward=20,
                    generatedLessonKey="lesson-1",
                ),
                AILearningPathStepDraft(
                    stepOrder=2,
                    stepType="quiz",
                    title="Quiz grammaire",
                    xpReward=20,
                    quizCategory="Grammaire",
                ),
                AILearningPathStepDraft(
                    stepOrder=3,
                    stepType="story",
                    title="Lecture courte",
                    xpReward=15,
                    generatedStoryKey="story-1",
                ),
            ],
            adaptationNotes="Priorité à la grammaire.",
        )


@dataclass
class FakePathRepo:
    paths: list[LearningPath] = field(default_factory=list)
    steps: list[LearningPathStep] = field(default_factory=list)

    def create_path(self, **kwargs) -> LearningPath:
        path = LearningPath(id=uuid4(), created_at=datetime.now(timezone.utc), **kwargs)
        self.paths.append(path)
        return path

    def create_step(self, **kwargs) -> LearningPathStep:
        step = LearningPathStep(id=uuid4(), created_at=datetime.now(timezone.utc), **kwargs)
        self.steps.append(step)
        return step


@dataclass
class FakeLessonRepo:
    lessons: list[Lesson] = field(default_factory=list)

    def list_all(self) -> list[Lesson]:
        return list(self.lessons)

    def create(self, **kwargs) -> Lesson:
        lesson = Lesson(id=uuid4(), created_at=datetime.now(timezone.utc), **kwargs)
        self.lessons.append(lesson)
        return lesson


@dataclass
class FakeStoryRepo:
    stories: list[Story] = field(default_factory=list)

    def list_all(self) -> list[Story]:
        return list(self.stories)

    def create(self, **kwargs) -> Story:
        story = Story(id=uuid4(), created_at=datetime.now(timezone.utc), **kwargs)
        self.stories.append(story)
        return story


@dataclass
class FakeQuizRepo:
    questions: list[QuizQuestion] = field(default_factory=list)

    def list_all(self) -> list[QuizQuestion]:
        return list(self.questions)

    def create(self, **kwargs) -> QuizQuestion:
        question = QuizQuestion(id=uuid4(), **kwargs)
        self.questions.append(question)
        return question


@dataclass
class FakeUserRepo:
    assigned: dict[UUID, UUID | None] = field(default_factory=dict)

    def assign_learning_path(
        self, user_id: UUID, learning_path_id: UUID | None
    ) -> User | None:
        self.assigned[user_id] = learning_path_id
        return None


def _student() -> User:
    return User(
        id=uuid4(),
        email="student@test.fr",
        first_name="Jean",
        last_name="Dupont",
        level="debutant",
        created_at=datetime.now(timezone.utc),
        role="user",
        class_level="3ème année",
    )


def _completed_session(user_id: UUID) -> DelfTestSession:
    return DelfTestSession(
        id=uuid4(),
        user_id=user_id,
        class_level="3ème année",
        target_delf_level="A1",
        status="completed",
        question_ids_by_category={},
        answers=[],
        category_scores={"Grammaire": 30, "Conjugaison": 55, "Vocabulaire": 80},
        overall_score=52,
        achieved_delf_level="A1",
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )


def test_ai_parcours_assignment_persists_generated_content_steps_and_user_assignment() -> None:
    ai = StubAIContentService()
    paths = FakePathRepo()
    lessons = FakeLessonRepo()
    stories = FakeStoryRepo()
    quizzes = FakeQuizRepo()
    users = FakeUserRepo()
    service = AIParcoursAssignmentService(
        ai=ai,
        paths=paths,
        lessons=lessons,
        stories=stories,
        quizzes=quizzes,
        users=users,
    )
    student = _student()
    session = _completed_session(student.id)

    result = service.assign_for_completed_test(student, session)

    assert result.generated_by_ai is True
    assert result.status == "ai_generated"
    assert users.assigned[student.id] == result.path_id
    assert paths.paths[0].id == result.path_id
    assert lessons.lessons[0].title == "Revoir la grammaire"
    assert stories.stories[0].audio_url is None
    assert quizzes.questions[0].category == "Grammaire"
    assert [step.step_type for step in paths.steps] == ["lesson", "quiz", "story"]
    assert paths.steps[0].lesson_id == lessons.lessons[0].id
    assert paths.steps[1].quiz_category == "Grammaire"
    assert paths.steps[2].story_id == stories.stories[0].id
    assert ai.calls[0]["body"].category == "Grammaire"
    assert ai.calls[0]["student_profile"]["weakCategories"] == ["Grammaire", "Conjugaison"]
