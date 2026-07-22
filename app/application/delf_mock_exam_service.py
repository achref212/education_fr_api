from typing import Any
from uuid import UUID

from app.domain.constants import (
    DELF_MOCK_LEVELS_BY_TRACK,
    DELF_MOCK_SECTION_LABELS,
    DELF_MOCK_SECTION_TYPES,
    DELF_MOCK_STATUSES,
)
from app.domain.entities import DelfMockExam
from app.domain.ports import IDelfMockExamRepository


class DelfMockExamError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DelfMockExamService:
    def __init__(self, exams: IDelfMockExamRepository) -> None:
        self._exams = exams

    def list_exams(
        self,
        *,
        track: str | None = None,
        level: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            self._build_out(exam)
            for exam in self._exams.list_exams(track=track, level=level, status=status)
        ]

    def get_exam(self, exam_id: UUID) -> dict[str, Any]:
        exam = self._exams.get_exam(exam_id)
        if exam is None:
            raise DelfMockExamError("Examen blanc introuvable")
        return self._build_out(exam)

    def create_exam(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._validate_payload(payload)
        exam = self._exams.create_exam(**normalized)
        return self._build_out(exam)

    def update_exam(self, exam_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._validate_payload(payload)
        exam = self._exams.update_exam(exam_id, **normalized)
        if exam is None:
            raise DelfMockExamError("Examen blanc introuvable")
        return self._build_out(exam)

    def archive_exam(self, exam_id: UUID) -> dict[str, Any]:
        exam = self._exams.archive_exam(exam_id)
        if exam is None:
            raise DelfMockExamError("Examen blanc introuvable")
        return self._build_out(exam)

    def _validate_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        track = str(payload.get("track", "")).strip()
        level = str(payload.get("level", "")).strip()
        status = str(payload.get("status") or "draft").strip()
        title = str(payload.get("title", "")).strip()
        description = _clean_optional(payload.get("description"))
        source_notes = _clean_optional(payload.get("sourceNotes"))
        sections = list(payload.get("sections") or [])
        assets = list(payload.get("assets") or [])

        if track not in DELF_MOCK_LEVELS_BY_TRACK:
            raise DelfMockExamError("Déclinaison DELF invalide")
        if level not in DELF_MOCK_LEVELS_BY_TRACK[track]:
            raise DelfMockExamError(f"Niveau {level or '—'} invalide pour DELF {track}")
        if status not in DELF_MOCK_STATUSES:
            raise DelfMockExamError("Statut d'examen blanc invalide")
        if not title:
            raise DelfMockExamError("Le titre de l'examen blanc est obligatoire")
        if len(sections) != len(DELF_MOCK_SECTION_TYPES):
            raise DelfMockExamError("Un examen blanc doit contenir 4 épreuves")

        normalized_sections = self._validate_sections(sections)
        total_points = sum(section["points"] for section in normalized_sections)
        if total_points != 100:
            raise DelfMockExamError("Le total de l'examen blanc doit être 100 points")
        total_duration = sum(section["durationMinutes"] for section in normalized_sections)

        return {
            "track": track,
            "level": level,
            "title": title,
            "description": description,
            "status": status,
            "total_duration_minutes": total_duration,
            "total_points": total_points,
            "source_notes": source_notes,
            "sections": normalized_sections,
            "assets": [self._validate_asset(asset) for asset in assets],
        }

    def _validate_sections(self, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, raw in enumerate(sections, start=1):
            section_type = str(raw.get("sectionType", "")).strip()
            if section_type not in DELF_MOCK_SECTION_TYPES:
                raise DelfMockExamError(f"Type d'épreuve invalide : {section_type or '—'}")
            if section_type in seen:
                raise DelfMockExamError(f"Épreuve dupliquée : {section_type}")
            seen.add(section_type)

            points = int(raw.get("points") or 0)
            if points != 25:
                label = DELF_MOCK_SECTION_LABELS[section_type]
                raise DelfMockExamError(f"{label} doit valoir 25 points")
            duration = int(raw.get("durationMinutes") or 0)
            if duration < 1:
                raise DelfMockExamError("La durée de chaque épreuve doit être positive")
            instructions = str(raw.get("instructions", "")).strip()
            if not instructions:
                raise DelfMockExamError("Chaque épreuve doit avoir une consigne")

            items = list(raw.get("items") or [])
            if not items:
                raise DelfMockExamError("Chaque épreuve doit contenir au moins un exercice")
            normalized_items = [
                self._validate_item(item, item_index)
                for item_index, item in enumerate(items, start=1)
            ]
            if sum(item["points"] for item in normalized_items) != points:
                label = DELF_MOCK_SECTION_LABELS[section_type]
                raise DelfMockExamError(f"Les exercices de {label} doivent totaliser 25 points")

            normalized.append(
                {
                    "sectionOrder": index,
                    "sectionType": section_type,
                    "title": str(raw.get("title") or DELF_MOCK_SECTION_LABELS[section_type]).strip(),
                    "durationMinutes": duration,
                    "points": points,
                    "instructions": instructions,
                    "audioUrl": _clean_optional(raw.get("audioUrl")),
                    "rubric": dict(raw.get("rubric") or {}),
                    "metadata": dict(raw.get("metadata") or {}),
                    "items": normalized_items,
                }
            )

        missing = [section for section in DELF_MOCK_SECTION_TYPES if section not in seen]
        if missing:
            raise DelfMockExamError("Épreuves manquantes : " + ", ".join(missing))
        return sorted(normalized, key=lambda section: section["sectionOrder"])

    def _validate_item(self, raw: dict[str, Any], index: int) -> dict[str, Any]:
        title = str(raw.get("title", "")).strip()
        prompt = str(raw.get("prompt", "")).strip()
        points = int(raw.get("points") or 0)
        if not title:
            raise DelfMockExamError("Chaque exercice doit avoir un titre")
        if not prompt:
            raise DelfMockExamError("Chaque exercice doit avoir une consigne")
        if not (1 <= points <= 25):
            raise DelfMockExamError("Les points d'un exercice doivent être entre 1 et 25")
        return {
            "itemOrder": index,
            "title": title,
            "prompt": prompt,
            "points": points,
            "content": dict(raw.get("content") or {}),
            "answerKey": dict(raw.get("answerKey") or {}),
            "rubric": dict(raw.get("rubric") or {}),
            "metadata": dict(raw.get("metadata") or {}),
        }

    def _validate_asset(self, raw: dict[str, Any]) -> dict[str, Any]:
        asset_type = str(raw.get("assetType", "")).strip()
        title = str(raw.get("title", "")).strip()
        url = str(raw.get("url", "")).strip()
        if not asset_type or not title or not url:
            raise DelfMockExamError("Chaque ressource doit avoir un type, un titre et une URL")
        return {
            "assetType": asset_type,
            "title": title,
            "url": url,
            "metadata": dict(raw.get("metadata") or {}),
        }

    def _build_out(self, exam: DelfMockExam) -> dict[str, Any]:
        return {
            "id": str(exam.id),
            "track": exam.track,
            "level": exam.level,
            "title": exam.title,
            "description": exam.description,
            "status": exam.status,
            "totalDurationMinutes": exam.total_duration_minutes,
            "totalPoints": exam.total_points,
            "sourceNotes": exam.source_notes,
            "sections": [
                {
                    "id": str(section.id),
                    "examId": str(section.exam_id),
                    "sectionOrder": section.section_order,
                    "sectionType": section.section_type,
                    "title": section.title,
                    "durationMinutes": section.duration_minutes,
                    "points": section.points,
                    "instructions": section.instructions,
                    "audioUrl": section.audio_url,
                    "rubric": section.rubric,
                    "metadata": section.metadata,
                    "items": [
                        {
                            "id": str(item.id),
                            "sectionId": str(item.section_id),
                            "itemOrder": item.item_order,
                            "title": item.title,
                            "prompt": item.prompt,
                            "points": item.points,
                            "content": item.content,
                            "answerKey": item.answer_key,
                            "rubric": item.rubric,
                            "metadata": item.metadata,
                        }
                        for item in section.items
                    ],
                }
                for section in exam.sections
            ],
            "assets": [
                {
                    "id": str(asset.id),
                    "examId": str(asset.exam_id),
                    "assetType": asset.asset_type,
                    "title": asset.title,
                    "url": asset.url,
                    "metadata": asset.metadata,
                    "createdAt": asset.created_at.isoformat(),
                }
                for asset in exam.assets
            ],
            "createdAt": exam.created_at.isoformat(),
            "updatedAt": exam.updated_at.isoformat(),
        }


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
