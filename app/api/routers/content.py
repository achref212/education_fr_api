from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_lesson_repo, get_quiz_repo, get_story_repo, get_current_user
from app.api.schemas.admin import LessonOut, QuizQuestionOut, StoryOut
from app.domain.entities import User
from app.domain.ports import ILessonRepository, IQuizRepository, IStoryRepository

router = APIRouter(tags=["content"])


@router.get("/lessons", response_model=list[LessonOut])
def list_lessons(
    level: str | None = Query(default=None, description="Filter by class level (e.g. '2e')"),
    category: str | None = Query(default=None, description="Filter by category"),
    _user: User = Depends(get_current_user),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> list[LessonOut]:
    if level:
        items = lessons.list_by_level(level)
    elif category:
        items = lessons.list_by_category(category)
    else:
        items = lessons.list_all()
    return [LessonOut.from_domain(x) for x in items]


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(
    lesson_id: UUID,
    _user: User = Depends(get_current_user),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> LessonOut:
    lesson = lessons.get(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leçon introuvable")
    return LessonOut.from_domain(lesson)


@router.get("/quiz-questions", response_model=list[QuizQuestionOut])
def list_quiz_questions(
    level: str | None = Query(default=None, description="Filter by level"),
    category: str | None = Query(default=None, description="Filter by category"),
    _user: User = Depends(get_current_user),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
) -> list[QuizQuestionOut]:
    if level and category:
        items = quizzes.list_by_level_and_category(level, category)
    elif level:
        items = quizzes.list_by_level(level)
    elif category:
        items = [q for q in quizzes.list_all() if q.category == category]
    else:
        items = quizzes.list_all()
    return [QuizQuestionOut.from_domain(x) for x in items]


@router.get("/stories", response_model=list[StoryOut])
def list_stories(
    level: str | None = Query(default=None, description="Filter by level"),
    _user: User = Depends(get_current_user),
    stories: IStoryRepository = Depends(get_story_repo),
) -> list[StoryOut]:
    if level:
        items = stories.list_by_level(level)
    else:
        items = stories.list_all()
    return [StoryOut.from_domain(x) for x in items]


@router.get("/stories/{story_id}", response_model=StoryOut)
def get_story(
    story_id: UUID,
    _user: User = Depends(get_current_user),
    stories: IStoryRepository = Depends(get_story_repo),
) -> StoryOut:
    story = stories.get(story_id)
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Histoire introuvable")
    return StoryOut.from_domain(story)
