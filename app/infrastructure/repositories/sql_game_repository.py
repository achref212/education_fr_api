import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Game, GameParticipant, GameSession
from app.domain.ports import IGameRepository
from app.infrastructure.models.game import GameORM
from app.infrastructure.models.game_participant import GameParticipantORM
from app.infrastructure.models.game_session import GameSessionORM


class SqlGameRepository(IGameRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_games(self, active_only: bool = True) -> list[Game]:
        stmt = select(GameORM)
        if active_only:
            stmt = stmt.where(GameORM.is_active.is_(True))
        stmt = stmt.order_by(GameORM.name)
        return [_game_to_domain(r) for r in self._session.scalars(stmt).all()]

    def get_game_by_slug(self, slug: str) -> Game | None:
        stmt = select(GameORM).where(GameORM.slug == slug)
        row = self._session.scalar(stmt)
        return _game_to_domain(row) if row else None

    def get_game(self, game_id: UUID) -> Game | None:
        row = self._session.get(GameORM, game_id)
        return _game_to_domain(row) if row else None

    def create_game(
        self,
        slug: str,
        name: str,
        min_players: int,
        max_players: int,
        default_question_count: int,
        description: str | None = None,
    ) -> Game:
        now = datetime.now(timezone.utc)
        row = GameORM(
            id=uuid.uuid4(),
            slug=slug,
            name=name,
            description=description,
            min_players=min_players,
            max_players=max_players,
            default_question_count=default_question_count,
            is_active=True,
            created_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _game_to_domain(row)

    def update_game(
        self,
        game_id: UUID,
        *,
        name: str | None = None,
        min_players: int | None = None,
        max_players: int | None = None,
        default_question_count: int | None = None,
        description: str | None = None,
    ) -> Game | None:
        row = self._session.get(GameORM, game_id)
        if row is None:
            return None
        if name is not None:
            row.name = name
        if min_players is not None:
            row.min_players = min_players
        if max_players is not None:
            row.max_players = max_players
        if default_question_count is not None:
            row.default_question_count = default_question_count
        if description is not None:
            row.description = description
        self._session.flush()
        return _game_to_domain(row)

    def create_session(
        self,
        room_id: UUID,
        game_id: UUID,
        difficulty: str,
        class_level: str,
        question_ids: list[str],
        total_rounds: int,
        settings: dict[str, Any],
    ) -> GameSession:
        now = datetime.now(timezone.utc)
        row = GameSessionORM(
            id=uuid.uuid4(),
            room_id=room_id,
            game_id=game_id,
            difficulty=difficulty,
            class_level=class_level,
            status="waiting",
            question_ids=list(question_ids),
            current_round=0,
            total_rounds=total_rounds,
            settings=dict(settings),
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _session_to_domain(row)

    def get_session(self, session_id: UUID) -> GameSession | None:
        row = self._session.get(GameSessionORM, session_id)
        return _session_to_domain(row) if row else None

    def update_session(
        self,
        session_id: UUID,
        *,
        status: str | None = None,
        current_round: int | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> GameSession | None:
        row = self._session.get(GameSessionORM, session_id)
        if row is None:
            return None
        if status is not None:
            row.status = status
        if current_round is not None:
            row.current_round = current_round
        if started_at is not None:
            row.started_at = started_at
        if ended_at is not None:
            row.ended_at = ended_at
        row.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return _session_to_domain(row)

    def list_participants(self, session_id: UUID) -> list[GameParticipant]:
        stmt = select(GameParticipantORM).where(
            GameParticipantORM.session_id == session_id
        )
        return [_participant_to_domain(r) for r in self._session.scalars(stmt).all()]

    def get_participant(
        self, session_id: UUID, user_id: UUID
    ) -> GameParticipant | None:
        stmt = select(GameParticipantORM).where(
            GameParticipantORM.session_id == session_id,
            GameParticipantORM.user_id == user_id,
        )
        row = self._session.scalar(stmt)
        return _participant_to_domain(row) if row else None

    def add_participant(
        self, session_id: UUID, user_id: UUID
    ) -> GameParticipant:
        now = datetime.now(timezone.utc)
        row = GameParticipantORM(
            id=uuid.uuid4(),
            session_id=session_id,
            user_id=user_id,
            score=0,
            rank=None,
            answers=[],
            joined_at=now,
            finished_at=None,
        )
        self._session.add(row)
        self._session.flush()
        return _participant_to_domain(row)

    def update_participant(
        self,
        participant_id: UUID,
        *,
        score: int | None = None,
        rank: int | None = None,
        answers: list[dict[str, Any]] | None = None,
        finished_at: datetime | None = None,
    ) -> GameParticipant | None:
        row = self._session.get(GameParticipantORM, participant_id)
        if row is None:
            return None
        if score is not None:
            row.score = score
        if rank is not None:
            row.rank = rank
        if answers is not None:
            row.answers = list(answers)
        if finished_at is not None:
            row.finished_at = finished_at
        self._session.flush()
        return _participant_to_domain(row)


def _game_to_domain(row: GameORM) -> Game:
    return Game(
        id=row.id,
        slug=row.slug,
        name=row.name,
        min_players=row.min_players,
        max_players=row.max_players,
        default_question_count=row.default_question_count,
        created_at=row.created_at,
        description=row.description,
        is_active=row.is_active,
    )


def _session_to_domain(row: GameSessionORM) -> GameSession:
    return GameSession(
        id=row.id,
        room_id=row.room_id,
        game_id=row.game_id,
        difficulty=row.difficulty,
        class_level=row.class_level,
        status=row.status,
        question_ids=[str(q) for q in (row.question_ids or [])],
        current_round=row.current_round,
        total_rounds=row.total_rounds,
        settings=dict(row.settings) if row.settings else {},
        created_at=row.created_at,
        updated_at=row.updated_at,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )


def _participant_to_domain(row: GameParticipantORM) -> GameParticipant:
    return GameParticipant(
        id=row.id,
        session_id=row.session_id,
        user_id=row.user_id,
        score=row.score,
        answers=list(row.answers) if row.answers else [],
        joined_at=row.joined_at,
        rank=row.rank,
        finished_at=row.finished_at,
    )
