from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.api.dependencies import (
    get_ai_content_service,
    get_lesson_repo,
    get_quiz_repo,
    require_admin,
)
from app.api.schemas.ai_content import AIContentGenerateIn, AIProviderInfo, AIQuizQuestionsOut, AIQuizQuestionDraft
from app.domain.entities import User
from app.main import app


class StubAIContentService:
    def generate_quiz_questions(
        self,
        body: AIContentGenerateIn,
        reference_context: str | None = None,
    ) -> AIQuizQuestionsOut:
        return AIQuizQuestionsOut(
            provider=AIProviderInfo(provider="hf", model="microsoft/Phi-4-mini-instruct"),
            questions=[
                AIQuizQuestionDraft(
                    question="Choisis la phrase correcte.",
                    options=["Je suis élève.", "Je être élève."],
                    correctIndex=0,
                    explanation="On utilise suis avec je.",
                    category=body.category or "Grammaire",
                    level=body.classLevel,
                )
            ],
        )


class EmptyContentRepo:
    def list_all(self) -> list:
        return []


def admin_user() -> User:
    return User(
        id=uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        level="avance",
        created_at=datetime.now(timezone.utc),
        role="admin",
    )


@pytest.mark.anyio
async def test_ai_endpoint_requires_auth(client) -> None:
    response = await client.post("/admin/ai/generate-quiz-questions", json={})

    assert response.status_code == 401


@pytest.mark.anyio
async def test_ai_endpoint_returns_reviewable_drafts_for_admin(client) -> None:
    app.dependency_overrides[require_admin] = admin_user
    app.dependency_overrides[get_ai_content_service] = lambda: StubAIContentService()
    app.dependency_overrides[get_quiz_repo] = lambda: EmptyContentRepo()
    app.dependency_overrides[get_lesson_repo] = lambda: EmptyContentRepo()
    try:
        response = await client.post(
            "/admin/ai/generate-quiz-questions",
            json={
                "classLevel": "3ème année",
                "targetDelfLevel": "A1",
                "category": "Grammaire",
                "count": 1,
                "difficulty": "medium",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["provider"]["provider"] == "hf"
    assert data["questions"][0]["category"] == "Grammaire"
    assert data["questions"][0]["level"] == "3ème année"
