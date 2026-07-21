from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.api.schemas.ai_content import (
    AIContentGenerateIn,
    AIDelfTestDraft,
    AIDelfTestOut,
    AILearningPathDraft,
    AILearningPathOut,
    AILessonDraft,
    AILessonOut,
    AIProviderInfo,
    AIQuizQuestionDraft,
    AIQuizQuestionsOut,
)
from app.core.config import Settings
from app.domain.constants import (
    CLASS_LEVELS,
    DELF_LEVELS,
    LESSON_CATEGORIES,
    QUIZ_CATEGORIES,
)


AI_SYSTEM_PROMPT = (
    "Tu es un concepteur pédagogique DELF pour une plateforme d'apprentissage du français. "
    "Tu dois produire uniquement du contenu original, exact, adapté à l'âge et au niveau scolaire. "
    "Chaque réponse doit être vérifiable par un professeur avant publication."
)

DEFAULT_PEDAGOGICAL_PROMPT = (
    "Respecte le niveau DELF demandé, utilise un vocabulaire scolaire simple, "
    "évite les pièges ambigus, donne une seule bonne réponse, et explique clairement "
    "la règle ou la raison pédagogique en français."
)

GENERIC_QUESTION_STEMS: set[str] = {
    "quelle phrase est correcte ?",
    "quelle phrase est correcte?",
    "choisis la phrase correcte.",
    "choisis la phrase correcte",
    "choisis la bonne réponse.",
    "choisis la bonne réponse",
}


class AIContentError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AIProviderResult(BaseModel):
    provider: str
    model: str
    text: str


class AIProvider(ABC):
    def __init__(self, provider: str, model: str, timeout: float) -> None:
        self.provider = provider
        self.model = model
        self.timeout = timeout

    @abstractmethod
    def generate(self, prompt: str) -> AIProviderResult:
        raise NotImplementedError


class HuggingFaceProvider(AIProvider):
    def __init__(self, token: str, model: str, timeout: float) -> None:
        super().__init__("hf", model, timeout)
        self._token = token

    def generate(self, prompt: str) -> AIProviderResult:
        if not self._token:
            raise AIContentError("HF_TOKEN n'est pas configuré.")
        response = httpx.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={"Authorization": f"Bearer {self._token}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": AI_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.25,
                "max_tokens": 2600,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return AIProviderResult(
            provider=self.provider,
            model=self.model,
            text=data["choices"][0]["message"]["content"],
        )


class NvidiaProvider(AIProvider):
    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        super().__init__("nvidia", model, timeout)
        self._api_key = api_key

    def generate(self, prompt: str) -> AIProviderResult:
        if not self._api_key:
            raise AIContentError("NVIDIA_API_KEY n'est pas configuré.")
        response = httpx.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": AI_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 3200,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return AIProviderResult(
            provider=self.provider,
            model=self.model,
            text=data["choices"][0]["message"]["content"],
        )


class AIContentService:
    def __init__(
        self,
        primary: AIProvider,
        backup: AIProvider | None = None,
        repair_retries: int = 1,
    ) -> None:
        self._primary = primary
        self._backup = backup
        self._repair_retries = max(0, repair_retries)

    @classmethod
    def from_settings(cls, settings: Settings) -> "AIContentService":
        primary = _build_provider(
            settings.ai_provider,
            model=settings.ai_model,
            token=settings.hf_token,
            nvidia_key=settings.nvidia_api_key,
            timeout=settings.ai_timeout_seconds,
        )
        backup = None
        if settings.ai_backup_provider:
            backup = _build_provider(
                settings.ai_backup_provider,
                model=settings.ai_backup_model,
                token=settings.hf_token,
                nvidia_key=settings.nvidia_api_key,
                timeout=settings.ai_timeout_seconds,
            )
        return cls(primary=primary, backup=backup, repair_retries=settings.ai_repair_retries)

    def generate_quiz_questions(
        self,
        body: AIContentGenerateIn,
        reference_context: str | None = None,
    ) -> AIQuizQuestionsOut:
        self._validate_base(body, require_quiz_category=True)
        prompt = self._prompt(
            body,
            (
                "Retourne uniquement JSON: "
                "{\"questions\":[{question,options,correctIndex,explanation,category,level}]}. "
                "Chaque question doit avoir 4 options courtes, toutes différentes, "
                "une seule bonne réponse, et une explication pédagogique complète."
            ),
            reference_context=reference_context,
        )
        questions: list[AIQuizQuestionDraft] = []
        provider: AIProviderInfo | None = None
        next_prompt = prompt
        last_error: AIContentError | None = None
        for _ in range(self._repair_retries + 2):
            data, provider = self._generate_json(next_prompt, ["questions"])
            try:
                questions = [
                    self._normalize_question(item, body.category or QUIZ_CATEGORIES[0], body.classLevel)
                    for item in data["questions"]
                ]
                break
            except AIContentError as exc:
                last_error = exc
                next_prompt = (
                    prompt
                    + f" La réponse précédente est refusée: {exc.message}. "
                    "Régénère entièrement les questions en corrigeant ce problème."
                )
        if not questions:
            raise last_error or AIContentError("Aucune question valide générée.")
        return AIQuizQuestionsOut(provider=provider, questions=questions)

    def generate_delf_test(
        self,
        body: AIContentGenerateIn,
        reference_context: str | None = None,
    ) -> AIDelfTestOut:
        self._validate_base(body, require_quiz_category=False)
        prompt = self._prompt(
            body,
            (
                "Retourne uniquement JSON: {\"name\":\"...\",\"description\":\"...\","
                "\"questionsByCategory\":{\"Grammaire\":[...],\"Conjugaison\":[...],"
                "\"Orthographe\":[...],\"Vocabulaire\":[...]}}. "
                "Chaque catégorie doit contenir le nombre demandé de questions. "
                "Chaque question suit {question,options,correctIndex,explanation,category,level} "
                "avec 4 options différentes et une explication pédagogique complète."
            ),
            reference_context=reference_context,
        )
        grouped: dict[str, list[AIQuizQuestionDraft]] = {}
        provider: AIProviderInfo | None = None
        data: dict[str, Any] = {}
        next_prompt = prompt
        last_error: AIContentError | None = None
        for _ in range(self._repair_retries + 2):
            data, provider = self._generate_json(next_prompt, ["questionsByCategory"])
            try:
                grouped = {}
                for category in QUIZ_CATEGORIES:
                    raw_items = data.get("questionsByCategory", {}).get(category, [])
                    grouped[category] = [
                        self._normalize_question(item, category, body.classLevel)
                        for item in raw_items[: body.count]
                    ]
                    if not grouped[category]:
                        raise AIContentError(f"La catégorie {category} ne contient aucune question valide.")
                break
            except AIContentError as exc:
                last_error = exc
                next_prompt = (
                    prompt
                    + f" La réponse précédente est refusée: {exc.message}. "
                    "Régénère entièrement le test en corrigeant ce problème dans toutes les catégories."
                )
        if not grouped:
            raise last_error or AIContentError("Aucun test DELF valide généré.")
        draft = AIDelfTestDraft(
            name=str(data.get("name") or f"Test DELF {body.targetDelfLevel} - {body.classLevel}"),
            description=data.get("description") or "Brouillon généré par l'assistant IA.",
            classLevel=body.classLevel,
            targetDelfLevel=body.targetDelfLevel,
            questionsByCategory=grouped,
        )
        return AIDelfTestOut(provider=provider, test=draft)

    def generate_lesson(
        self,
        body: AIContentGenerateIn,
        reference_context: str | None = None,
    ) -> AILessonOut:
        self._validate_base(body, require_lesson_category=True)
        prompt = self._prompt(
            body,
            (
                "Retourne uniquement JSON: {\"lesson\":{title,content,category,level,sortOrder}}. "
                "La leçon doit avoir un titre clair, un objectif, une explication progressive, "
                "2 exemples adaptés au niveau, une mini-activité, et une phrase de révision."
            ),
            reference_context=reference_context,
        )
        data, provider = self._generate_json(prompt, ["lesson"])
        lesson = data["lesson"]
        draft = AILessonDraft(
            title=str(lesson.get("title") or f"Leçon {body.category}"),
            content=str(lesson.get("content") or ""),
            category=body.category or LESSON_CATEGORIES[0],
            level=body.classLevel,
            sortOrder=int(lesson.get("sortOrder") or 0),
        )
        return AILessonOut(provider=provider, lesson=draft)

    def generate_learning_path(
        self,
        body: AIContentGenerateIn,
        reference_context: str | None = None,
    ) -> AILearningPathOut:
        self._validate_base(body, require_quiz_category=False)
        prompt = self._prompt(
            body,
            (
                "Retourne uniquement JSON: {\"path\":{title,description,classLevel,"
                "delfTargetLevel,minScore,maxScore,isDefault}}. "
                "Le parcours doit expliquer pour quel résultat DELF il est utile, "
                "quels besoins d'élève il cible, et rester cohérent avec les parcours existants."
            ),
            reference_context=reference_context,
        )
        data, provider = self._generate_json(prompt, ["path"])
        raw = data["path"]
        draft = AILearningPathDraft(
            title=str(raw.get("title") or f"Parcours DELF {body.targetDelfLevel}"),
            description=raw.get("description") or "",
            classLevel=body.classLevel,
            delfTargetLevel=body.targetDelfLevel,
            minScore=raw.get("minScore"),
            maxScore=raw.get("maxScore"),
            isDefault=bool(raw.get("isDefault", False)),
        )
        return AILearningPathOut(provider=provider, path=draft)

    def _validate_base(
        self,
        body: AIContentGenerateIn,
        *,
        require_quiz_category: bool = False,
        require_lesson_category: bool = False,
    ) -> None:
        if body.classLevel not in CLASS_LEVELS:
            raise AIContentError("Niveau scolaire invalide.")
        if body.targetDelfLevel not in DELF_LEVELS:
            raise AIContentError("Niveau DELF invalide.")
        if require_quiz_category and body.category not in QUIZ_CATEGORIES:
            raise AIContentError("Catégorie de quiz invalide.")
        if require_lesson_category and body.category not in LESSON_CATEGORIES:
            raise AIContentError("Catégorie de leçon invalide.")

    def _prompt(
        self,
        body: AIContentGenerateIn,
        output_contract: str,
        *,
        reference_context: str | None = None,
    ) -> str:
        extra = body.teacherInstructions.strip() if body.teacherInstructions else DEFAULT_PEDAGOGICAL_PROMPT
        references = reference_context.strip() if reference_context else "Aucune donnée existante pertinente."
        return (
            "Mission: générer un brouillon pédagogique fiable pour le dashboard admin DELFy. "
            "Contraintes qualité obligatoires: français correct, niveau adapté, aucune ambiguïté, "
            "aucune réponse en double, aucune formulation trop avancée pour l'élève, aucune copie de texte protégé. "
            "Pour les QCM: la bonne option doit être objectivement correcte, les distracteurs doivent être plausibles "
            "mais clairement faux, et l'explication doit citer la règle ou le raisonnement. "
            "N'utilise jamais une consigne trop vague comme 'Quelle phrase est correcte ?' sans contexte précis. "
            "La question doit contenir la cible exacte à évaluer pour qu'une seule option soit possible. "
            "Pour les leçons: structure claire, exemples courts, activité finale, ton professeur. "
            f"Niveau scolaire: {body.classLevel}. Niveau DELF cible: {body.targetDelfLevel}. "
            f"Catégorie: {body.category or 'toutes les catégories DELF'}. "
            f"Nombre demandé: {body.count}. Difficulté: {body.difficulty}. "
            f"Consignes professeur: {extra}. "
            f"Données existantes du projet à respecter comme style et contexte, sans les recopier: {references}. "
            f"{output_contract} "
            "Ne mets aucun Markdown, aucun commentaire, uniquement un objet JSON valide."
        )

    def _generate_json(
        self,
        prompt: str,
        required_keys: list[str],
    ) -> tuple[dict[str, Any], AIProviderInfo]:
        errors: list[str] = []
        for index, provider in enumerate([self._primary, self._backup]):
            if provider is None:
                continue
            try:
                result = provider.generate(prompt)
                data = self._parse_json(result.text)
                for _ in range(self._repair_retries):
                    if self._has_keys(data, required_keys):
                        break
                    result = provider.generate(
                        prompt + " Corrige et retourne uniquement le JSON avec les clés demandées."
                    )
                    data = self._parse_json(result.text)
                if not self._has_keys(data, required_keys):
                    raise AIContentError("La réponse IA ne respecte pas le format attendu.")
                return data, AIProviderInfo(
                    provider=result.provider,
                    model=result.model,
                    usedBackup=index > 0,
                )
            except (AIContentError, httpx.HTTPError, KeyError, ValueError, ValidationError) as exc:
                errors.append(str(exc))
        raise AIContentError("Aucun fournisseur IA disponible. " + " | ".join(errors))

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end >= start:
            cleaned = cleaned[start : end + 1]
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise AIContentError("La réponse IA doit être un objet JSON.")
        return data

    def _has_keys(self, data: dict[str, Any], keys: list[str]) -> bool:
        return all(key in data for key in keys)

    def _normalize_question(
        self,
        item: dict[str, Any],
        category: str,
        level: str,
    ) -> AIQuizQuestionDraft:
        options = [
            _clean_option(str(option))
            for option in item.get("options", [])
            if str(option).strip()
        ]
        correct_index = int(item.get("correctIndex", 0))
        question = str(item.get("question") or "").strip()
        explanation = str(item.get("explanation") or "").strip()
        if not question:
            raise AIContentError("Une question générée est vide.")
        if not question.endswith("?"):
            raise AIContentError("Une question générée doit être formulée comme une vraie question.")
        if question.casefold() in GENERIC_QUESTION_STEMS:
            raise AIContentError("Une question générée est trop vague pour garantir une seule bonne réponse.")
        if len(options) != 4:
            raise AIContentError("Une question générée doit contenir exactement quatre options.")
        if question.casefold() in {option.casefold() for option in options}:
            raise AIContentError("Le texte de la question ne doit pas être identique à une option.")
        if len({option.casefold() for option in options}) != len(options):
            raise AIContentError("Une question générée contient des options en double.")
        if correct_index < 0 or correct_index >= len(options):
            raise AIContentError("Index de bonne réponse invalide dans une question générée.")
        if len(explanation) < 12:
            raise AIContentError("Une question générée doit contenir une explication pédagogique.")
        return AIQuizQuestionDraft(
            question=question,
            options=options,
            correctIndex=correct_index,
            explanation=explanation,
            category=category,
            level=level,
        )


def _build_provider(
    provider: str,
    *,
    model: str,
    token: str,
    nvidia_key: str,
    timeout: float,
) -> AIProvider:
    normalized = provider.strip().lower()
    if normalized in {"hf", "huggingface", "hugging-face"}:
        return HuggingFaceProvider(token=token, model=model, timeout=timeout)
    if normalized == "nvidia":
        return NvidiaProvider(api_key=nvidia_key, model=model, timeout=timeout)
    raise AIContentError(f"Fournisseur IA non supporté: {provider}")


def _clean_option(value: str) -> str:
    return re.sub(r"^[A-Da-d][).:-]\s*", "", value.strip()).strip()
