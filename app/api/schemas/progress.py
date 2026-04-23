from pydantic import BaseModel, Field


class ProgressOut(BaseModel):
    lessonsCompleted: list[str] = Field(default_factory=list)
    quizScores: dict[str, list[int]] = Field(default_factory=dict)
    exerciseScores: dict[str, list[int]] = Field(default_factory=dict)


class ProgressIn(BaseModel):
    lessonsCompleted: list[str] = Field(default_factory=list)
    quizScores: dict[str, list[int]] = Field(default_factory=dict)
    exerciseScores: dict[str, list[int]] = Field(default_factory=dict)
