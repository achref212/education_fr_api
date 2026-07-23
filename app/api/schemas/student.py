from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.api.schemas.delf_mock_exam import DelfMockExamOut


class StudentReviewItemOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    sourceType: str
    sourceId: str | None = None
    questionId: str | None = None
    category: str
    question: str
    options: list
    selectedIndex: int | None = None
    correctIndex: int | None = None
    explanation: str | None = None
    status: str
    timesReviewed: int
    createdAt: datetime
    updatedAt: datetime
    lastReviewedAt: datetime | None = None


class StudentReviewGroupOut(BaseModel):
    category: str
    total: int
    openCount: int
    items: list[StudentReviewItemOut]


class StudentReviewOut(BaseModel):
    totalOpen: int
    totalCompleted: int
    weakCategories: list[dict]
    groups: list[StudentReviewGroupOut]


class StudentHintOut(BaseModel):
    itemId: UUID
    hint: str
    source: str
    provider: dict | None = None


class StudentLeaderboardEntryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    userId: UUID
    firstName: str
    lastName: str
    classLevel: str | None = None
    profilePictureUrl: str | None = None
    totalXp: int
    currentStreak: int
    completedSteps: int
    progressPercent: float
    rank: int
    isCurrentUser: bool = False


class StudentLeaderboardOut(BaseModel):
    scope: str
    currentRank: int | None = None
    currentStudent: StudentLeaderboardEntryOut | None = None
    entries: list[StudentLeaderboardEntryOut]


class StudentAchievementOut(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    unlocked: bool
    progress: int
    target: int
    category: str


class StudentAchievementsOut(BaseModel):
    unlockedCount: int
    totalCount: int
    nextBadge: StudentAchievementOut | None = None
    items: list[StudentAchievementOut]


class StudentRecentDelfOut(BaseModel):
    sessionId: UUID
    targetDelfLevel: str
    achievedDelfLevel: str | None = None
    overallScore: int | None = None
    categoryScores: dict
    finishedAt: datetime | None = None


class StudentNextActionOut(BaseModel):
    type: str
    title: str
    subtitle: str
    route: str
    itemId: str | None = None


class StudentHubOut(BaseModel):
    firstName: str
    lastName: str
    classLevel: str | None = None
    profilePictureUrl: str | None = None
    totalXp: int
    currentStreak: int
    longestStreak: int
    level: int
    completedSteps: int
    totalSteps: int
    parcoursPercent: float
    nextStepId: UUID | None = None
    nextStepTitle: str | None = None
    reviewOpenCount: int
    weakCategories: list[dict]
    recentDelf: StudentRecentDelfOut | None = None
    achievementsPreview: list[StudentAchievementOut]
    nextAction: StudentNextActionOut


class StudentDelfMockAnswerIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    itemId: UUID
    selectedIndex: int | None = None
    text: str | None = None


class StudentDelfMockAttemptSubmitIn(BaseModel):
    answers: list[StudentDelfMockAnswerIn]


class StudentDelfMockAttemptOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attemptId: UUID
    examId: UUID
    status: str
    answers: list[dict]
    sectionScores: dict[str, int]
    overallScore: int | None = None
    approximate: bool
    resultMessage: str | None = None
    startedAt: datetime
    finishedAt: datetime | None = None
    exam: DelfMockExamOut
