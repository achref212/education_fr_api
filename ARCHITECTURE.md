# DELFy API — Architecture & Complete Diagram

> **Version:** 0.2.0 — FastAPI · PostgreSQL · SQLAlchemy 2.0 · Alembic · JWT

---

## Table of Contents

1. [Overview](#1-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Architecture Layers](#4-architecture-layers)
5. [Database Schema](#5-database-schema)
6. [Role & Access Model](#6-role--access-model)
7. [Authentication Flows](#7-authentication-flows)
8. [API Endpoints Reference](#8-api-endpoints-reference)
9. [Email System](#9-email-system)
10. [Domain Entities](#10-domain-entities)
11. [Repository Layer](#11-repository-layer)
12. [Migration History](#12-migration-history)

---

## 1. Overview

DELFy is a **French-language education platform** targeting Tunisian students from grade 2 to grade 9. The API exposes content (lessons, quizzes, stories), a multiplayer room system, progress tracking, and a full institution management layer (schools + professors).

```
┌────────────────────────────────────────────────────────────────┐
│                     CLIENT APPLICATIONS                        │
│                                                                │
│   Flutter App (student)   Admin Panel (web)   School Dashboard │
└────────────┬──────────────────┬──────────────────┬────────────┘
             │  JWT (user)      │  JWT (admin)     │  JWT (school)
             ▼                  ▼                  ▼
┌────────────────────────────────────────────────────────────────┐
│                    DELFy REST API  :8000                       │
│               FastAPI  ·  CORS  ·  Pydantic v2                 │
└────────────────────────┬───────────────────────────────────────┘
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
      PostgreSQL DB          SMTP / Email
    (SQLAlchemy 2.0)      (Gmail / Console)
```

---

## 2. Technology Stack

| Category | Technology |
|---|---|
| Web framework | **FastAPI 0.115** |
| Language | **Python 3.12** |
| ORM | **SQLAlchemy 2.0** (declarative, type-annotated) |
| Database | **PostgreSQL 15** |
| Migrations | **Alembic** |
| Validation | **Pydantic v2** |
| Auth tokens | **python-jose** (HS256 JWT) |
| Password hashing | **passlib / bcrypt** |
| Email | **smtplib** (SMTP + TLS) + HTML templates |
| Testing | **pytest** + in-memory fakes |
| Containerisation | **docker-compose** (PostgreSQL) |

---

## 3. Project Structure

```
education_fr_api/
│
├── alembic/                         # DB migration scripts
│   ├── env.py
│   └── versions/
│       ├── 0001_initial.py
│       ├── 0002_add_role_content_tables.py
│       ├── 0003_add_schools_roles.py
│       └── 0004_add_user_phone_dob.py
│
├── app/
│   │
│   ├── core/                        # Cross-cutting concerns
│   │   ├── config.py                ← Pydantic BaseSettings (.env)
│   │   ├── security.py              ← JWT creation/parsing, bcrypt
│   │   └── email_validation.py      ← DNS + disposable-domain check
│   │
│   ├── domain/                      # ★ Core business rules (no deps)
│   │   ├── entities.py              ← Pure dataclasses
│   │   └── ports.py                 ← Protocol interfaces (repository contracts)
│   │
│   ├── application/                 # ★ Use-case orchestration
│   │   ├── auth_service.py          ← Auth, register, reset, school/prof creation
│   │   └── progress_service.py      ← Get / upsert user progress
│   │
│   ├── infrastructure/              # ★ External concerns
│   │   ├── db/
│   │   │   ├── base.py              ← SQLAlchemy declarative Base
│   │   │   └── session.py           ← Engine, SessionLocal, get_db()
│   │   ├── email/
│   │   │   ├── smtp_email_sender.py ← SmtpEmailSender + ConsoleFallback
│   │   │   └── templates.py         ← HTML email templates
│   │   ├── models/                  ← SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── school.py
│   │   │   ├── recommendation.py
│   │   │   ├── multiplayer_room.py
│   │   │   ├── lesson.py
│   │   │   ├── quiz_question.py
│   │   │   ├── story.py
│   │   │   ├── user_progress.py
│   │   │   └── contact_message.py
│   │   └── repositories/            ← SQL implementations of ports
│   │       ├── sql_user_repository.py
│   │       ├── sql_admin_user_repository.py
│   │       ├── sql_school_repository.py
│   │       ├── sql_recommendation_repository.py
│   │       ├── sql_lesson_repository.py
│   │       ├── sql_quiz_repository.py
│   │       ├── sql_story_repository.py
│   │       ├── sql_progress_repository.py
│   │       ├── sql_admin_progress_repository.py
│   │       ├── sql_multiplayer_repository.py
│   │       └── sql_contact_repository.py
│   │
│   ├── api/                         # ★ HTTP delivery layer
│   │   ├── dependencies.py          ← DI: repos, services, auth guards
│   │   ├── routers/
│   │   │   ├── health.py            GET /health
│   │   │   ├── auth.py              POST /auth/*
│   │   │   ├── progress.py          GET|PUT /progress
│   │   │   ├── content.py           GET /lessons, /quiz-questions, /stories
│   │   │   ├── school.py            GET|POST /school/*
│   │   │   ├── prof.py              GET|POST /prof/*
│   │   │   └── admin.py             GET|POST|PUT|DELETE /admin/*
│   │   └── schemas/
│   │       ├── user.py
│   │       ├── school.py
│   │       ├── admin.py
│   │       ├── recommendation.py
│   │       └── progress.py
│   │
│   └── main.py                      ← FastAPI app + CORS + router registration
│
├── tests/
│   ├── conftest.py
│   ├── test_auth_service.py         ← Unit tests (in-memory fakes, no DB)
│   └── test_health.py
│
├── scripts/
│   └── create_admin.py              ← Bootstrap first admin account
│
├── docker-compose.yml               ← PostgreSQL service
├── requirements.txt
└── .env.example
```

---

## 4. Architecture Layers

The project follows **Clean Architecture** — dependencies always point inward.

```
┌─────────────────────────────────────────────────────────────────┐
│  API LAYER  (app/api/)                                          │
│                                                                 │
│  Routers ──► Pydantic schemas ──► HTTP response                 │
│  dependencies.py  →  auth guards  +  repository injection      │
│                                                                 │
│  Knows about: Application layer, Domain entities, Schemas       │
└───────────────────────────┬─────────────────────────────────────┘
                            │  calls
┌───────────────────────────▼─────────────────────────────────────┐
│  APPLICATION LAYER  (app/application/)                          │
│                                                                 │
│  AuthService          — register, login, reset, school/prof     │
│  ProgressService      — get/upsert progress                     │
│                                                                 │
│  Knows about: Domain ports (interfaces), Domain entities        │
│  Does NOT know about: SQLAlchemy, HTTP, email internals         │
└───────────────────────────┬─────────────────────────────────────┘
                            │  depends on (Protocol)
┌───────────────────────────▼─────────────────────────────────────┐
│  DOMAIN LAYER  (app/domain/)                                    │
│                                                                 │
│  entities.py   — pure Python dataclasses (User, School, …)     │
│  ports.py      — Protocol interfaces  (IUserRepository, …)     │
│                                                                 │
│  Knows about: Python stdlib only.  Zero external dependencies   │
└───────────────────────────┬─────────────────────────────────────┘
                            │  implemented by
┌───────────────────────────▼─────────────────────────────────────┐
│  INFRASTRUCTURE LAYER  (app/infrastructure/)                    │
│                                                                 │
│  ORM models (SQLAlchemy)                                        │
│  SQL repositories  → implement domain ports                     │
│  SmtpEmailSender / ConsoleFallbackEmailSender                   │
│  Database session management (PostgreSQL)                       │
│                                                                 │
│  Knows about: SQLAlchemy, PostgreSQL, SMTP                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Database Schema

### Entity-Relationship Diagram

```
┌──────────────────────┐         ┌──────────────────────────┐
│        users         │         │         schools           │
├──────────────────────┤         ├──────────────────────────┤
│ id              UUID │◄────────┤ created_by_admin_id  UUID│
│ email      VARCHAR   │         │ id              UUID  PK  │
│ password_hash  TEXT  │         │ name            VARCHAR   │
│ first_name  VARCHAR  │         │ email      VARCHAR UNIQUE │
│ last_name   VARCHAR  │         │ password_hash   TEXT      │
│ level       VARCHAR  │         │ address         VARCHAR   │
│ class_level VARCHAR  │         │ city            VARCHAR   │
│ phone       VARCHAR  │         │ postal_code     VARCHAR   │
│ date_of_birth  DATE  │         │ phone           VARCHAR   │
│ role        VARCHAR  │◄───┐    │ director_name   VARCHAR   │
│ is_active   BOOLEAN  │    │    │ is_active       BOOLEAN   │
│ created_at  TIMESTAMPTZ   │    │ created_at   TIMESTAMPTZ  │
│ school_id       UUID ├────┼───►│ id (FK target)            │
│ teacher_school_id UUID├───┘    └──────────────────────────┘
└──────┬───────────────┘                   │
       │                                   │
       │  1:N                              │  1:N
       ▼                                   ▼
┌──────────────────────┐         ┌──────────────────────────┐
│   recommendations    │         │    multiplayer_rooms      │
├──────────────────────┤         ├──────────────────────────┤
│ id            UUID   │         │ id            UUID   PK   │
│ student_id    UUID ──┼─►users  │ room_code  VARCHAR UNIQUE │
│ professor_id  UUID ──┼─►users  │ data          JSONB       │
│ content       TEXT   │         │ label         VARCHAR     │
│ created_at  TIMESTAMPTZ        │ created_at  TIMESTAMPTZ   │
└──────────────────────┘         │ updated_at  TIMESTAMPTZ   │
                                 │ professor_id  UUID ──►users│
                                 │ school_id     UUID ──►schools│
                                 └──────────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│       lessons        │  │    quiz_questions     │  │       stories        │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ id        UUID  PK   │  │ id        UUID  PK   │  │ id        UUID  PK   │
│ title     VARCHAR    │  │ question  TEXT        │  │ title     VARCHAR    │
│ content   TEXT        │  │ options   JSONB       │  │ content   TEXT       │
│ category  VARCHAR    │  │ correct_index INT     │  │ level     VARCHAR    │
│ level     VARCHAR    │  │ explanation TEXT      │  │ audio_url VARCHAR    │
│ sort_order INT       │  │ category  VARCHAR     │  │ created_at TIMESTAMPTZ│
│ created_at TIMESTAMPTZ│  │ level     VARCHAR    │  └──────────────────────┘
└──────────────────────┘  │ created_at TIMESTAMPTZ│
                          └──────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐
│    user_progress     │  │   contact_messages   │
├──────────────────────┤  ├──────────────────────┤
│ user_id   UUID  PK ──┼─►users                  │
│ lessons_completed INT│  │ id        UUID  PK   │
│ quiz_scores   JSONB  │  │ name      VARCHAR    │
│ exercise_scores JSONB│  │ email     VARCHAR    │
│ updated_at TIMESTAMPTZ│  │ subject   VARCHAR   │
└──────────────────────┘  │ message   TEXT       │
                          │ read      BOOLEAN    │
                          │ created_at TIMESTAMPTZ│
                          └──────────────────────┘
```

### Table Summary

| Table | Rows | Key Relations |
|---|---|---|
| `users` | Students, professors, admins | FK → `schools` (school_id, teacher_school_id) |
| `schools` | School institutions | FK → `users` (created_by_admin_id) |
| `recommendations` | Prof → Student notes | FK → `users` (student_id, professor_id) |
| `multiplayer_rooms` | Game sessions | FK → `users`, `schools` |
| `lessons` | Course content | — |
| `quiz_questions` | Quiz content | — |
| `stories` | Reading content | — |
| `user_progress` | Per-user progress | FK → `users` (1:1) |
| `contact_messages` | Contact form | — |

---

## 6. Role & Access Model

```
                         ┌─────────────┐
                         │    ADMIN    │
                         │ role=admin  │
                         └──────┬──────┘
                                │ Full access to all endpoints
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
             Create School  Manage Users  Manage Content
                    │
                    ▼
            ┌─────────────┐
            │   SCHOOL    │  ← Separate JWT namespace (sub=school:{id})
            │ schools table│
            └──────┬──────┘
                   │ Creates professor accounts, views students
                   ▼
            ┌─────────────┐
            │    PROF     │
            │  role=prof  │
            └──────┬──────┘
                   │ Manages their school's students
                   ▼
            ┌─────────────┐
            │   STUDENT   │
            │  role=user  │
            └─────────────┘
              Consumes content, tracks progress
```

### Access Control Summary

| Actor | JWT `sub` | Can access |
|---|---|---|
| **Student** (`role=user`) | UUID | `/auth/*`, `/progress`, `/lessons`, `/quiz-questions`, `/stories` |
| **Professor** (`role=prof`) | UUID | All student endpoints + `/prof/*` |
| **School** | `school:{UUID}` | `/auth/login`, `/auth/me`, `/school/*` |
| **Admin** (`role=admin`) | UUID | All endpoints + `/admin/*` |

### Auth Guard Functions

```python
get_current_user   → User           # any valid user JWT, must be is_active
get_current_school → School         # JWT sub starts with "school:", must be is_active
require_admin      → User           # role == "admin"
require_prof       → User           # role in ("prof", "admin")
require_student    → User           # role in ("user", "admin")
```

---

## 7. Authentication Flows

### 7.1 Student Registration

```
Student                        API                         Email Service
   │                            │                               │
   │── POST /auth/register ─────►│                               │
   │   {email, password,         │── validate email (DNS)        │
   │    firstName, lastName,     │── hash password               │
   │    level, classLevel,       │── create user (is_active=F)   │
   │    phone, dateOfBirth,      │── generate 6-digit code       │
   │    schoolId}                │── store code in state JWT     │
   │                             │──────────────────────────────►│
   │                             │                  send activation email
   │◄── 201 {registration_state_token}
   │
   │── POST /auth/verify-registration
   │   {email, code,             │
   │    registration_state_token}│── decode state JWT
   │                             │── verify bcrypt(code) matches
   │                             │── set is_active = True
   │◄── 200 {access_token, user} │
```

### 7.2 Unified Login

```
Client                  API                  DB (users)    DB (schools)
  │                      │                       │              │
  │── POST /auth/login ──►│                       │              │
  │   {email, password}   │── get_by_email ───────►              │
  │                       │                    found?            │
  │                       │   if not found ──────────────────────►
  │                       │                               found?
  │                       │   verify bcrypt(password)           │
  │                       │                                     │
  │                       │── if school ──────────────────────────
  │                       │   create school JWT (sub=school:{id})│
  │◄── 200 {access_token, role="school", school: SchoolOut}
  │                       │── if user
  │                       │   create user JWT (sub={uuid})
  │◄── 200 {access_token, role, user: UserOut}
```

### 7.3 Password Reset

```
User                        API
  │── POST /auth/forgot-password {email}
  │                            │── generate 6-digit code
  │                            │── send code via email
  │◄── {reset_state_token}     │
  │
  │── POST /auth/verify-reset-code {email, code, reset_state_token}
  │                            │── verify code in state JWT
  │◄── {reset_token}           │   (short-lived, single-use)
  │
  │── POST /auth/reset-password {email, reset_token, newPassword}
  │                            │── validate reset_token (bound to old hash)
  │                            │── update password_hash
  │◄── 200 OK
```

### 7.4 Admin Creates School

```
Admin                       API                     Email Service
  │── POST /admin/schools ──►│
  │   {name, email, …}       │── validate email
  │                          │── generate random password
  │                          │── hash + store in schools table
  │                          │── school.created_by_admin_id = admin.id
  │                          │─────────────────────────────────────────►
  │                          │               send welcome email with credentials
  │◄── 201 {school, plainPassword}
```

### 7.5 School Creates Professor

```
School                      API                     Email Service
  │── POST /school/professors
  │   {email, firstName,     │── validate school JWT
  │    lastName, phone,      │── generate random password
  │    dateOfBirth}          │── create user (role=prof,
  │                          │    teacher_school_id=school.id)
  │                          │─────────────────────────────────────────►
  │                          │               send prof welcome email
  │◄── 201 {userId, plainPassword, phone, dateOfBirth}
```

---

## 8. API Endpoints Reference

**68 endpoints total**

### Health

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/health` | Public | `{"status": "ok"}` |

---

### Auth `/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Register student; sends activation code; returns `registration_state_token` |
| POST | `/auth/verify-registration` | Public | Activate account with 6-digit code |
| POST | `/auth/resend-activation` | Public | Resend activation email |
| POST | `/auth/login` | Public | Unified login → JWT for user or school |
| GET | `/auth/me` | User | Current user profile |
| POST | `/auth/forgot-password` | Public | Send password-reset code |
| POST | `/auth/verify-reset-code` | Public | Validate code → short-lived reset token |
| POST | `/auth/reset-password` | Public | Apply new password |

---

### Progress `/progress`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/progress` | User | Get current user progress |
| PUT | `/progress` | User | Save current user progress |

---

### Content (Student)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/lessons` | User | List lessons — optional `?level=` `?category=` |
| GET | `/lessons/{id}` | User | Get single lesson |
| GET | `/quiz-questions` | User | List quiz questions — optional `?level=` |
| GET | `/stories` | User | List stories — optional `?level=` |
| GET | `/stories/{id}` | User | Get single story |

---

### School `/school`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/school/me` | School | School profile |
| GET | `/school/students` | School | List enrolled students |
| GET | `/school/students/{id}` | School | Student details |
| GET | `/school/students/{id}/progress` | School | Student profile + progress |
| GET | `/school/professors` | School | List linked professors |
| POST | `/school/professors` | School | Create professor (sends credentials email) |

---

### Professor `/prof`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/prof/students` | Prof | List students in professor's school |
| GET | `/prof/students/{id}` | Prof | Get student |
| GET | `/prof/students/{id}/progress` | Prof | Student + progress |
| GET | `/prof/students/{id}/recommendations` | Prof | Recommendations list |
| POST | `/prof/students/{id}/recommendations` | Prof | Add recommendation |
| GET | `/prof/multiplayer-rooms` | Prof | List professor's rooms |
| POST | `/prof/multiplayer-rooms` | Prof | Create room (random hex code) |
| GET | `/prof/lessons` | Prof | List all lessons |
| POST | `/prof/lessons` | Prof | Create a lesson |

---

### Admin `/admin`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/admin/setup` | Public* | Bootstrap first admin account |
| GET | `/admin/stats` | Admin | Dashboard stats |
| GET | `/admin/users` | Admin | List all users |
| POST | `/admin/users` | Admin | Create user with role |
| PUT | `/admin/users/{id}` | Admin | Update user |
| DELETE | `/admin/users/{id}` | Admin | Delete user |
| GET | `/admin/lessons` | Admin | List lessons |
| POST | `/admin/lessons` | Admin | Create lesson |
| PUT | `/admin/lessons/{id}` | Admin | Update lesson |
| DELETE | `/admin/lessons/{id}` | Admin | Delete lesson |
| GET | `/admin/quiz-questions` | Admin | List quiz questions |
| POST | `/admin/quiz-questions` | Admin | Create quiz question |
| PUT | `/admin/quiz-questions/{id}` | Admin | Update quiz question |
| DELETE | `/admin/quiz-questions/{id}` | Admin | Delete quiz question |
| GET | `/admin/stories` | Admin | List stories |
| POST | `/admin/stories` | Admin | Create story |
| PUT | `/admin/stories/{id}` | Admin | Update story |
| DELETE | `/admin/stories/{id}` | Admin | Delete story |
| GET | `/admin/contact-messages` | Admin | List contact messages |
| PUT | `/admin/contact-messages/{id}` | Admin | Mark read/unread |
| DELETE | `/admin/contact-messages/{id}` | Admin | Delete message |
| GET | `/admin/progress` | Admin | All users + progress |
| GET | `/admin/multiplayer-rooms` | Admin | All multiplayer rooms |
| GET | `/admin/schools` | Admin | List schools |
| POST | `/admin/schools` | Admin | Create school (sends credentials email) |
| GET | `/admin/schools/{id}` | Admin | Get school |
| PUT | `/admin/schools/{id}` | Admin | Update school |
| DELETE | `/admin/schools/{id}` | Admin | Delete school |
| GET | `/admin/schools/{id}/students` | Admin | School's students |
| GET | `/admin/schools/{id}/professors` | Admin | School's professors |

\*`/admin/setup` guarded by "no admins exist yet" — no JWT needed.

---

## 9. Email System

```
IEmailSender (port)
       │
       ├── SmtpEmailSender          ← used when SMTP_HOST + credentials set
       │     Gmail / any SMTP server (TLS port 587 or SSL 465)
       │
       └── ConsoleFallbackEmailSender  ← used in development (logs to console)
```

### Email Types

| Trigger | Template function | Recipients |
|---|---|---|
| Student registration | `build_activation_email_html` | Student |
| Password reset | `build_password_reset_email_html` | Student |
| School created by admin | `build_school_welcome_email_html` | School email |
| Professor created by school | `build_prof_welcome_email_html` | Professor email |

All templates are HTML with a plain-text fallback, sent as `multipart/alternative`.

---

## 10. Domain Entities

```python
@dataclass
class User:
    id: UUID
    email: str
    first_name: str
    last_name: str
    level: str                     # e.g. "5eme"
    created_at: datetime
    role: str                      # "user" | "prof" | "admin"
    is_active: bool
    class_level: str | None        # "2ème année" … "9ème année"
    school_id: UUID | None         # enrolled school (students)
    teacher_school_id: UUID | None # affiliated school (profs)
    phone: str | None
    date_of_birth: date | None

@dataclass
class School:
    id: UUID
    name: str
    email: str
    is_active: bool
    created_at: datetime
    address: str | None
    city: str | None
    postal_code: str | None
    phone: str | None
    director_name: str | None
    created_by_admin_id: UUID | None

@dataclass
class Recommendation:
    id: UUID
    student_id: UUID
    content: str
    created_at: datetime
    professor_id: UUID | None

@dataclass
class Lesson:
    id: UUID;  title: str;  content: str
    category: str;  level: str;  sort_order: int;  created_at: datetime

@dataclass
class QuizQuestion:
    id: UUID;  question: str;  options: list[str]
    correct_index: int;  explanation: str;  category: str
    level: str;  created_at: datetime

@dataclass
class Story:
    id: UUID;  title: str;  content: str
    level: str;  audio_url: str | None;  created_at: datetime

@dataclass
class ProgressData:
    lessons_completed: int
    quiz_scores: dict[str, Any]
    exercise_scores: dict[str, Any]

@dataclass
class MultiplayerRoom:
    id: UUID;  room_code: str;  data: dict
    label: str;  created_at: datetime;  updated_at: datetime
    professor_id: UUID | None;  school_id: UUID | None
```

---

## 11. Repository Layer

Each SQL repository implements a domain `Protocol` and is injected via FastAPI `Depends()`.

```
Domain Port                  SQL Implementation
─────────────────────────    ────────────────────────────────────────
IUserRepository          →   SqlUserRepository
IAdminUserRepository     →   SqlAdminUserRepository
ISchoolRepository        →   SqlSchoolRepository
IRecommendationRepository→   SqlRecommendationRepository
IProgressRepository      →   SqlProgressRepository
IAdminProgressRepository →   SqlAdminProgressRepository
ILessonRepository        →   SqlLessonRepository
IQuizRepository          →   SqlQuizRepository
IStoryRepository         →   SqlStoryRepository
IContactRepository       →   SqlContactRepository
IMultiplayerRepository   →   SqlMultiplayerRepository
IEmailSender             →   SmtpEmailSender | ConsoleFallbackEmailSender
```

All repositories receive a `Session` injected by `get_db()` (SQLAlchemy `SessionLocal`). The HTTP request owns the session lifecycle — `db.commit()` is called at the router level after successful operations.

---

## 12. Migration History

| # | File | Changes |
|---|---|---|
| `0001` | `20250224_initial` | Create `users`, `user_progress` |
| `0002` | `20250423_add_role_content_tables` | Add `role`, `is_active` to `users`; create `lessons`, `quiz_questions`, `stories`, `contact_messages`, `multiplayer_rooms` |
| `0003` | `20260702_add_schools_roles` | Create `schools`, `recommendations`; add `class_level`, `school_id`, `teacher_school_id` to `users`; add `professor_id`, `school_id` to `multiplayer_rooms` |
| `0004` | `20260702_add_user_phone_dob` | Add `phone`, `date_of_birth` to `users` |

Run all pending migrations:
```bash
alembic upgrade head
```

---

## Environment Variables (`.env`)

```env
DATABASE_URL=postgresql://user:password@localhost:5432/education_fr

SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

CORS_ORIGINS=http://localhost:3000,https://admin.delfy.app

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=app-password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=no-reply@delfy.app
SMTP_FROM_NAME=DELFy

PASSWORD_RESET_CODE_EXPIRE_MINUTES=15
DASHBOARD_URL=https://dashboard.delfy.app
```

---

## Quick Start

```bash
# 1. Install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Start PostgreSQL
docker-compose up -d

# 3. Apply migrations
alembic upgrade head

# 4. Create first admin
python scripts/create_admin.py

# 5. Run the API
uvicorn app.main:app --reload --port 8000

# 6. Interactive docs
open http://localhost:8000/docs
```

---

*Generated for DELFy API v0.2.0 — Thursday 2 July 2026*
