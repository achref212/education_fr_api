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


def mock_exam_json(section_points: int = 25) -> str:
    def section(order: int, section_type: str, points: list[int]) -> str:
        return f"""
        {{
          "sectionOrder": {order},
          "sectionType": "{section_type}",
          "title": "{section_type}",
          "durationMinutes": 15,
          "points": {section_points},
          "instructions": "Consigne originale.",
          "audioUrl": null,
          "rubric": {{"total": {section_points}}},
          "metadata": {{}},
          "items": [
            {{"itemOrder": 1, "title": "Exercice 1", "prompt": "Réponds.", "points": {points[0]}, "content": {{}}, "answerKey": {{}}, "rubric": {{}}, "metadata": {{}}}},
            {{"itemOrder": 2, "title": "Exercice 2", "prompt": "Réponds.", "points": {points[1]}, "content": {{}}, "answerKey": {{}}, "rubric": {{}}, "metadata": {{}}}},
            {{"itemOrder": 3, "title": "Exercice 3", "prompt": "Réponds.", "points": {points[2]}, "content": {{}}, "answerKey": {{}}, "rubric": {{}}, "metadata": {{}}}}
          ]
        }}
        """

    return """
    {"exam":{
      "track":"Prime",
      "level":"A1.1",
      "title":"Examen blanc original",
      "description":"Brouillon",
      "status":"draft",
      "sourceNotes":"Relecture professeur requise.",
      "assets":[],
      "sections":[
    """ + ",".join(
        [
            section(1, "listening", [8, 8, 9]),
            section(2, "reading", [8, 7, 10]),
            section(3, "writing", [7, 8, 10]),
            section(4, "speaking", [8, 8, 9]),
        ]
    ) + "]}}"


def learning_path_json(
    *,
    quiz_category: str = "Grammaire",
    lesson_key: str = "lesson-1",
) -> str:
    return f"""
    {{
      "path": {{
        "title": "Parcours personnalisé A1",
        "description": "Renforcement adapté après le test DELF.",
        "classLevel": "3ème année",
        "delfTargetLevel": "A1",
        "minScore": 0,
        "maxScore": 100,
        "isDefault": false
      }},
      "generatedLessons": [
        {{
          "key": "lesson-1",
          "title": "Revoir les accords simples",
          "content": "Objectif: comprendre les accords. Exemple 1. Exemple 2. Mini-activité.",
          "category": "Grammaire",
          "level": "3ème année",
          "sortOrder": 0
        }},
        {{
          "key": "lesson-2",
          "title": "Conjuguer être au présent",
          "content": "Objectif: conjuguer être. Exemple 1. Exemple 2. Mini-activité.",
          "category": "Conjugaison",
          "level": "3ème année",
          "sortOrder": 1
        }}
      ],
      "generatedStories": [
        {{
          "key": "story-1",
          "title": "Une journée à l'école",
          "content": "Lina arrive à l'école. Elle lit une phrase et répond calmement.",
          "level": "3ème année",
          "audioUrl": null
        }}
      ],
      "generatedQuestions": [
        {{
          "question": "Quelle phrase accorde correctement le nom ami au pluriel ?",
          "options": ["Les amis jouent.", "Les ami jouent.", "Le amis jouent.", "Les amies joue."],
          "correctIndex": 0,
          "explanation": "Au pluriel, ami prend un s avec les.",
          "category": "{quiz_category}",
          "level": "3ème année"
        }},
        {{
          "question": "Quelle forme du verbe être convient avec nous ?",
          "options": ["Nous sommes prêts.", "Nous suis prêts.", "Nous est prêts.", "Nous sont prêts."],
          "correctIndex": 0,
          "explanation": "Avec nous, le verbe être se conjugue sommes.",
          "category": "Conjugaison",
          "level": "3ème année"
        }}
      ],
      "steps": [
        {{"stepOrder": 1, "stepType": "lesson", "title": "Comprendre les accords", "xpReward": 20, "generatedLessonKey": "{lesson_key}"}},
        {{"stepOrder": 2, "stepType": "quiz", "title": "Quiz grammaire", "xpReward": 20, "quizCategory": "Grammaire"}},
        {{"stepOrder": 3, "stepType": "lesson", "title": "Conjuguer être", "xpReward": 20, "generatedLessonKey": "lesson-2"}},
        {{"stepOrder": 4, "stepType": "story", "title": "Lire une histoire courte", "xpReward": 15, "generatedStoryKey": "story-1"}},
        {{"stepOrder": 5, "stepType": "quiz", "title": "Quiz conjugaison", "xpReward": 20, "quizCategory": "Conjugaison"}}
      ],
      "adaptationNotes": "Le parcours commence par les deux catégories faibles."
    }}
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


def test_generates_delf_mock_exam_draft() -> None:
    primary = StubProvider("hf", "model", [mock_exam_json()])
    service = AIContentService(primary)

    result = service.generate_delf_mock_exam(request(targetDelfLevel="A1.1"))

    assert result.exam.track == "Prime"
    assert result.exam.level == "A1.1"
    assert [section.sectionType for section in result.exam.sections] == [
        "listening",
        "reading",
        "writing",
        "speaking",
    ]
    assert sum(section.points for section in result.exam.sections) == 100


def test_rejects_delf_mock_exam_with_wrong_section_points() -> None:
    primary = StubProvider(
        "hf",
        "model",
        [mock_exam_json(section_points=20), mock_exam_json(section_points=20)],
    )
    service = AIContentService(primary, repair_retries=0)

    with pytest.raises(AIContentError):
        service.generate_delf_mock_exam(request(targetDelfLevel="A1.1"))


def test_generates_full_learning_path_draft_with_steps_and_content() -> None:
    primary = StubProvider("hf", "model", [learning_path_json()])
    service = AIContentService(primary)

    result = service.generate_learning_path(
        request(),
        student_profile={
            "targetDelfLevel": "A1",
            "achievedDelfLevel": "A1",
            "overallScore": 58,
            "categoryScores": {"Grammaire": 35, "Conjugaison": 48},
            "weakCategories": ["Grammaire", "Conjugaison"],
            "strongCategories": ["Vocabulaire"],
        },
    )

    assert result.path.title == "Parcours personnalisé A1"
    assert len(result.generatedLessons) == 2
    assert len(result.generatedStories) == 1
    assert len(result.generatedQuestions) == 2
    assert [step.stepOrder for step in result.steps] == [1, 2, 3, 4, 5]
    assert result.steps[0].generatedLessonKey == "lesson-1"
    assert "catégories faibles" in primary.prompts[0]


def test_rejects_learning_path_with_bad_quiz_category() -> None:
    service = AIContentService(
        StubProvider("hf", "model", [learning_path_json(quiz_category="Lecture")]),
        repair_retries=0,
    )

    with pytest.raises(AIContentError):
        service.generate_learning_path(request())


def test_rejects_learning_path_with_missing_generated_lesson_key() -> None:
    service = AIContentService(
        StubProvider("hf", "model", [learning_path_json(lesson_key="missing")]),
        repair_retries=0,
    )

    with pytest.raises(AIContentError):
        service.generate_learning_path(request())
