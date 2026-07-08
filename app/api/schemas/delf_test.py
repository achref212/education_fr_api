from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DelfTestQuestionOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    question: str
    options: list[Any]
    category: str
    level: str


class DelfTestSectionOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category: str
    questions: list[DelfTestQuestionOut]
    submitted: bool = False
    score: int | None = None


class DelfTestStartOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sessionId: UUID
    classLevel: str
    targetDelfLevel: str
    status: str
    sections: list[DelfTestSectionOut]
    submittedCategories: list[str]


class DelfTestAnswerIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    questionId: UUID
    selectedIndex: int = Field(ge=0)
    timeMs: int = Field(default=0, ge=0)


class DelfTestSectionSubmitIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    answers: list[DelfTestAnswerIn]


class DelfTestSectionSubmitOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sessionId: UUID
    category: str
    score: int
    correctCount: int
    totalQuestions: int
    submittedCategories: list[str]
    remainingCategories: list[str]


class DelfTestHistoryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sessionId: UUID
    classLevel: str
    targetDelfLevel: str
    achievedDelfLevel: str | None
    overallScore: int | None
    categoryScores: dict[str, int]
    comparisonToTarget: str
    finishedAt: str | None


class DelfTestQuestionResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    questionId: UUID
    question: str
    options: list[Any]
    category: str
    selectedIndex: int | None = None
    isCorrect: bool = False
    correctIndex: int | None = None
    explanation: str | None = None


class DelfTestSectionResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category: str
    score: int
    questions: list[DelfTestQuestionResultOut]


class DelfTestResultsOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sessionId: UUID
    classLevel: str
    targetDelfLevel: str
    achievedDelfLevel: str | None
    overallScore: int | None
    categoryScores: dict[str, int]
    comparisonToTarget: str
    status: str
    sections: list[DelfTestSectionResultOut]
    finishedAt: str | None


class DelfTestSessionAdminOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sessionId: UUID
    userId: UUID
    classLevel: str
    targetDelfLevel: str
    achievedDelfLevel: str | None
    overallScore: int | None
    categoryScores: dict[str, int]
    status: str
    startedAt: datetime | None = None
    finishedAt: datetime | None = None
    studentFirstName: str | None = None
    studentLastName: str | None = None
    studentEmail: str | None = None


class DelfLevelThresholdIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    level: str
    minOverall: int = Field(ge=0, le=100)
    minCategory: int = Field(ge=0, le=100)


class DelfTestConfigOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    questionsPerCategory: int
    levelThresholds: list[DelfLevelThresholdIn]
    updatedAt: datetime


class DelfTestConfigUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    questionsPerCategory: int | None = Field(default=None, ge=1, le=20)
    levelThresholds: list[DelfLevelThresholdIn] | None = None
