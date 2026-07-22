from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.delf_mock_exam_service import (
    DelfMockExamError,
    DelfMockExamService,
)
from app.domain.entities import DelfMockExam


class FakeMockExamRepo:
    def __init__(self) -> None:
        self.items: dict[UUID, DelfMockExam] = {}

    def list_exams(self, *, track=None, level=None, status=None):
        return list(self.items.values())

    def get_exam(self, exam_id: UUID):
        return self.items.get(exam_id)

    def create_exam(self, **kwargs):
        exam = _exam_from_kwargs(uuid4(), kwargs)
        self.items[exam.id] = exam
        return exam

    def update_exam(self, exam_id: UUID, **kwargs):
        if exam_id not in self.items:
            return None
        exam = _exam_from_kwargs(exam_id, kwargs)
        self.items[exam.id] = exam
        return exam

    def archive_exam(self, exam_id: UUID):
        exam = self.items.get(exam_id)
        if exam is None:
            return None
        exam.status = "archived"
        return exam


def valid_payload() -> dict:
    return {
        "track": "Prime",
        "level": "A1.1",
        "title": "Examen blanc DELF Prime A1.1",
        "description": "Original",
        "status": "published",
        "sourceNotes": "Relecture professeur requise.",
        "assets": [],
        "sections": [
            _section(1, "listening", [8, 8, 9]),
            _section(2, "reading", [8, 7, 10]),
            _section(3, "writing", [7, 8, 10]),
            _section(4, "speaking", [8, 8, 9]),
        ],
    }


def _section(order: int, section_type: str, points: list[int]) -> dict:
    return {
        "sectionOrder": order,
        "sectionType": section_type,
        "title": section_type,
        "durationMinutes": 15,
        "points": 25,
        "instructions": "Consigne",
        "audioUrl": None,
        "rubric": {},
        "metadata": {},
        "items": [
            {
                "itemOrder": index,
                "title": f"Exercice {index}",
                "prompt": "Réponds à la consigne.",
                "points": point,
                "content": {},
                "answerKey": {},
                "rubric": {},
                "metadata": {},
            }
            for index, point in enumerate(points, start=1)
        ],
    }


def _exam_from_kwargs(exam_id: UUID, kwargs: dict) -> DelfMockExam:
    now = datetime.now(timezone.utc)
    return DelfMockExam(
        id=exam_id,
        track=kwargs["track"],
        level=kwargs["level"],
        title=kwargs["title"],
        description=kwargs["description"],
        status=kwargs["status"],
        total_duration_minutes=kwargs["total_duration_minutes"],
        total_points=kwargs["total_points"],
        source_notes=kwargs["source_notes"],
        created_at=now,
        updated_at=now,
    )


def test_creates_valid_official_shape() -> None:
    service = DelfMockExamService(FakeMockExamRepo())

    result = service.create_exam(valid_payload())

    assert result["track"] == "Prime"
    assert result["level"] == "A1.1"
    assert result["totalPoints"] == 100
    assert result["totalDurationMinutes"] == 60


def test_rejects_wrong_track_level_pair() -> None:
    payload = valid_payload()
    payload["track"] = "Junior"
    payload["level"] = "A1.1"
    service = DelfMockExamService(FakeMockExamRepo())

    with pytest.raises(DelfMockExamError):
        service.create_exam(payload)


def test_rejects_missing_skill() -> None:
    payload = valid_payload()
    payload["sections"] = payload["sections"][:3] + [_section(4, "writing", [8, 8, 9])]
    service = DelfMockExamService(FakeMockExamRepo())

    with pytest.raises(DelfMockExamError):
        service.create_exam(payload)


def test_rejects_item_points_not_totaling_section() -> None:
    payload = valid_payload()
    payload["sections"][0] = _section(1, "listening", [8, 8, 8])
    service = DelfMockExamService(FakeMockExamRepo())

    with pytest.raises(DelfMockExamError):
        service.create_exam(payload)


def test_archives_exam() -> None:
    repo = FakeMockExamRepo()
    service = DelfMockExamService(repo)
    created = service.create_exam(valid_payload())

    archived = service.archive_exam(UUID(created["id"]))

    assert archived["status"] == "archived"
