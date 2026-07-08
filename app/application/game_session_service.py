import random
from datetime import datetime, timezone
from uuid import UUID

from app.application.difficulty_service import DifficultyService
from app.application.student_stats_service import StudentStatsService
from app.domain.constants import ALLOWED_DIFFICULTIES, DIFFICULTY_MODES
from app.domain.entities import GameParticipant, MultiplayerRoom, User
from app.domain.ports import (
    IGameRepository,
    IMultiplayerRepository,
    IQuizRepository,
    IUserRepository,
)


class GameSessionError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class GameSessionService:
    def __init__(
        self,
        rooms: IMultiplayerRepository,
        games: IGameRepository,
        quiz: IQuizRepository,
        users: IUserRepository,
        stats_service: StudentStatsService,
        difficulty_service: DifficultyService,
    ) -> None:
        self._rooms = rooms
        self._games = games
        self._quiz = quiz
        self._users = users
        self._stats = stats_service
        self._difficulty = difficulty_service

    def join_room(self, user: User, room_code: str) -> MultiplayerRoom:
        room = self._rooms.get_by_code(room_code)
        if room is None:
            raise GameSessionError("Code de salle invalide")
        participants = room.data.get("participants") or []
        participant_ids = {p.get("id") for p in participants}
        user_key = str(user.id)
        if user_key not in participant_ids:
            raise GameSessionError(
                "Vous n'êtes pas invité à rejoindre cette salle"
            )
        data = dict(room.data)
        data["status"] = data.get("status") or "waiting"
        if user_key not in {p.get("id") for p in data.get("players") or []}:
            players = list(data.get("players") or participants)
            data["players"] = players
        updated = self._rooms.update_data(room.id, data)
        return updated if updated else room

    def list_my_rooms(self, user: User) -> list[MultiplayerRoom]:
        return self._rooms.list_for_student(user.id)

    def get_room(self, user: User, room_id: UUID) -> dict:
        room = self._require_room_access(user, room_id)
        session = None
        if room.active_session_id:
            session = self._games.get_session(room.active_session_id)
        participants = self._build_room_participants(room)
        return {"room": room, "session": session, "participants": participants}

    def start_session(
        self,
        user: User,
        room_id: UUID,
        game_slug: str,
        difficulty: str,
    ) -> dict:
        if difficulty not in DIFFICULTY_MODES:
            raise GameSessionError("Difficulté invalide")
        room = self._require_room_access(user, room_id)
        self._require_can_start(user, room)
        if room.active_session_id:
            existing = self._games.get_session(room.active_session_id)
            if existing and existing.status in ("waiting", "in_progress"):
                raise GameSessionError("Une partie est déjà en cours")
        game = self._games.get_game_by_slug(game_slug)
        if game is None or not game.is_active:
            raise GameSessionError("Jeu introuvable")
        participants = room.data.get("participants") or []
        if len(participants) < game.min_players:
            raise GameSessionError(
                f"Minimum {game.min_players} joueurs requis"
            )
        class_level = room.class_level or room.data.get("classLevel") or user.class_level
        if not class_level:
            raise GameSessionError("Niveau scolaire non défini pour la salle")
        settings = self._difficulty.build_game_settings(difficulty)
        question_count = settings["questionCount"]
        question_level = self._difficulty.resolve_question_level(
            class_level, difficulty
        )
        all_questions = self._quiz.list_by_level(question_level)
        if len(all_questions) < question_count:
            all_questions = self._quiz.list_by_level(class_level)
        if not all_questions:
            raise GameSessionError("Aucune question disponible pour ce niveau")
        selected = random.sample(
            all_questions, min(question_count, len(all_questions))
        )
        question_ids = [str(q.id) for q in selected]
        session = self._games.create_session(
            room_id=room.id,
            game_id=game.id,
            difficulty=difficulty,
            class_level=class_level,
            question_ids=question_ids,
            total_rounds=len(question_ids),
            settings=settings,
        )
        now = datetime.now(timezone.utc)
        self._games.update_session(
            session.id,
            status="in_progress",
            current_round=1,
            started_at=now,
        )
        for participant in participants:
            user_id = UUID(participant["id"])
            self._games.add_participant(session.id, user_id)
        self._rooms.set_active_session(room.id, session.id)
        data = dict(room.data)
        data["status"] = "in_progress"
        data["activeSessionId"] = str(session.id)
        data["allowedDifficulties"] = list(ALLOWED_DIFFICULTIES)
        self._rooms.update_data(room.id, data)
        refreshed = self._games.get_session(session.id)
        questions = self._sanitize_questions(question_ids)
        return {
            "session": refreshed,
            "questions": questions,
            "settings": settings,
        }

    def get_session_state(self, user: User, session_id: UUID) -> dict:
        session = self._require_session_access(user, session_id)
        participants = self._games.list_participants(session_id)
        leaderboard = self._build_leaderboard(participants)
        current_question = self._current_question(session)
        return {
            "session": session,
            "leaderboard": leaderboard,
            "currentQuestion": current_question,
        }

    def submit_answer(
        self,
        user: User,
        session_id: UUID,
        question_id: UUID,
        selected_index: int,
        time_ms: int,
    ) -> dict:
        session = self._require_session_access(user, session_id)
        if session.status != "in_progress":
            raise GameSessionError("La partie n'est pas active")
        participant = self._games.get_participant(session_id, user.id)
        if participant is None:
            raise GameSessionError("Participant introuvable")
        question_key = str(question_id)
        if any(a.get("questionId") == question_key for a in participant.answers):
            raise GameSessionError("Question déjà répondue")
        question = self._quiz.get(question_id)
        if question is None:
            raise GameSessionError("Question introuvable")
        if question_key not in session.question_ids:
            raise GameSessionError("Question hors partie")
        is_correct = selected_index == question.correct_index
        base_points = 100 if is_correct else 0
        multiplier = self._difficulty.resolve_score_multiplier(
            session.difficulty, user.level
        )
        points = int(base_points * multiplier)
        if is_correct and time_ms > 0:
            time_bonus = max(0, int((session.settings.get("timeLimitMs", 30000) - time_ms) / 1000))
            points += min(time_bonus, 20)
        answers = list(participant.answers)
        answers.append(
            {
                "questionId": question_key,
                "selectedIndex": selected_index,
                "isCorrect": is_correct,
                "timeMs": time_ms,
                "points": points,
            }
        )
        new_score = participant.score + points
        finished_at = None
        if len(answers) >= session.total_rounds:
            finished_at = datetime.now(timezone.utc)
        updated = self._games.update_participant(
            participant.id,
            score=new_score,
            answers=answers,
            finished_at=finished_at,
        )
        assert updated is not None
        answered_count = len(answers)
        if answered_count < session.total_rounds:
            self._games.update_session(
                session_id, current_round=answered_count + 1
            )
        else:
            self._maybe_finish_session(session_id)
        return {
            "isCorrect": is_correct,
            "points": points,
            "totalScore": new_score,
            "roundResult": {
                "correctIndex": question.correct_index,
                "explanation": question.explanation,
            },
        }

    def get_results(self, user: User, session_id: UUID) -> dict:
        session = self._require_session_access(user, session_id)
        if session.status != "finished":
            raise GameSessionError("La partie n'est pas terminée")
        participants = self._games.list_participants(session_id)
        leaderboard = self._build_leaderboard(participants)
        my_entry = next(
            (p for p in leaderboard if p["userId"] == str(user.id)),
            None,
        )
        return {"session": session, "leaderboard": leaderboard, "myResult": my_entry}

    def _maybe_finish_session(self, session_id: UUID) -> None:
        session = self._games.get_session(session_id)
        if session is None:
            return
        participants = self._games.list_participants(session_id)
        if not participants:
            return
        if not all(p.finished_at is not None for p in participants):
            return
        ranked = sorted(participants, key=lambda p: p.score, reverse=True)
        for index, participant in enumerate(ranked, start=1):
            self._games.update_participant(participant.id, rank=index)
            xp = max(5, participant.score // 10)
            if index == 1:
                xp += 20
            self._stats.record_activity(participant.user_id, xp)
        now = datetime.now(timezone.utc)
        self._games.update_session(
            session_id, status="finished", ended_at=now
        )
        room = self._rooms.get_by_id(session.room_id)
        if room:
            data = dict(room.data)
            data["status"] = "finished"
            self._rooms.update_data(room.id, data)

    def _build_leaderboard(
        self, participants: list[GameParticipant]
    ) -> list[dict]:
        sorted_participants = sorted(
            participants, key=lambda p: p.score, reverse=True
        )
        result: list[dict] = []
        for index, participant in enumerate(sorted_participants, start=1):
            user = self._users.get_by_id(participant.user_id)
            result.append(
                {
                    "userId": str(participant.user_id),
                    "firstName": user.first_name if user else "",
                    "lastName": user.last_name if user else "",
                    "score": participant.score,
                    "rank": participant.rank or index,
                    "finished": participant.finished_at is not None,
                }
            )
        return result

    def _current_question(self, session) -> dict | None:
        if session.status != "in_progress":
            return None
        if session.current_round <= 0 or session.current_round > len(session.question_ids):
            return None
        question_id = UUID(session.question_ids[session.current_round - 1])
        question = self._quiz.get(question_id)
        if question is None:
            return None
        return {
            "id": str(question.id),
            "question": question.question,
            "options": question.options,
            "round": session.current_round,
            "totalRounds": session.total_rounds,
        }

    def _sanitize_questions(self, question_ids: list[str]) -> list[dict]:
        result: list[dict] = []
        for question_id in question_ids:
            question = self._quiz.get(UUID(question_id))
            if question is None:
                continue
            result.append(
                {
                    "id": str(question.id),
                    "question": question.question,
                    "options": question.options,
                    "category": question.category,
                    "level": question.level,
                }
            )
        return result

    def _require_room_access(self, user: User, room_id: UUID) -> MultiplayerRoom:
        room = self._rooms.get_by_id(room_id)
        if room is None:
            raise GameSessionError("Salle introuvable")
        participants = room.data.get("participants") or []
        participant_ids = {p.get("id") for p in participants}
        if str(user.id) not in participant_ids and user.role != "prof":
            if user.role == "admin":
                return room
            raise GameSessionError("Accès refusé à cette salle")
        return room

    def _require_session_access(self, user: User, session_id: UUID):
        session = self._games.get_session(session_id)
        if session is None:
            raise GameSessionError("Partie introuvable")
        room = self._rooms.get_by_id(session.room_id)
        if room is None:
            raise GameSessionError("Salle introuvable")
        if user.role in ("admin", "prof"):
            return session
        participant = self._games.get_participant(session_id, user.id)
        if participant is None:
            participants = room.data.get("participants") or []
            if str(user.id) not in {p.get("id") for p in participants}:
                raise GameSessionError("Accès refusé à cette partie")
            self._games.add_participant(session_id, user.id)
        return session

    def _require_can_start(self, user: User, room: MultiplayerRoom) -> None:
        if user.role in ("prof", "admin"):
            if user.role == "prof" and room.professor_id != user.id:
                raise GameSessionError("Seul le professeur de la salle peut lancer la partie")
            return
        host_id = room.data.get("hostId")
        if host_id and host_id != str(user.id):
            raise GameSessionError("Seul l'hôte peut lancer la partie")

    def _build_room_participants(self, room: MultiplayerRoom) -> list[dict]:
        return list(room.data.get("participants") or [])
