import pytest

from app.api.schemas.ai_content import AIContentGenerateIn
from app.application.ai_content_service import (
    AIContentError,
    AIContentService,
    AIProvider,
    AIProviderResult,
)


class StubProvider(AIProvider):
    def __init__(self, provider: str, model: str, responses: list[str | Exception]) -> None:
        super().__init__(provider, model, 1)
        self.responses = responses
        self.calls = 0
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> AIProviderResult:
        self.calls += 1
        self.prompts.append(prompt)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return AIProviderResult(provider=self.provider, model=self.model, text=response)


def request(**overrides) -> AIContentGenerateIn:
    data = {
        "classLevel": "3ème année",
        "targetDelfLevel": "A1",
        "category": "Grammaire",
        "count": 2,
        "difficulty": "medium",
    }
    data.update(overrides)
    return AIContentGenerateIn(**data)


def question_json() -> str:
    return """
    {
      "questions": [
        {
          "question": "Quelle phrase utilise correctement le verbe être avec le sujet je ?",
          "options": ["Je suis élève.", "Je être élève.", "Je a élève.", "Je sont élève."],
          "correctIndex": 0,
          "explanation": "On utilise suis avec je.",
          "category": "Grammaire",
          "level": "3ème année"
        }
      ]
    }
    """


def test_generates_normalized_quiz_questions() -> None:
    primary = StubProvider("hf", "microsoft/Phi-4-mini-instruct", [question_json()])
    service = AIContentService(primary)

    result = service.generate_quiz_questions(request())

    assert result.provider.provider == "hf"
    assert result.provider.usedBackup is False
    assert result.questions[0].category == "Grammaire"
    assert result.questions[0].level == "3ème année"
    assert result.questions[0].correctIndex == 0


def test_repairs_malformed_shape_once() -> None:
    primary = StubProvider("hf", "model", ['{"bad":[]}', question_json()])
    service = AIContentService(primary, repair_retries=1)

    result = service.generate_quiz_questions(request())

    assert primary.calls == 2
    assert len(result.questions) == 1


def test_repairs_pedagogically_invalid_question_once() -> None:
    duplicate_options = """
    {
      "questions": [
        {
          "question": "Quelle phrase utilise correctement le verbe être avec le sujet je ?",
          "options": ["Je suis élève.", "Je suis élève.", "Je a élève.", "Je sont élève."],
          "correctIndex": 0,
          "explanation": "On utilise suis avec je.",
          "category": "Grammaire",
          "level": "3ème année"
        }
      ]
    }
    """
    primary = StubProvider("hf", "model", [duplicate_options, question_json()])
    service = AIContentService(primary, repair_retries=1)

    result = service.generate_quiz_questions(request())

    assert primary.calls == 2
    assert result.questions[0].options == [
        "Je suis élève.",
        "Je être élève.",
        "Je a élève.",
        "Je sont élève.",
    ]


def test_uses_backup_when_primary_fails() -> None:
    primary = StubProvider("hf", "model", [AIContentError("down")])
    backup = StubProvider("nvidia", "backup", [question_json()])
    service = AIContentService(primary, backup)

    result = service.generate_quiz_questions(request())

    assert result.provider.provider == "nvidia"
    assert result.provider.usedBackup is True
    assert backup.calls == 1


def test_rejects_invalid_category() -> None:
    service = AIContentService(StubProvider("hf", "model", [question_json()]))

    with pytest.raises(AIContentError):
        service.generate_quiz_questions(request(category="Lecture"))


def test_generated_question_matches_existing_create_shape() -> None:
    service = AIContentService(StubProvider("hf", "model", [question_json()]))

    result = service.generate_quiz_questions(request())
    payload = result.questions[0].model_dump(by_alias=True)

    assert set(payload) == {
        "question",
        "options",
        "correctIndex",
        "explanation",
        "category",
        "level",
    }


def test_prompt_includes_default_quality_rules_and_project_context() -> None:
    primary = StubProvider("hf", "model", [question_json()])
    service = AIContentService(primary)

    service.generate_quiz_questions(
        request(teacherInstructions=None),
        reference_context="Questions existantes: Grammaire: Quel est le verbe correct ?",
    )

    prompt = primary.prompts[0]
    assert "Respecte le niveau DELF demandé" in prompt
    assert "Données existantes du projet" in prompt
    assert "Quel est le verbe correct" in prompt


def test_strips_letter_prefixes_from_generated_options() -> None:
    prefixed_options = """
    {
      "questions": [
        {
          "question": "Quelle est la bonne forme du verbe être pour le sujet je ?",
          "options": ["A) est", "B) suis", "C) étais", "D) sont"],
          "correctIndex": 1,
          "explanation": "Avec le sujet je, le verbe être se conjugue suis.",
          "category": "Grammaire",
          "level": "3ème année"
        }
      ]
    }
    """
    service = AIContentService(StubProvider("hf", "model", [prefixed_options]))

    result = service.generate_quiz_questions(request())

    assert result.questions[0].options == ["est", "suis", "étais", "sont"]
