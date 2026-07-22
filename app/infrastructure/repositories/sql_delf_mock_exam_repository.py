import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.entities import (
    DelfMockAsset,
    DelfMockExam,
    DelfMockItem,
    DelfMockSection,
)
from app.domain.ports import IDelfMockExamRepository
from app.infrastructure.models.delf_mock_exam import (
    DelfMockAssetORM,
    DelfMockExamORM,
    DelfMockItemORM,
    DelfMockSectionORM,
)


class SqlDelfMockExamRepository(IDelfMockExamRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_exams(
        self,
        *,
        track: str | None = None,
        level: str | None = None,
        status: str | None = None,
    ) -> list[DelfMockExam]:
        stmt = _with_nested(select(DelfMockExamORM))
        if track is not None:
            stmt = stmt.where(DelfMockExamORM.track == track)
        if level is not None:
            stmt = stmt.where(DelfMockExamORM.level == level)
        if status is not None:
            stmt = stmt.where(DelfMockExamORM.status == status)
        else:
            stmt = stmt.where(DelfMockExamORM.is_archived.is_(False))
        stmt = stmt.order_by(
            DelfMockExamORM.track.asc(),
            DelfMockExamORM.level.asc(),
            DelfMockExamORM.updated_at.desc(),
        )
        return [_exam_to_domain(row) for row in self._session.scalars(stmt).all()]

    def get_exam(self, exam_id: UUID) -> DelfMockExam | None:
        row = self._session.scalar(
            _with_nested(select(DelfMockExamORM).where(DelfMockExamORM.id == exam_id))
        )
        return _exam_to_domain(row) if row else None

    def create_exam(
        self,
        *,
        track: str,
        level: str,
        title: str,
        description: str | None,
        status: str,
        total_duration_minutes: int,
        total_points: int,
        source_notes: str | None,
        sections: list[dict[str, Any]],
        assets: list[dict[str, Any]] | None = None,
    ) -> DelfMockExam:
        now = datetime.now(timezone.utc)
        row = DelfMockExamORM(
            id=uuid.uuid4(),
            track=track,
            level=level,
            title=title,
            description=description,
            status=status,
            total_duration_minutes=total_duration_minutes,
            total_points=total_points,
            source_notes=source_notes,
            is_archived=status == "archived",
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        self._replace_children(row, sections, assets or [], now)
        self._session.flush()
        return self.get_exam(row.id) or _exam_to_domain(row)

    def update_exam(
        self,
        exam_id: UUID,
        *,
        track: str,
        level: str,
        title: str,
        description: str | None,
        status: str,
        total_duration_minutes: int,
        total_points: int,
        source_notes: str | None,
        sections: list[dict[str, Any]],
        assets: list[dict[str, Any]] | None = None,
    ) -> DelfMockExam | None:
        row = self._session.get(DelfMockExamORM, exam_id)
        if row is None:
            return None
        now = datetime.now(timezone.utc)
        row.track = track
        row.level = level
        row.title = title
        row.description = description
        row.status = status
        row.total_duration_minutes = total_duration_minutes
        row.total_points = total_points
        row.source_notes = source_notes
        row.is_archived = status == "archived"
        row.updated_at = now
        row.sections.clear()
        row.assets.clear()
        self._session.flush()
        self._replace_children(row, sections, assets or [], now)
        self._session.flush()
        return self.get_exam(row.id)

    def archive_exam(self, exam_id: UUID) -> DelfMockExam | None:
        row = self._session.get(DelfMockExamORM, exam_id)
        if row is None:
            return None
        row.status = "archived"
        row.is_archived = True
        row.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return self.get_exam(row.id)

    def _replace_children(
        self,
        row: DelfMockExamORM,
        sections: list[dict[str, Any]],
        assets: list[dict[str, Any]],
        now: datetime,
    ) -> None:
        for section_data in sections:
            section = DelfMockSectionORM(
                id=uuid.uuid4(),
                exam_id=row.id,
                section_order=int(section_data["sectionOrder"]),
                section_type=str(section_data["sectionType"]),
                title=str(section_data["title"]),
                duration_minutes=int(section_data["durationMinutes"]),
                points=int(section_data["points"]),
                instructions=str(section_data["instructions"]),
                audio_url=section_data.get("audioUrl"),
                rubric=dict(section_data.get("rubric") or {}),
                meta=dict(section_data.get("metadata") or {}),
            )
            self._session.add(section)
            self._session.flush()
            for item_data in section_data.get("items", []):
                self._session.add(
                    DelfMockItemORM(
                        id=uuid.uuid4(),
                        section_id=section.id,
                        item_order=int(item_data["itemOrder"]),
                        title=str(item_data["title"]),
                        prompt=str(item_data["prompt"]),
                        points=int(item_data["points"]),
                        content=dict(item_data.get("content") or {}),
                        answer_key=dict(item_data.get("answerKey") or {}),
                        rubric=dict(item_data.get("rubric") or {}),
                        meta=dict(item_data.get("metadata") or {}),
                    )
                )
        for asset_data in assets:
            self._session.add(
                DelfMockAssetORM(
                    id=uuid.uuid4(),
                    exam_id=row.id,
                    asset_type=str(asset_data["assetType"]),
                    title=str(asset_data["title"]),
                    url=str(asset_data["url"]),
                    meta=dict(asset_data.get("metadata") or {}),
                    created_at=now,
                )
            )


def _with_nested(stmt):
    return stmt.options(
        selectinload(DelfMockExamORM.sections).selectinload(DelfMockSectionORM.items),
        selectinload(DelfMockExamORM.assets),
    )


def _asset_to_domain(row: DelfMockAssetORM) -> DelfMockAsset:
    return DelfMockAsset(
        id=row.id,
        exam_id=row.exam_id,
        asset_type=row.asset_type,
        title=row.title,
        url=row.url,
        metadata=dict(row.meta or {}),
        created_at=row.created_at,
    )


def _item_to_domain(row: DelfMockItemORM) -> DelfMockItem:
    return DelfMockItem(
        id=row.id,
        section_id=row.section_id,
        item_order=row.item_order,
        title=row.title,
        prompt=row.prompt,
        points=row.points,
        content=dict(row.content or {}),
        answer_key=dict(row.answer_key or {}),
        rubric=dict(row.rubric or {}),
        metadata=dict(row.meta or {}),
    )


def _section_to_domain(row: DelfMockSectionORM) -> DelfMockSection:
    return DelfMockSection(
        id=row.id,
        exam_id=row.exam_id,
        section_order=row.section_order,
        section_type=row.section_type,
        title=row.title,
        duration_minutes=row.duration_minutes,
        points=row.points,
        instructions=row.instructions,
        audio_url=row.audio_url,
        rubric=dict(row.rubric or {}),
        metadata=dict(row.meta or {}),
        items=[_item_to_domain(item) for item in row.items],
    )


def _exam_to_domain(row: DelfMockExamORM) -> DelfMockExam:
    return DelfMockExam(
        id=row.id,
        track=row.track,
        level=row.level,
        title=row.title,
        description=row.description,
        status=row.status,
        total_duration_minutes=row.total_duration_minutes,
        total_points=row.total_points,
        source_notes=row.source_notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sections=[_section_to_domain(section) for section in row.sections],
        assets=[_asset_to_domain(asset) for asset in row.assets],
    )
