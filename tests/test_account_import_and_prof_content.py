from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from openpyxl import Workbook

from app.api.dependencies import (
    get_auth_service,
    get_current_school,
    get_current_user,
    get_quiz_repo,
    get_story_repo,
    require_admin,
    require_prof,
)
from app.api.routers.admin import get_db as admin_get_db
from app.api.routers.school import get_db as school_get_db
from app.application.auth_service import AuthError
from app.application.import_service import parse_import_file
from app.domain.entities import QuizQuestion, School, Story, User
from app.main import app


class FakeUpload:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


class FakeDb:
    commits = 0
    rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeAuth:
    def create_school_account(self, **kwargs):
        if "taken" in kwargs["email"]:
            raise AuthError("email_taken", "Cet e-mail est déjà utilisé")
        school = School(
            id=uuid4(),
            name=kwargs["name"],
            email=kwargs["email"],
            is_active=True,
            must_change_password=True,
            created_at=datetime.now(timezone.utc),
        )
        return school, "SchoolPwd1"

    def create_prof_account(self, **kwargs):
        if "taken" in kwargs["email"]:
            raise AuthError("email_taken", "Cet e-mail est déjà utilisé")
        prof = User(
            id=uuid4(),
            email=kwargs["email"],
            first_name=kwargs["first_name"],
            last_name=kwargs["last_name"],
            level="prof",
            role="prof",
            created_at=datetime.now(timezone.utc),
            teacher_school_id=kwargs["teacher_school_id"],
        )
        return prof, "ProfPwd1"


@dataclass
class FakeQuizRepo:
    questions: dict[UUID, QuizQuestion] = field(default_factory=dict)

    def list_by_professor(self, professor_id: UUID) -> list[QuizQuestion]:
        return [q for q in self.questions.values() if q.professor_id == professor_id]

    def list_visible_for_user(self, user: User) -> list[QuizQuestion]:
        return [
            q
            for q in self.questions.values()
            if q.visibility == "public" or q.school_id == user.school_id
        ]

    def get(self, question_id: UUID) -> QuizQuestion | None:
        return self.questions.get(question_id)

    def create(self, **kwargs) -> QuizQuestion:
        question = QuizQuestion(id=uuid4(), **kwargs)
        self.questions[question.id] = question
        return question

    def update(self, question_id: UUID, **kwargs) -> QuizQuestion | None:
        question = self.questions.get(question_id)
        if question is None:
            return None
        for key, value in kwargs.items():
            if value is not None:
                attr = {"correct_index": "correct_index"}.get(key, key)
                setattr(question, attr, value)
        return question

    def delete(self, question_id: UUID) -> bool:
        return self.questions.pop(question_id, None) is not None


@dataclass
class FakeStoryRepo:
    stories: dict[UUID, Story] = field(default_factory=dict)

    def list_by_professor(self, professor_id: UUID) -> list[Story]:
        return [s for s in self.stories.values() if s.professor_id == professor_id]

    def get(self, story_id: UUID) -> Story | None:
        return self.stories.get(story_id)

    def create(self, **kwargs) -> Story:
        story = Story(id=uuid4(), created_at=datetime.now(timezone.utc), **kwargs)
        self.stories[story.id] = story
        return story

    def update(self, story_id: UUID, **kwargs) -> Story | None:
        story = self.stories.get(story_id)
        if story is None:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(story, key, value)
        return story

    def delete(self, story_id: UUID) -> bool:
        return self.stories.pop(story_id, None) is not None


def _admin() -> User:
    return User(
        id=uuid4(),
        email="admin@test.fr",
        first_name="Admin",
        last_name="User",
        level="avance",
        role="admin",
        created_at=datetime.now(timezone.utc),
    )


def _school() -> School:
    return School(
        id=uuid4(),
        name="École Test",
        email="school@test.fr",
        is_active=True,
        must_change_password=False,
        created_at=datetime.now(timezone.utc),
    )


def _prof(school_id: UUID, professor_id: UUID | None = None) -> User:
    return User(
        id=professor_id or uuid4(),
        email="prof@test.fr",
        first_name="Prof",
        last_name="User",
        level="prof",
        role="prof",
        created_at=datetime.now(timezone.utc),
        teacher_school_id=school_id,
    )


def _student(school_id: UUID) -> User:
    return User(
        id=uuid4(),
        email="student@test.fr",
        first_name="Student",
        last_name="User",
        level="debutant",
        role="user",
        created_at=datetime.now(timezone.utc),
        school_id=school_id,
    )


@pytest.mark.anyio
async def test_import_parser_reads_csv_and_xlsx_rows() -> None:
    csv_content = "Nom,Email,Ville\nÉcole A,ecole-a@test.fr,Paris\n".encode()
    csv_rows = await parse_import_file(FakeUpload("schools.csv", csv_content), kind="schools")
    assert csv_rows[0].values["name"] == "École A"
    assert csv_rows[0].values["city"] == "Paris"

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Prénom", "Nom", "Email"])
    sheet.append(["Marie", "Dupont", "marie@test.fr"])
    output = BytesIO()
    workbook.save(output)

    xlsx_rows = await parse_import_file(FakeUpload("professeurs.xlsx", output.getvalue()), kind="professors")
    assert xlsx_rows[0].values["firstName"] == "Marie"
    assert xlsx_rows[0].values["lastName"] == "Dupont"


@pytest.mark.anyio
async def test_admin_school_import_partially_creates_valid_rows(client) -> None:
    fake_db = FakeDb()
    app.dependency_overrides[require_admin] = _admin
    app.dependency_overrides[get_auth_service] = lambda: FakeAuth()
    app.dependency_overrides[admin_get_db] = lambda: fake_db
    try:
        response = await client.post(
            "/admin/schools/import",
            files={
                "file": (
                    "schools.csv",
                    "Nom,Email\nÉcole A,ecole-a@test.fr\nÉcole B,taken@test.fr\n,email-missing-name@test.fr\n",
                    "text/csv",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["createdCount"] == 1
    assert data["skippedCount"] == 2
    assert data["results"][0]["plainPassword"] == "SchoolPwd1"
    assert fake_db.commits == 1
    assert fake_db.rollbacks == 1


@pytest.mark.anyio
async def test_school_professor_import_partially_creates_valid_rows(client) -> None:
    fake_db = FakeDb()
    school = _school()
    app.dependency_overrides[get_current_school] = lambda: school
    app.dependency_overrides[get_auth_service] = lambda: FakeAuth()
    app.dependency_overrides[school_get_db] = lambda: fake_db
    try:
        response = await client.post(
            "/school/professors/import",
            files={
                "file": (
                    "profs.csv",
                    "Prénom,Nom,Email\nMarie,Dupont,marie@test.fr\nJean,Martin,taken@test.fr\n",
                    "text/csv",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["createdCount"] == 1
    assert data["skippedCount"] == 1
    assert data["results"][0]["plainPassword"] == "ProfPwd1"
    assert fake_db.commits == 1
    assert fake_db.rollbacks == 1


@pytest.mark.anyio
async def test_professor_quiz_permissions_and_school_private_content_visibility(client) -> None:
    school_id = uuid4()
    other_school_id = uuid4()
    owner_id = uuid4()
    repo = FakeQuizRepo()
    owner = _prof(school_id, owner_id)
    other_prof = _prof(school_id)
    app.dependency_overrides[require_prof] = lambda: owner
    app.dependency_overrides[get_quiz_repo] = lambda: repo
    app.dependency_overrides[admin_get_db] = lambda: FakeDb()
    try:
        created = await client.post(
            "/prof/quiz-questions",
            json={
                "question": "Quelle phrase est correcte ?",
                "options": ["Je suis prêt.", "Je être prêt."],
                "correctIndex": 0,
                "explanation": "Avec je, on utilise suis.",
                "category": "Grammaire",
                "level": "3ème année",
                "visibility": "school",
            },
        )
        app.dependency_overrides[require_prof] = lambda: other_prof
        denied = await client.put(
            f"/prof/quiz-questions/{created.json()['id']}",
            json={"question": "Modification interdite"},
        )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["visibility"] == "school"
    assert denied.status_code == 404

    app.dependency_overrides[get_quiz_repo] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: _student(school_id)
    try:
        same_school = await client.get("/quiz-questions")
        app.dependency_overrides[get_current_user] = lambda: _student(other_school_id)
        other_school = await client.get("/quiz-questions")
    finally:
        app.dependency_overrides.clear()

    assert len(same_school.json()) == 1
    assert other_school.json() == []


@pytest.mark.anyio
async def test_professor_story_permissions(client) -> None:
    school_id = uuid4()
    owner_id = uuid4()
    repo = FakeStoryRepo()
    app.dependency_overrides[require_prof] = lambda: _prof(school_id, owner_id)
    app.dependency_overrides[get_story_repo] = lambda: repo
    app.dependency_overrides[admin_get_db] = lambda: FakeDb()
    try:
        created = await client.post(
            "/prof/stories",
            json={
                "title": "Lecture courte",
                "content": "Lina lit une phrase simple.",
                "level": "3ème année",
                "audioUrl": None,
                "visibility": "school",
            },
        )
        app.dependency_overrides[require_prof] = lambda: _prof(school_id)
        denied = await client.delete(f"/prof/stories/{created.json()['id']}")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["visibility"] == "school"
    assert denied.status_code == 404
