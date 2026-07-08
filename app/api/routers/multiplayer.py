from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_game_session_service,
    require_player,
)
from app.api.schemas.admin import MultiplayerRoomOut
from app.api.schemas.multiplayer import (
    GameOut,
    GameSessionOut,
    JoinRoomIn,
    LeaderboardEntryOut,
    RoomDetailOut,
    SessionResultsOut,
    SessionStateOut,
    StartSessionIn,
    SubmitAnswerIn,
    SubmitAnswerOut,
)
from app.application.game_session_service import GameSessionError, GameSessionService
from app.domain.entities import User
from app.domain.ports import IGameRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.repositories.sql_game_repository import SqlGameRepository

router = APIRouter(prefix="/multiplayer", tags=["multiplayer"])


def _session_out(session) -> GameSessionOut:
    return GameSessionOut(
        id=session.id,
        roomId=session.room_id,
        gameId=session.game_id,
        difficulty=session.difficulty,
        classLevel=session.class_level,
        status=session.status,
        currentRound=session.current_round,
        totalRounds=session.total_rounds,
        settings=session.settings,
        startedAt=session.started_at,
        endedAt=session.ended_at,
    )


@router.get("/games", response_model=list[GameOut])
def list_games(
    db: Session = Depends(get_db),
    user: User = Depends(require_player),
) -> list[GameOut]:
    repo = SqlGameRepository(db)
    return [
        GameOut(
            id=g.id,
            slug=g.slug,
            name=g.name,
            description=g.description,
            minPlayers=g.min_players,
            maxPlayers=g.max_players,
            defaultQuestionCount=g.default_question_count,
        )
        for g in repo.list_games()
    ]


@router.post("/join", response_model=MultiplayerRoomOut)
def join_room(
    body: JoinRoomIn,
    user: User = Depends(require_player),
    svc: GameSessionService = Depends(get_game_session_service),
) -> MultiplayerRoomOut:
    try:
        room = svc.join_room(user, body.roomCode)
    except GameSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.message
        ) from exc
    return MultiplayerRoomOut.from_domain(room)


@router.get("/rooms/mine", response_model=list[MultiplayerRoomOut])
def list_my_rooms(
    user: User = Depends(require_player),
    svc: GameSessionService = Depends(get_game_session_service),
) -> list[MultiplayerRoomOut]:
    rooms = svc.list_my_rooms(user)
    return [MultiplayerRoomOut.from_domain(r) for r in rooms]


@router.get("/rooms/{room_id}", response_model=RoomDetailOut)
def get_room(
    room_id: UUID,
    user: User = Depends(require_player),
    svc: GameSessionService = Depends(get_game_session_service),
) -> RoomDetailOut:
    try:
        data = svc.get_room(user, room_id)
    except GameSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=exc.message
        ) from exc
    room = data["room"]
    session = data["session"]
    return RoomDetailOut(
        id=room.id,
        roomCode=room.room_code,
        label=room.label,
        classLevel=room.class_level or room.data.get("classLevel"),
        status=room.data.get("status", "waiting"),
        activeSessionId=room.active_session_id,
        participants=data["participants"],
        session=_session_out(session) if session else None,
    )


@router.post("/rooms/{room_id}/sessions")
def start_session(
    room_id: UUID,
    body: StartSessionIn,
    user: User = Depends(require_player),
    svc: GameSessionService = Depends(get_game_session_service),
) -> dict:
    try:
        result = svc.start_session(
            user, room_id, body.gameSlug, body.difficulty
        )
    except GameSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    session = result["session"]
    assert session is not None
    return {
        "session": _session_out(session),
        "questions": result["questions"],
        "settings": result["settings"],
    }


@router.get("/sessions/{session_id}", response_model=SessionStateOut)
def get_session_state(
    session_id: UUID,
    user: User = Depends(require_player),
    svc: GameSessionService = Depends(get_game_session_service),
) -> SessionStateOut:
    try:
        data = svc.get_session_state(user, session_id)
    except GameSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=exc.message
        ) from exc
    return SessionStateOut(
        session=_session_out(data["session"]),
        leaderboard=[
            LeaderboardEntryOut(**entry) for entry in data["leaderboard"]
        ],
        currentQuestion=data["currentQuestion"],
    )


@router.post("/sessions/{session_id}/answers", response_model=SubmitAnswerOut)
def submit_answer(
    session_id: UUID,
    body: SubmitAnswerIn,
    user: User = Depends(require_player),
    svc: GameSessionService = Depends(get_game_session_service),
) -> SubmitAnswerOut:
    try:
        result = svc.submit_answer(
            user,
            session_id,
            body.questionId,
            body.selectedIndex,
            body.timeMs,
        )
    except GameSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    return SubmitAnswerOut(
        isCorrect=result["isCorrect"],
        points=result["points"],
        totalScore=result["totalScore"],
        roundResult=result["roundResult"],
    )


@router.get("/sessions/{session_id}/results", response_model=SessionResultsOut)
def get_session_results(
    session_id: UUID,
    user: User = Depends(require_player),
    svc: GameSessionService = Depends(get_game_session_service),
) -> SessionResultsOut:
    try:
        data = svc.get_results(user, session_id)
    except GameSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    return SessionResultsOut(
        session=_session_out(data["session"]),
        leaderboard=[
            LeaderboardEntryOut(**entry) for entry in data["leaderboard"]
        ],
        myResult=(
            LeaderboardEntryOut(**data["myResult"])
            if data["myResult"]
            else None
        ),
    )
