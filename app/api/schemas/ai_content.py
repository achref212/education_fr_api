from typing import Literal

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


class AILearningPathDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    classLevel: str
    delfTargetLevel: str
    minScore: int | None = Field(default=None, ge=0, le=100)
    maxScore: int | None = Field(default=None, ge=0, le=100)
    isDefault: bool = False


class AIDelfTestDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    classLevel: str
    targetDelfLevel: str
    questionsByCategory: dict[str, list[AIQuizQuestionDraft]]


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


class AIDelfTestOut(BaseModel):
    provider: AIProviderInfo
    test: AIDelfTestDraft
