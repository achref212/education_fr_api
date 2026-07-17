from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StepProgressOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stepId: UUID
    status: str
    score: int | None = None
    attempts: int = 0
    completedAt: datetime | None = None


class ParcoursStepOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    stepOrder: int
    stepType: str
    title: str
    xpReward: int
    status: str
    quizCategory: str | None = None
    lessonId: UUID | None = None
    storyId: UUID | None = None
    requiredStepId: UUID | None = None
    score: int | None = None
    attempts: int = 0


class ParcoursOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pathId: UUID
    assignedPathId: UUID | None = None
    title: str
    description: str | None
    classLevel: str
    delfTargetLevel: str
    totalXp: int
    currentStreak: int
    preferredDifficulty: str
    completionPercent: float
    steps: list[ParcoursStepOut]


class ParcoursSummaryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    classLevel: str
    delfTargetLevel: str
    completionPercent: float
    totalSteps: int
    completedSteps: int
    totalXp: int
    currentStreak: int
    preferredDifficulty: str
    nextStepId: UUID | None = None
    nextStepTitle: str | None = None


class StepCompleteIn(BaseModel):
    score: int = Field(ge=0, le=100)


class StepCompleteOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stepId: UUID
    score: int
    xpEarned: int
    passed: bool
    nextStepId: UUID | None = None
    parcoursPercent: float


class DifficultyUpdateIn(BaseModel):
    difficulty: str = Field(pattern="^(easy|medium|hard)$")


class LearningPathCreateIn(BaseModel):
    classLevel: str
    title: str
    delfTargetLevel: str
    description: str | None = None
    minScore: int | None = Field(default=None, ge=0, le=100)
    maxScore: int | None = Field(default=None, ge=0, le=100)
    isDefault: bool = False


class LearningPathUpdateIn(BaseModel):
    title: str | None = None
    description: str | None = None
    delfTargetLevel: str | None = None
    isActive: bool | None = None
    minScore: int | None = Field(default=None, ge=0, le=100)
    maxScore: int | None = Field(default=None, ge=0, le=100)
    isDefault: bool | None = None


class LearningPathOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    classLevel: str
    title: str
    description: str | None
    delfTargetLevel: str
    isActive: bool
    minScore: int | None = None
    maxScore: int | None = None
    isDefault: bool = False
    stepCount: int = 0
    assignedUsersCount: int = 0
    createdAt: datetime


class LearningPathStepCreateIn(BaseModel):
    stepOrder: int
    stepType: str
    title: str
    xpReward: int = 10
    quizCategory: str | None = None
    lessonId: UUID | None = None
    storyId: UUID | None = None
    requiredStepId: UUID | None = None


class LearningPathStepUpdateIn(BaseModel):
    stepOrder: int | None = None
    stepType: str | None = None
    title: str | None = None
    xpReward: int | None = None
    quizCategory: str | None = None
    lessonId: UUID | None = None
    storyId: UUID | None = None
    requiredStepId: UUID | None = None


class LearningPathStepOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    pathId: UUID
    stepOrder: int
    stepType: str
    title: str
    xpReward: int
    quizCategory: str | None = None
    lessonId: UUID | None = None
    storyId: UUID | None = None
    requiredStepId: UUID | None = None
    createdAt: datetime
