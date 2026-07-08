from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.application.difficulty_service import DifficultyService
from app.application.game_session_service import GameSessionError, GameSessionService
from app.application.student_stats_service import StudentStatsService
from app.domain.entities import (
    Game,
    GameParticipant,
    GameSession,
    MultiplayerRoom,
    QuizQuestion,
    User,
)


@dataclass
class FakeMultiplayerRepo:
    rooms: dict[UUID, MultiplayerRoom] = field(default_factory=dict)
    codes: dict[str, UUID] = field(default_factory=dict)

    def list_all(self) -> list[MultiplayerRoom]:
        return list(self.rooms.values())

    def list_by_professor(self, professor_id: UUID) -> list[MultiplayerRoom]:
        return [r for r in self.rooms.values() if r.professor_id == professor_id]

    def get_by_id(self, room_id: UUID) -> MultiplayerRoom | None:
        return self.rooms.get(room_id)

    def get_by_code(self, room_code: str) -> MultiplayerRoom | None:
        room_id = self.codes.get(room_code.upper())
        return self.rooms.get(room_id) if room_id else None

    def list_for_student(self, student_id: UUID) -> list[MultiplayerRoom]:
        key = str(student_id)
        return [
            r
            for r in self.rooms.values()
            if key in {p.get("id") for p in (r.data.get("participants") or [])}
        ]

    def create(
        self,
        room_code: str,
        label: str | None,
        professor_id: UUID,
        school_id: UUID | None,
        data: dict | None = None,
        class_level: str | None = None,
    ) -> MultiplayerRoom:
        now = datetime.now(timezone.utc)
        room = MultiplayerRoom(
            id=uuid4(),
            room_code=room_code,
            data=data or {},
            label=label,
            created_at=now,
            updated_at=now,
            professor_id=professor_id,
            school_id=school_id,
            class_level=class_level,
        )
        self.rooms[room.id] = room
        self.codes[room.room_code] = room.id
        return room

    def update_data(self, room_id: UUID, data: dict[str, Any]) -> MultiplayerRoom | None:
        room = self.rooms.get(room_id)
        if room is None:
            return None
        updated = MultiplayerRoom(
            id=room.id,
            room_code=room.room_code,
            data=data,
            label=room.label,
            created_at=room.created_at,
            updated_at=datetime.now(timezone.utc),
            professor_id=room.professor_id,
            school_id=room.school_id,
            class_level=room.class_level,
            active_session_id=room.active_session_id,
        )
        self.rooms[room_id] = updated
        return updated

    def set_active_session(
        self, room_id: UUID, session_id: UUID | None
    ) -> MultiplayerRoom | None:
        room = self.rooms.get(room_id)
        if room is None:
            return None
        updated = MultiplayerRoom(
            id=room.id,
            room_code=room.room_code,
            data=room.data,
            label=room.label,
            created_at=room.created_at,
            updated_at=datetime.now(timezone.utc),
            professor_id=room.professor_id,
            school_id=room.school_id,
            class_level=room.class_level,
            active_session_id=session_id,
        )
        self.rooms[room_id] = updated
        return updated

    def count(self) -> int:
        return len(self.rooms)


@dataclass
class FakeGameRepo:
    games: dict[str, Game] = field(default_factory=dict)
    sessions: dict[UUID, GameSession] = field(default_factory=dict)
    participants: dict[UUID, list[GameParticipant]] = field(default_factory=dict)

    def list_games(self, active_only: bool = True) -> list[Game]:
        games = list(self.games.values())
        if active_only:
            games = [g for g in games if g.is_active]
        return games

    def get_game_by_slug(self, slug: str) -> Game | None:
        return self.games.get(slug)

    def get_game(self, game_id: UUID) -> Game | None:
        return next((g for g in self.games.values() if g.id == game_id), None)

    def create_game(self, **kwargs) -> Game:
        raise NotImplementedError

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
        session = GameSession(
            id=uuid4(),
            room_id=room_id,
            game_id=game_id,
            difficulty=difficulty,
            class_level=class_level,
            status="waiting",
            question_ids=question_ids,
            current_round=0,
            total_rounds=total_rounds,
            settings=settings,
            created_at=now,
            updated_at=now,
        )
        self.sessions[session.id] = session
        self.participants[session.id] = []
        return session

    def get_session(self, session_id: UUID) -> GameSession | None:
        return self.sessions.get(session_id)

    def update_session(self, session_id: UUID, **kwargs) -> GameSession | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        updated = GameSession(
            id=session.id,
            room_id=session.room_id,
            game_id=session.game_id,
            difficulty=session.difficulty,
            class_level=session.class_level,
            status=kwargs.get("status", session.status),
            question_ids=session.question_ids,
            current_round=kwargs.get("current_round", session.current_round),
            total_rounds=session.total_rounds,
            settings=session.settings,
            created_at=session.created_at,
            updated_at=datetime.now(timezone.utc),
            started_at=kwargs.get("started_at", session.started_at),
            ended_at=kwargs.get("ended_at", session.ended_at),
        )
        self.sessions[session_id] = updated
        return updated

    def list_participants(self, session_id: UUID) -> list[GameParticipant]:
        return self.participants.get(session_id, [])

    def get_participant(
        self, session_id: UUID, user_id: UUID
    ) -> GameParticipant | None:
        return next(
            (
                p
                for p in self.participants.get(session_id, [])
                if p.user_id == user_id
            ),
            None,
        )

    def add_participant(self, session_id: UUID, user_id: UUID) -> GameParticipant:
        participant = GameParticipant(
            id=uuid4(),
            session_id=session_id,
            user_id=user_id,
            score=0,
            answers=[],
            joined_at=datetime.now(timezone.utc),
        )
        self.participants.setdefault(session_id, []).append(participant)
        return participant

    def update_participant(self, participant_id: UUID, **kwargs) -> GameParticipant | None:
        for session_id, items in self.participants.items():
            for index, participant in enumerate(items):
                if participant.id == participant_id:
                    updated = GameParticipant(
                        id=participant.id,
                        session_id=participant.session_id,
                        user_id=participant.user_id,
                        score=kwargs.get("score", participant.score),
                        answers=kwargs.get("answers", participant.answers),
                        joined_at=participant.joined_at,
                        rank=kwargs.get("rank", participant.rank),
                        finished_at=kwargs.get("finished_at", participant.finished_at),
                    )
                    self.participants[session_id][index] = updated
                    return updated
        return None


@dataclass
class FakeQuizRepo:
    questions: dict[UUID, QuizQuestion] = field(default_factory=dict)

    def list_all(self) -> list[QuizQuestion]:
        return list(self.questions.values())

    def list_by_level(self, level: str) -> list[QuizQuestion]:
        return [q for q in self.questions.values() if q.level == level]

    def list_by_level_and_category(
        self, level: str, category: str
    ) -> list[QuizQuestion]:
        return [
            q
            for q in self.questions.values()
            if q.level == level and q.category == category
        ]

    def get(self, question_id: UUID) -> QuizQuestion | None:
        return self.questions.get(question_id)


@dataclass
class FakeUserRepo:
    users: dict[UUID, User] = field(default_factory=dict)

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)


@dataclass
class FakeStudentProgressRepo:
    def get_stats(self, user_id: UUID):
        return None

    def upsert_stats(self, stats):
        return stats

    def get_step_progress(self, user_id: UUID, step_id: UUID):
        return None

    def list_step_progress(self, user_id: UUID):
        return []

    def upsert_step_progress(self, progress):
        return progress


def _user(role: str = "user", class_level: str = "5ème année") -> User:
    user_id = uuid4()
    return User(
        id=user_id,
        email=f"{role}@test.com",
        first_name="Test",
        last_name="User",
        level="debutant",
        created_at=datetime.now(timezone.utc),
        role=role,
        class_level=class_level,
    )


def _build_session_service(
    rooms: FakeMultiplayerRepo,
    games: FakeGameRepo,
    quiz: FakeQuizRepo,
    users: FakeUserRepo,
) -> GameSessionService:
    return GameSessionService(
        rooms=rooms,
        games=games,
        quiz=quiz,
        users=users,
        stats_service=StudentStatsService(FakeStudentProgressRepo()),
        difficulty_service=DifficultyService(),
    )


def test_join_room_requires_invitation() -> None:
    student = _user()
    other = _user()
    rooms = FakeMultiplayerRepo()
    room = rooms.create(
        room_code="ABC123",
        label="Test",
        professor_id=uuid4(),
        school_id=uuid4(),
        class_level="5ème année",
        data={
            "participants": [{"id": str(other.id)}],
            "players": [{"id": str(other.id)}],
            "status": "waiting",
        },
    )
    svc = _build_session_service(rooms, FakeGameRepo(), FakeQuizRepo(), FakeUserRepo())
    with pytest.raises(GameSessionError):
        svc.join_room(student, room.room_code)


def test_full_multiplayer_session_flow() -> None:
    prof = _user(role="prof")
    student1 = _user()
    student2 = _user()
    rooms = FakeMultiplayerRepo()
    room = rooms.create(
        room_code="ROOM01",
        label="Quiz",
        professor_id=prof.id,
        school_id=uuid4(),
        class_level="5ème année",
        data={
            "participants": [
                {"id": str(student1.id), "firstName": "A", "lastName": "One"},
                {"id": str(student2.id), "firstName": "B", "lastName": "Two"},
            ],
            "players": [],
            "status": "waiting",
        },
    )
    q1_id = uuid4()
    q2_id = uuid4()
    quiz = FakeQuizRepo(
        questions={
            q1_id: QuizQuestion(
                id=q1_id,
                question="Q1?",
                options=["a", "b"],
                correct_index=0,
                explanation=None,
                category="Grammaire",
                level="5ème année",
            ),
            q2_id: QuizQuestion(
                id=q2_id,
                question="Q2?",
                options=["a", "b"],
                correct_index=1,
                explanation=None,
                category="Grammaire",
                level="5ème année",
            ),
        }
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
    users = FakeUserRepo(
        users={
            student1.id: student1,
            student2.id: student2,
            prof.id: prof,
        }
    )
    svc = _build_session_service(rooms, games, quiz, users)
    joined = svc.join_room(student1, room.room_code)
    assert joined.id == room.id
    started = svc.start_session(prof, room.id, "quiz_duel", "medium")
    session = started["session"]
    assert session is not None
    assert session.status == "in_progress"
    result1 = svc.submit_answer(student1, session.id, q1_id, 0, 5000)
    assert result1["isCorrect"] is True
    result1b = svc.submit_answer(student1, session.id, q2_id, 0, 4000)
    assert result1b["isCorrect"] is False
    result2 = svc.submit_answer(student2, session.id, q1_id, 0, 3000)
    svc.submit_answer(student2, session.id, q2_id, 1, 2000)
    assert result2["isCorrect"] is True
    finished = games.get_session(session.id)
    assert finished is not None
    assert finished.status == "finished"
    results = svc.get_results(student1, session.id)
    assert len(results["leaderboard"]) == 2
