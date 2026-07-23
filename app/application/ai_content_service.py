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
    AIDelfMockAssetDraft,
    AIDelfMockExamDraft,
    AIDelfMockExamOut,
    AIDelfMockItemDraft,
    AIDelfMockSectionDraft,
    AIGeneratedLessonDraft,
    AIGeneratedStoryDraft,
    AILearningPathDraft,
    AILearningPathOut,
    AILearningPathStepDraft,
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
    DELF_MOCK_LEVELS_BY_TRACK,
    DELF_MOCK_SECTION_LABELS,
    DELF_MOCK_SECTION_TYPES,
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
        for _ in range(self._repair_retries + 1):
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
        for _ in range(self._repair_retries + 1):
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

    def generate_delf_mock_exam(
        self,
        body: AIContentGenerateIn,
        reference_context: str | None = None,
    ) -> AIDelfMockExamOut:
        self._validate_base(body, require_quiz_category=False)
        track = self._mock_track_for(body)
        if body.targetDelfLevel not in DELF_MOCK_LEVELS_BY_TRACK[track]:
            raise AIContentError(f"Niveau DELF invalide pour DELF {track}.")
        section_contract = (
            "Retourne uniquement JSON: {\"exam\":{track,level,title,description,status,"
            "sourceNotes,sections,assets}}. sections contient exactement 4 objets dans cet ordre: "
            "listening, reading, writing, speaking. Chaque section suit {sectionOrder,sectionType,"
            "title,durationMinutes,points,instructions,audioUrl,rubric,metadata,items}. "
            "Chaque section vaut exactement 25 points. Chaque item suit {itemOrder,title,prompt,"
            "points,content,answerKey,rubric,metadata}. Les points des items totalisent 25 par section. "
            "assets est une liste, vide si aucune ressource n'est nécessaire."
        )
        prompt = self._prompt(
            body,
            (
                "Génère un examen blanc DELF officiel en forme et en fond, mais entièrement original. "
                "Ne copie aucun sujet, texte, dialogue, image ou correction officielle. "
                f"Déclinaison: DELF {track}. Niveau: {body.targetDelfLevel}. "
                "Compétences obligatoires: compréhension de l'oral, compréhension des écrits, "
                "production écrite, production orale. Total obligatoire: 100 points. "
                "Ajoute dans sourceNotes une mention indiquant que le brouillon doit être relu par un professeur. "
                "Pour listening, crée des scripts audio originaux dans content.transcripts et laisse audioUrl null. "
                "Pour writing et speaking, fournis des grilles de correction utilisables dans rubric. "
                "Inclure les règles: seuil de réussite 50/100 et note minimale 5/25 par épreuve. "
                f"{section_contract}"
            ),
            reference_context=reference_context,
        )
        next_prompt = prompt
        provider: AIProviderInfo | None = None
        last_error: AIContentError | None = None
        for _ in range(self._repair_retries + 1):
            data, provider = self._generate_json(next_prompt, ["exam"])
            try:
                draft = self._normalize_mock_exam(data["exam"], body, track)
                return AIDelfMockExamOut(provider=provider, exam=draft)
            except (AIContentError, ValidationError) as exc:
                last_error = AIContentError(str(exc))
                next_prompt = (
                    prompt
                    + f" La réponse précédente est refusée: {last_error.message}. "
                    "Régénère entièrement l'examen blanc en corrigeant ce problème."
                )
        raise last_error or AIContentError("Aucun examen blanc DELF valide généré.")

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
        student_profile: dict[str, Any] | None = None,
    ) -> AILearningPathOut:
        self._validate_base(body, require_quiz_category=False)
        prompt = self._learning_path_prompt(
            body,
            student_profile=student_profile,
            reference_context=reference_context,
        )
        provider: AIProviderInfo | None = None
        next_prompt = prompt
        last_error: AIContentError | None = None
        for _ in range(self._repair_retries + 1):
            data, provider = self._generate_json(next_prompt, ["path", "steps"])
            try:
                return self._normalize_learning_path(data, body, provider)
            except (AIContentError, ValidationError) as exc:
                last_error = AIContentError(str(exc))
                next_prompt = (
                    prompt
                    + f" La réponse précédente est refusée: {last_error.message}. "
                    "Régénère entièrement le parcours en corrigeant ce problème."
                )
        raise last_error or AIContentError("Aucun parcours IA valide généré.")

    def generate_student_hint(
        self,
        *,
        question: str,
        selected_answer: str | None,
        correct_answer: str | None,
        explanation: str | None,
        category: str,
    ) -> tuple[str, AIProviderInfo]:
        prompt = (
            "Aide un élève à comprendre une erreur de QCM sans donner une nouvelle question. "
            "Réponds en français simple, en 3 phrases maximum. "
            "Donne un indice guidé: rappelle la règle, explique pourquoi son choix pose problème, "
            "puis invite l'élève à relire la bonne réponse. "
            f"Catégorie: {category}. "
            f"Question: {question}. "
            f"Réponse choisie: {selected_answer or 'non fournie'}. "
            f"Bonne réponse: {correct_answer or 'non fournie'}. "
            f"Explication professeur: {explanation or 'non fournie'}."
        )
        errors: list[str] = []
        for index, provider in enumerate([self._primary, self._backup]):
            if provider is None:
                continue
            try:
                result = provider.generate(prompt)
                hint = result.text.strip()
                if not hint:
                    raise AIContentError("Réponse IA vide.")
                return hint, AIProviderInfo(
                    provider=result.provider,
                    model=result.model,
                    usedBackup=index > 0,
                )
            except (AIContentError, httpx.HTTPError, KeyError, ValueError) as exc:
                errors.append(str(exc))
        raise AIContentError("Aucun fournisseur IA disponible. " + " | ".join(errors))

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

    def _mock_track_for(self, body: AIContentGenerateIn) -> str:
        if body.targetDelfLevel == "A1.1":
            return "Prime"
        if body.classLevel in CLASS_LEVELS[:5]:
            return "Prime"
        return "Junior"

    def _normalize_mock_exam(
        self,
        raw: dict[str, Any],
        body: AIContentGenerateIn,
        track: str,
    ) -> AIDelfMockExamDraft:
        sections = raw.get("sections")
        if not isinstance(sections, list) or len(sections) != 4:
            raise AIContentError("L'examen blanc doit contenir exactement 4 épreuves.")
        normalized_sections: list[AIDelfMockSectionDraft] = []
        seen: set[str] = set()
        for index, section in enumerate(sections, start=1):
            section_type = str(section.get("sectionType", "")).strip()
            if section_type not in DELF_MOCK_SECTION_TYPES:
                raise AIContentError("Une épreuve a un type invalide.")
            if section_type in seen:
                raise AIContentError("Une épreuve DELF est dupliquée.")
            seen.add(section_type)
            points = int(section.get("points") or 0)
            if points != 25:
                raise AIContentError("Chaque épreuve DELF doit valoir 25 points.")
            items = section.get("items") or []
            if not items:
                raise AIContentError("Chaque épreuve doit contenir au moins un exercice.")
            normalized_items = [
                AIDelfMockItemDraft(
                    itemOrder=item_index,
                    title=str(item.get("title") or f"Exercice {item_index}").strip(),
                    prompt=str(item.get("prompt") or "").strip(),
                    points=int(item.get("points") or 0),
                    content=dict(item.get("content") or {}),
                    answerKey=dict(item.get("answerKey") or {}),
                    rubric=dict(item.get("rubric") or {}),
                    metadata=dict(item.get("metadata") or {}),
                )
                for item_index, item in enumerate(items, start=1)
            ]
            if sum(item.points for item in normalized_items) != 25:
                raise AIContentError("Les exercices d'une épreuve doivent totaliser 25 points.")
            if any(not item.prompt for item in normalized_items):
                raise AIContentError("Chaque exercice doit contenir une consigne.")
            normalized_sections.append(
                AIDelfMockSectionDraft(
                    sectionOrder=index,
                    sectionType=section_type,
                    title=str(section.get("title") or DELF_MOCK_SECTION_LABELS[section_type]).strip(),
                    durationMinutes=int(section.get("durationMinutes") or 1),
                    points=points,
                    instructions=str(section.get("instructions") or "").strip(),
                    audioUrl=section.get("audioUrl"),
                    rubric=dict(section.get("rubric") or {}),
                    metadata=dict(section.get("metadata") or {}),
                    items=normalized_items,
                )
            )
        missing = [section for section in DELF_MOCK_SECTION_TYPES if section not in seen]
        if missing:
            raise AIContentError("Des épreuves DELF obligatoires sont manquantes.")
        assets = [
            AIDelfMockAssetDraft(
                assetType=str(asset.get("assetType") or "link").strip(),
                title=str(asset.get("title") or "Ressource").strip(),
                url=str(asset.get("url") or "").strip(),
                metadata=dict(asset.get("metadata") or {}),
            )
            for asset in raw.get("assets", [])
            if str(asset.get("url") or "").strip()
        ]
        return AIDelfMockExamDraft(
            track=track,
            level=body.targetDelfLevel,
            title=str(raw.get("title") or f"Examen blanc DELF {track} {body.targetDelfLevel}").strip(),
            description=raw.get("description") or "Brouillon d'examen blanc généré par l'assistant IA.",
            status="draft",
            sourceNotes=raw.get("sourceNotes")
            or "Contenu original généré pour entraînement. Relecture professeur obligatoire avant publication.",
            sections=normalized_sections,
            assets=assets,
        )

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

    def _learning_path_prompt(
        self,
        body: AIContentGenerateIn,
        *,
        student_profile: dict[str, Any] | None = None,
        reference_context: str | None = None,
    ) -> str:
        profile = student_profile or {}
        achieved = profile.get("achievedDelfLevel") or body.targetDelfLevel
        overall = profile.get("overallScore")
        category_scores = profile.get("categoryScores") or {}
        weak_categories = profile.get("weakCategories") or QUIZ_CATEGORIES[:2]
        strong_categories = profile.get("strongCategories") or []
        references = reference_context.strip() if reference_context else "Aucune donnée existante pertinente."
        extra = body.teacherInstructions.strip() if body.teacherInstructions else DEFAULT_PEDAGOGICAL_PROMPT
        return (
            "Mission: créer un parcours DELF personnalisé et immédiatement jouable pour un élève. "
            "Profil élève: "
            f"Classe: {body.classLevel}. "
            f"Objectif DELF initial: {profile.get('targetDelfLevel') or body.targetDelfLevel}. "
            f"Niveau DELF atteint: {achieved}. "
            f"Score global: {overall if overall is not None else 'non fourni'}/100. "
            f"Scores par catégorie: {category_scores}. "
            f"Catégories faibles à renforcer en priorité: {weak_categories}. "
            f"Catégories fortes à maintenir: {strong_categories}. "
            "Règles pédagogiques obligatoires: adapter le niveau de langue à l'âge et à la classe; "
            "commencer par les faiblesses, puis consolider, puis terminer par une révision mixte; "
            "ne pas punir l'élève, avec un ton encourageant, des consignes courtes et une progression claire; "
            "chaque étape doit être faisable dans l'application mobile existante; "
            "générer uniquement du contenu original, sans copier de textes protégés; "
            "pour les leçons: expliquer une règle, donner 2 exemples, puis une mini-activité; "
            "pour les quiz: créer 4 options différentes, une seule bonne réponse, une explication claire; "
            "pour les histoires: texte court adapté au niveau, vocabulaire simple, audioUrl null; "
            "ne jamais inventer d'UUID; si une étape référence du contenu généré, utiliser une clé locale stable "
            "comme generatedLessonKey ou generatedStoryKey. "
            "Structure recommandée: 5 à 8 étapes; 2 leçons pour les catégories faibles; "
            "2 quiz pour les catégories faibles; 1 histoire de lecture/vocabulaire; 1 quiz de révision mixte; "
            "ajouter une étape leçon ou quiz seulement si le score global est inférieur à 50. "
            f"Consignes professeur: {extra}. "
            f"Données existantes du projet à respecter comme style et contexte, sans les recopier: {references}. "
            "Retourne uniquement JSON valide: "
            "{\"path\":{title,description,classLevel,delfTargetLevel,minScore,maxScore,isDefault},"
            "\"generatedLessons\":[{key,title,content,category,level,sortOrder}],"
            "\"generatedStories\":[{key,title,content,level,audioUrl}],"
            "\"generatedQuestions\":[{question,options,correctIndex,explanation,category,level}],"
            "\"steps\":[{stepOrder,stepType,title,xpReward,quizCategory,generatedLessonKey,generatedStoryKey}],"
            "\"adaptationNotes\":\"...\"}. "
            "Ne mets aucun Markdown, aucun commentaire, uniquement un objet JSON valide."
        )

    def _normalize_learning_path(
        self,
        data: dict[str, Any],
        body: AIContentGenerateIn,
        provider: AIProviderInfo,
    ) -> AILearningPathOut:
        raw_path = data.get("path") or {}
        class_level = str(raw_path.get("classLevel") or body.classLevel).strip()
        delf_level = str(raw_path.get("delfTargetLevel") or body.targetDelfLevel).strip()
        if class_level not in CLASS_LEVELS:
            raise AIContentError("Le parcours généré contient un niveau scolaire invalide.")
        if delf_level not in DELF_LEVELS:
            raise AIContentError("Le parcours généré contient un niveau DELF invalide.")
        min_score = raw_path.get("minScore")
        max_score = raw_path.get("maxScore")
        min_score = int(min_score) if min_score is not None else None
        max_score = int(max_score) if max_score is not None else None
        if min_score is not None and (min_score < 0 or min_score > 100):
            raise AIContentError("Score minimum du parcours invalide.")
        if max_score is not None and (max_score < 0 or max_score > 100):
            raise AIContentError("Score maximum du parcours invalide.")
        if min_score is not None and max_score is not None and min_score > max_score:
            raise AIContentError("Le score minimum du parcours dépasse le score maximum.")

        path = AILearningPathDraft(
            title=str(raw_path.get("title") or f"Parcours DELF {delf_level}").strip(),
            description=str(raw_path.get("description") or "").strip(),
            classLevel=class_level,
            delfTargetLevel=delf_level,
            minScore=min_score,
            maxScore=max_score,
            isDefault=bool(raw_path.get("isDefault", False)),
        )
        lessons = [
            self._normalize_generated_lesson(item, class_level)
            for item in data.get("generatedLessons", [])
        ]
        stories = [
            self._normalize_generated_story(item, class_level)
            for item in data.get("generatedStories", [])
        ]
        questions: list[AIQuizQuestionDraft] = []
        for item in data.get("generatedQuestions", []):
            category = str(item.get("category") or body.category or "").strip()
            if category not in QUIZ_CATEGORIES:
                raise AIContentError("Une question générée contient une catégorie invalide.")
            questions.append(self._normalize_question(item, category, class_level))
        steps = [
            self._normalize_learning_path_step(item)
            for item in data.get("steps", [])
        ]
        self._validate_learning_path_steps(steps, lessons, stories)
        return AILearningPathOut(
            provider=provider,
            path=path,
            generatedLessons=lessons,
            generatedStories=stories,
            generatedQuestions=questions,
            steps=steps,
            adaptationNotes=str(data.get("adaptationNotes") or "").strip() or None,
        )

    def _normalize_generated_lesson(
        self,
        item: dict[str, Any],
        class_level: str,
    ) -> AIGeneratedLessonDraft:
        category = str(item.get("category") or "").strip()
        if category not in LESSON_CATEGORIES:
            raise AIContentError("Une leçon générée contient une catégorie invalide.")
        lesson = AIGeneratedLessonDraft(
            key=str(item.get("key") or "").strip(),
            title=str(item.get("title") or "").strip(),
            content=str(item.get("content") or "").strip(),
            category=category,
            level=str(item.get("level") or class_level).strip(),
            sortOrder=int(item.get("sortOrder") or 0),
        )
        if lesson.level not in CLASS_LEVELS:
            raise AIContentError("Une leçon générée contient un niveau invalide.")
        return lesson

    def _normalize_generated_story(
        self,
        item: dict[str, Any],
        class_level: str,
    ) -> AIGeneratedStoryDraft:
        story = AIGeneratedStoryDraft(
            key=str(item.get("key") or "").strip(),
            title=str(item.get("title") or "").strip(),
            content=str(item.get("content") or "").strip(),
            level=str(item.get("level") or class_level).strip(),
            audioUrl=item.get("audioUrl"),
        )
        if story.level not in CLASS_LEVELS:
            raise AIContentError("Une histoire générée contient un niveau invalide.")
        return story

    def _normalize_learning_path_step(
        self,
        item: dict[str, Any],
    ) -> AILearningPathStepDraft:
        step_type = str(item.get("stepType") or "").strip()
        if step_type not in {"lesson", "quiz", "story"}:
            raise AIContentError("Une étape générée contient un type invalide.")
        quiz_category = item.get("quizCategory")
        quiz_category = str(quiz_category).strip() if quiz_category else None
        if step_type == "quiz" and quiz_category not in QUIZ_CATEGORIES:
            raise AIContentError("Une étape quiz doit contenir une catégorie valide.")
        return AILearningPathStepDraft(
            stepOrder=int(item.get("stepOrder") or 0),
            stepType=step_type,
            title=str(item.get("title") or "").strip(),
            xpReward=int(item.get("xpReward") or 20),
            quizCategory=quiz_category,
            generatedLessonKey=(
                str(item.get("generatedLessonKey")).strip()
                if item.get("generatedLessonKey")
                else None
            ),
            generatedStoryKey=(
                str(item.get("generatedStoryKey")).strip()
                if item.get("generatedStoryKey")
                else None
            ),
        )

    def _validate_learning_path_steps(
        self,
        steps: list[AILearningPathStepDraft],
        lessons: list[AIGeneratedLessonDraft],
        stories: list[AIGeneratedStoryDraft],
    ) -> None:
        if len(steps) < 5 or len(steps) > 8:
            raise AIContentError("Un parcours généré doit contenir entre 5 et 8 étapes.")
        expected_orders = list(range(1, len(steps) + 1))
        if [step.stepOrder for step in steps] != expected_orders:
            raise AIContentError("Les étapes du parcours doivent être ordonnées de 1 à N.")
        lesson_keys = {lesson.key for lesson in lessons}
        story_keys = {story.key for story in stories}
        if len(lesson_keys) != len(lessons):
            raise AIContentError("Les clés de leçons générées doivent être uniques.")
        if len(story_keys) != len(stories):
            raise AIContentError("Les clés d'histoires générées doivent être uniques.")
        for step in steps:
            if step.stepType == "lesson" and step.generatedLessonKey not in lesson_keys:
                raise AIContentError("Une étape leçon référence une leçon générée introuvable.")
            if step.stepType == "story" and step.generatedStoryKey not in story_keys:
                raise AIContentError("Une étape histoire référence une histoire générée introuvable.")

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
