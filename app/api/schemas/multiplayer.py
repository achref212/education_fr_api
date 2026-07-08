from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JoinRoomIn(BaseModel):
    roomCode: str = Field(min_length=4, max_length=32)


class StartSessionIn(BaseModel):
    gameSlug: str = Field(min_length=1)
    difficulty: str = Field(pattern="^(easy|medium|hard)$")


class SubmitAnswerIn(BaseModel):
    questionId: UUID
    selectedIndex: int = Field(ge=0)
    timeMs: int = Field(ge=0, default=0)


class GameOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    slug: str
    name: str
    description: str | None
    minPlayers: int
    maxPlayers: int
    defaultQuestionCount: int


class GameSessionOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    roomId: UUID
    gameId: UUID
    difficulty: str
    classLevel: str
    status: str
    currentRound: int
    totalRounds: int
    settings: dict[str, Any]
    startedAt: datetime | None = None
    endedAt: datetime | None = None


class LeaderboardEntryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    userId: str
    firstName: str
    lastName: str
    score: int
    rank: int
    finished: bool


class RoomDetailOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    roomCode: str
    label: str | None
    classLevel: str | None
    status: str
    activeSessionId: UUID | None = None
    participants: list[dict[str, Any]]
    session: GameSessionOut | None = None


class SessionStateOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session: GameSessionOut
    leaderboard: list[LeaderboardEntryOut]
    currentQuestion: dict[str, Any] | None = None


class SubmitAnswerOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    isCorrect: bool
    points: int
    totalScore: int
    roundResult: dict[str, Any]


class SessionResultsOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session: GameSessionOut
    leaderboard: list[LeaderboardEntryOut]
    myResult: LeaderboardEntryOut | None = None


class GameCreateIn(BaseModel):
    slug: str
    name: str
    minPlayers: int = 2
    maxPlayers: int = 8
    defaultQuestionCount: int = 10
    description: str | None = None


class GameUpdateIn(BaseModel):
    name: str | None = None
    minPlayers: int | None = Field(None, ge=1)
    maxPlayers: int | None = Field(None, ge=1)
    defaultQuestionCount: int | None = Field(None, ge=1)
    description: str | None = None
