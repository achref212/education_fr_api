from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.game_session_service import GameSessionError
from app.domain.entities import Game
from tests.test_game_session_service import (
    FakeGameRepo,
    FakeMultiplayerRepo,
    FakeQuizRepo,
    FakeUserRepo,
    _build_session_service,
    _user,
)


def test_join_invalid_room_code_raises() -> None:
    student = _user()
    svc = _build_session_service(
        FakeMultiplayerRepo(), FakeGameRepo(), FakeQuizRepo(), FakeUserRepo()
    )
    with pytest.raises(GameSessionError, match="Code de salle invalide"):
        svc.join_room(student, "INVALID")


def test_start_session_requires_minimum_players() -> None:
    prof = _user(role="prof")
    student = _user()
    rooms = FakeMultiplayerRepo()
    room = rooms.create(
        room_code="ROOM02",
        label="Solo",
        professor_id=prof.id,
        school_id=uuid4(),
        class_level="5ème année",
        data={
            "participants": [{"id": str(student.id)}],
            "status": "waiting",
        },
    )
    game_id = uuid4()
    games = FakeGameRepo(
        games={
            "quiz_duel": Game(
                id=game_id,
                slug="quiz_duel",
                name="Quiz Duel",
                min_players=2,
                max_players=8,
                default_question_count=2,
                created_at=datetime.now(timezone.utc),
            )
        }
    )
    svc = _build_session_service(rooms, games, FakeQuizRepo(), FakeUserRepo())
    with pytest.raises(GameSessionError, match="Minimum"):
        svc.start_session(prof, room.id, "quiz_duel", "easy")
