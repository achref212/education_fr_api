from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Difficulty = Literal["easy", "medium", "hard"]


class AIContentGenerateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    classLevel: str
    targetDelfLevel: str = "A1"
    category: str | None = None
    count: int = Field(default=4, ge=1, le=20)
    difficulty: Difficulty = "medium"
    teacherInstructions: str | None = Field(default=None, max_length=1200)


class AIQuizQuestionDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(min_length=1)
    options: list[str] = Field(min_length=2, max_length=5)
    correctIndex: int = Field(ge=0)
    explanation: str | None = None
    category: str
    level: str


class AILessonDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1)
    category: str
    level: str
    sortOrder: int = 0


class AIGeneratedLessonDraft(AILessonDraft):
    key: str = Field(min_length=1, max_length=80)


class AIGeneratedStoryDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1)
    level: str
    audioUrl: str | None = None


class AILearningPathDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    classLevel: str
    delfTargetLevel: str
    minScore: int | None = Field(default=None, ge=0, le=100)
    maxScore: int | None = Field(default=None, ge=0, le=100)
    isDefault: bool = False


class AILearningPathStepDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stepOrder: int = Field(ge=1)
    stepType: str
    title: str = Field(min_length=1, max_length=180)
    xpReward: int = Field(default=20, ge=0, le=200)
    quizCategory: str | None = None
    generatedLessonKey: str | None = None
    generatedStoryKey: str | None = None


class AIDelfTestDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    classLevel: str
    targetDelfLevel: str
    questionsByCategory: dict[str, list[AIQuizQuestionDraft]]


class AIDelfMockAssetDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    assetType: str
    title: str
    url: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIDelfMockItemDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    itemOrder: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=180)
    prompt: str = Field(min_length=1)
    points: int = Field(ge=1, le=25)
    content: dict[str, Any] = Field(default_factory=dict)
    answerKey: dict[str, Any] = Field(default_factory=dict)
    rubric: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIDelfMockSectionDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sectionOrder: int = Field(ge=1)
    sectionType: str
    title: str = Field(min_length=1, max_length=180)
    durationMinutes: int = Field(ge=1)
    points: int = Field(default=25, ge=1, le=25)
    instructions: str = Field(min_length=1)
    audioUrl: str | None = None
    rubric: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    items: list[AIDelfMockItemDraft] = Field(min_length=1)


class AIDelfMockExamDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    track: str
    level: str
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    status: str = "draft"
    sourceNotes: str | None = None
    sections: list[AIDelfMockSectionDraft]
    assets: list[AIDelfMockAssetDraft] = Field(default_factory=list)


class AIProviderInfo(BaseModel):
    provider: str
    model: str
    usedBackup: bool = False


class AIQuizQuestionsOut(BaseModel):
    provider: AIProviderInfo
    questions: list[AIQuizQuestionDraft]


class AILessonOut(BaseModel):
    provider: AIProviderInfo
    lesson: AILessonDraft


class AILearningPathOut(BaseModel):
    provider: AIProviderInfo
    path: AILearningPathDraft
    generatedLessons: list[AIGeneratedLessonDraft] = Field(default_factory=list)
    generatedStories: list[AIGeneratedStoryDraft] = Field(default_factory=list)
    generatedQuestions: list[AIQuizQuestionDraft] = Field(default_factory=list)
    steps: list[AILearningPathStepDraft] = Field(default_factory=list)
    adaptationNotes: str | None = None


class AIDelfTestOut(BaseModel):
    provider: AIProviderInfo
    test: AIDelfTestDraft


class AIDelfMockExamOut(BaseModel):
    provider: AIProviderInfo
    exam: AIDelfMockExamDraft
