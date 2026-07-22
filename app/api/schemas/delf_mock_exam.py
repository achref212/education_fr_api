from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DelfMockAssetIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    assetType: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=180)
    url: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DelfMockItemIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    itemOrder: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=180)
    prompt: str = Field(min_length=1)
    points: int = Field(ge=1, le=25)
    content: dict[str, Any] = Field(default_factory=dict)
    answerKey: dict[str, Any] = Field(default_factory=dict)
    rubric: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DelfMockSectionIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sectionOrder: int = Field(ge=1)
    sectionType: str
    title: str = Field(min_length=1, max_length=180)
    durationMinutes: int = Field(ge=1, le=180)
    points: int = Field(default=25, ge=1, le=25)
    instructions: str = Field(min_length=1)
    audioUrl: str | None = None
    rubric: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    items: list[DelfMockItemIn] = Field(min_length=1)


class DelfMockExamCreateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    track: str
    level: str
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    status: str = "draft"
    sourceNotes: str | None = None
    sections: list[DelfMockSectionIn] = Field(min_length=4, max_length=4)
    assets: list[DelfMockAssetIn] = Field(default_factory=list)


class DelfMockExamUpdateIn(DelfMockExamCreateIn):
    pass


class DelfMockAssetOut(DelfMockAssetIn):
    id: UUID
    examId: UUID
    createdAt: datetime


class DelfMockItemOut(DelfMockItemIn):
    id: UUID
    sectionId: UUID


class DelfMockSectionOut(DelfMockSectionIn):
    id: UUID
    examId: UUID
    items: list[DelfMockItemOut]


class DelfMockExamOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    track: str
    level: str
    title: str
    description: str | None = None
    status: str
    totalDurationMinutes: int
    totalPoints: int
    sourceNotes: str | None = None
    sections: list[DelfMockSectionOut]
    assets: list[DelfMockAssetOut]
    createdAt: datetime
    updatedAt: datetime
