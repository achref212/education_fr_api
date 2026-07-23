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
    user: User = Depends(get_current_user),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> list[LessonOut]:
    visible = lessons.list_visible_for_user(user)
    if level:
        items = [item for item in visible if item.level == level]
    elif category:
        items = [item for item in visible if item.category == category]
    else:
        items = visible
    return [LessonOut.from_domain(x) for x in items]


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(
    lesson_id: UUID,
    user: User = Depends(get_current_user),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> LessonOut:
    lesson = lessons.get(lesson_id)
    visible_ids = {item.id for item in lessons.list_visible_for_user(user)}
    if lesson is None or lesson.id not in visible_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leçon introuvable")
    return LessonOut.from_domain(lesson)


@router.get("/quiz-questions", response_model=list[QuizQuestionOut])
def list_quiz_questions(
    level: str | None = Query(default=None, description="Filter by level"),
    category: str | None = Query(default=None, description="Filter by category"),
    user: User = Depends(get_current_user),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
) -> list[QuizQuestionOut]:
    visible = quizzes.list_visible_for_user(user)
    if level and category:
        items = [q for q in visible if q.level == level and q.category == category]
    elif level:
        items = [q for q in visible if q.level == level]
    elif category:
        items = [q for q in visible if q.category == category]
    else:
        items = visible
    return [QuizQuestionOut.from_domain(x) for x in items]


@router.get("/stories", response_model=list[StoryOut])
def list_stories(
    level: str | None = Query(default=None, description="Filter by level"),
    user: User = Depends(get_current_user),
    stories: IStoryRepository = Depends(get_story_repo),
) -> list[StoryOut]:
    visible = stories.list_visible_for_user(user)
    if level:
        items = [story for story in visible if story.level == level]
    else:
        items = visible
    return [StoryOut.from_domain(x) for x in items]


@router.get("/stories/{story_id}", response_model=StoryOut)
def get_story(
    story_id: UUID,
    user: User = Depends(get_current_user),
    stories: IStoryRepository = Depends(get_story_repo),
) -> StoryOut:
    story = stories.get(story_id)
    visible_ids = {item.id for item in stories.list_visible_for_user(user)}
    if story is None or story.id not in visible_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Histoire introuvable")
    return StoryOut.from_domain(story)
