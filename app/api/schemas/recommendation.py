from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities import Recommendation


class RecommendationCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    content: str = Field(min_length=1, max_length=4000)


class RecommendationOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    studentId: UUID
    professorId: UUID | None
    content: str
    createdAt: datetime

    @classmethod
    def from_domain(cls, r: Recommendation) -> "RecommendationOut":
        return cls(
            id=r.id,
            studentId=r.student_id,
            professorId=r.professor_id,
            content=r.content,
            createdAt=r.created_at,
        )
