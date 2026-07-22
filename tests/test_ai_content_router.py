from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.api.dependencies import (
    get_ai_content_service,
    get_lesson_repo,
    get_quiz_repo,
    require_admin,
)
from app.api.schemas.ai_content import (
    AIContentGenerateIn,
    AIDelfMockExamDraft,
    AIDelfMockExamOut,
    AIDelfMockItemDraft,
    AIDelfMockSectionDraft,
    AIProviderInfo,
    AIQuizQuestionDraft,
    AIQuizQuestionsOut,
)
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

    def generate_delf_mock_exam(
        self,
        body: AIContentGenerateIn,
        reference_context: str | None = None,
    ) -> AIDelfMockExamOut:
        provider = AIProviderInfo(provider="hf", model="microsoft/Phi-4-mini-instruct")
        sections = [
            _mock_section(1, "listening", [8, 8, 9]),
            _mock_section(2, "reading", [8, 7, 10]),
            _mock_section(3, "writing", [7, 8, 10]),
            _mock_section(4, "speaking", [8, 8, 9]),
        ]
        return AIDelfMockExamOut(
            provider=provider,
            exam=AIDelfMockExamDraft(
                track="Prime",
                level=body.targetDelfLevel,
                title="Examen blanc original",
                description="Brouillon",
                status="draft",
                sourceNotes="Relecture professeur requise.",
                sections=sections,
                assets=[],
            ),
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


def _mock_section(order: int, section_type: str, points: list[int]) -> AIDelfMockSectionDraft:
    return AIDelfMockSectionDraft(
        sectionOrder=order,
        sectionType=section_type,
        title=section_type,
        durationMinutes=15,
        points=25,
        instructions="Consigne",
        audioUrl=None,
        rubric={},
        metadata={},
        items=[
            AIDelfMockItemDraft(
                itemOrder=index,
                title=f"Exercice {index}",
                prompt="Réponds.",
                points=point,
                content={},
                answerKey={},
                rubric={},
                metadata={},
            )
            for index, point in enumerate(points, start=1)
        ],
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


@pytest.mark.anyio
async def test_ai_mock_exam_endpoint_returns_full_draft_for_admin(client) -> None:
    app.dependency_overrides[require_admin] = admin_user
    app.dependency_overrides[get_ai_content_service] = lambda: StubAIContentService()
    app.dependency_overrides[get_quiz_repo] = lambda: EmptyContentRepo()
    app.dependency_overrides[get_lesson_repo] = lambda: EmptyContentRepo()
    try:
        response = await client.post(
            "/admin/ai/generate-delf-mock-exam",
            json={
                "classLevel": "2ème année",
                "targetDelfLevel": "A1.1",
                "count": 3,
                "difficulty": "medium",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["exam"]["track"] == "Prime"
    assert [section["sectionType"] for section in data["exam"]["sections"]] == [
        "listening",
        "reading",
        "writing",
        "speaking",
    ]
