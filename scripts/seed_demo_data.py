#!/usr/bin/env python3
"""Seed complete demo data across all tables for the admin dashboard.

Idempotent: safe to run multiple times — only fills missing data.

Usage:
  cd education_fr_api
  python3 scripts/seed_demo_data.py
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, text

from app.core.security import hash_password
from app.domain.constants import (
    CLASS_LEVELS,
    DELF_TARGETS_BY_CLASS,
    LESSON_CATEGORIES,
    QUIZ_CATEGORIES,
)
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.models.contact_message import ContactMessageORM
from app.infrastructure.models.delf_test import DelfTestSessionORM
from app.infrastructure.models.game import GameORM
from app.infrastructure.models.game_participant import GameParticipantORM
from app.infrastructure.models.game_session import GameSessionORM
from app.infrastructure.models.learning_path import LearningPathORM
from app.infrastructure.models.learning_path_step import LearningPathStepORM
from app.infrastructure.models.lesson import LessonORM
from app.infrastructure.models.multiplayer_room import MultiplayerRoomORM
from app.infrastructure.models.quiz_question import QuizQuestionORM
from app.infrastructure.models.recommendation import RecommendationORM
from app.infrastructure.models.school import SchoolORM
from app.infrastructure.models.story import StoryORM
from app.infrastructure.models.student_stats import StudentStatsORM
from app.infrastructure.models.student_step_progress import StudentStepProgressORM
from app.infrastructure.models.user import UserORM
from app.infrastructure.models.user_progress import UserProgressORM

DEMO_PASSWORD = "Demo2024!"

LESSON_SNIPPETS: dict[str, tuple[str, str]] = {
    "Grammaire": (
        "Les articles définis",
        "Les articles **le**, **la**, **les** et **l'** servent à désigner quelque chose "
        "de précis.\n\n- *Le* chat dort.\n- *La* maison est grande.\n- *Les* enfants jouent.\n\n"
        "Exercice : complétez avec le bon article — ___ école, ___ arbre, ___ fleurs.",
    ),
    "Conjugaison": (
        "Le présent de l'indicatif",
        "Au présent, les verbes du 1er groupe se terminent en **-e**, **-es**, **-e**, "
        "**-ons**, **-ez**, **-ent**.\n\nExemple avec *chanter* : je chante, tu chantes, "
        "il chante, nous chantons, vous chantez, ils chantent.\n\n"
        "Retenez : la terminaison **-ent** ne se prononce pas pour il/elle/on.",
    ),
    "Orthographe": (
        "Les homophones a / à",
        "**A** (sans accent) est un verbe : *Il a un vélo.*\n"
        "**À** (avec accent) est une préposition : *Je vais à l'école.*\n\n"
        "Astuce : remplacez par *avait* — si ça marche, c'est **a**.",
    ),
    "Vocabulaire": (
        "Les synonymes",
        "Un **synonyme** est un mot de sens proche.\n\n"
        "- grand → immense, énorme\n- content → heureux, joyeux\n- rapidement → vite\n\n"
        "Enrichir son vocabulaire aide à mieux s'exprimer à l'oral et à l'écrit.",
    ),
    "Lecture": (
        "Comprendre un texte court",
        "Pour bien lire :\n1. Lisez le titre et regardez les images.\n"
        "2. Repérez les personnages et le lieu.\n3. Relisez les phrases difficiles.\n"
        "4. Répondez : *Qui ? Quoi ? Où ? Quand ?*",
    ),
    "Dictée": (
        "Les accents et la cédille",
        "L'accent **é** ouvre le *e* : *été, café*.\n"
        "L'accent **è** ferme le *e* : *père, frère*.\n"
        "La **cédille** sous le *c* donne le son [s] devant *a, o, u* : *garçon, leçon*.",
    ),
}

STORY_BY_LEVEL: dict[str, tuple[str, str]] = {
    "2ème année": (
        "Le petit chat curieux",
        "Mimi est un petit chat orange. Chaque matin, elle regarde par la fenêtre. "
        "Un jour, elle voit un papillon bleu dans le jardin. Mimi sort doucement. "
        "Le papillon vole haut, haut, haut ! Mimi saute, mais le papillon s'envole. "
        "Mimi rentre à la maison. Sa maman lui donne du lait chaud. "
        "Mimi est contente. Fin.",
    ),
    "3ème année": (
        "La rentrée de Sami",
        "Sami prépare son cartable : cahiers, stylos, gomme. Il met aussi une pomme "
        "dans sa boîte à goûter. Dans la cour, il retrouve Léa et Karim. "
        "La maîtresse accueille la classe avec un grand sourire. "
        "« Bonjour les enfants ! » dit-elle. Sami est un peu timide, "
        "mais Léa lui prend la main. La journée commence bien.",
    ),
    "4ème année": (
        "Le trésor du jardin",
        "Sous un vieux chêne, Tom et Inès creusent avec une petite pelle. "
        "Soudain, la pelle touche une boîte en métal. À l'intérieur : "
        "des photos en noir et blanc et une lettre datée de 1952. "
        "Ils montrent leur découverte à grand-père, qui reconnaît sa propre école ! "
        "Le trésor n'était pas de l'or, mais une belle histoire de famille.",
    ),
    "5ème année": (
        "Le match décisif",
        "L'équipe de l'école Delacroix joue la finale de handball. "
        "À la mi-temps, le score est de 8 à 8. L'entraîneur encourage les joueurs : "
        "« Restez concentrés, jouez en équipe ! » En fin de match, Amina marque le but "
        "de la victoire. Toute la tribune applaudit. Les camarades portent Amina "
        "en héros. C'était un après-midi inoubliable.",
    ),
    "6ème année": (
        "Voyage en train",
        "Clara et son frère Hugo prennent le TGV pour aller chez leur tante à Lyon. "
        "Par la fenêtre, ils voient défiler les champs, les rivières et les villages. "
        "Hugo lit un roman policier pendant que Clara écoute de la musique. "
        "À l'arrivée, leur tante les attend avec des croissants chauds. "
        "« Bienvenue ! » dit-elle en français et en italien.",
    ),
    "7ème année": (
        "Le débat en classe",
        "Le professeur propose un débat : « Faut-il interdire les téléphones à l'école ? » "
        "Deux groupes préparent leurs arguments. Emma défend l'interdiction : "
        "« Les téléphones distraient et empêchent de travailler. » "
        "Youssef répond : « Ils peuvent servir à chercher des informations utiles. » "
        "Après vingt minutes, la classe vote. Résultat : 18 pour, 12 contre.",
    ),
    "8ème année": (
        "La nuit des étoiles",
        "L'association astronomique organise une soirée au collège. "
        "Avec un télescope, les élèves observent Jupiter et ses lunes. "
        "Leur professeur explique la différence entre une étoile et une planète. "
        "Plus tard, ils dessinent la carte du ciel. Une élève murmure : "
        "« La science rend le monde plus grand. » Tout le monde approuve en silence.",
    ),
    "9ème année": (
        "Lettre à mon futur moi",
        "Dans le cadre du projet de fin d'année, chaque élève écrit une lettre "
        "qu'il ouvrira dans cinq ans. Nadia y parle de ses rêves : étudier les langues, "
        "voyager, aider les autres. Elle scelle l'enveloppe et la confie au professeur. "
        "« Un jour, vous relirez ces mots et vous sourirez », dit-il. "
        "Nadia espère qu'elle aura tenu ses promesses.",
    ),
}

DEMO_SCHOOL = {
    "name": "Collège Lumière — Démo",
    "email": "demo.ecole@delfy.fr",
    "address": "12 avenue de la République",
    "city": "Paris",
    "postal_code": "75011",
    "phone": "+33 1 42 00 00 00",
    "director_name": "Marie Dubois",
}

DEMO_PROFESSORS = [
    {
        "email": "prof.martin@delfy.fr",
        "first_name": "Pierre",
        "last_name": "Martin",
    },
    {
        "email": "prof.bernard@delfy.fr",
        "first_name": "Sophie",
        "last_name": "Bernard",
    },
]

DEMO_STUDENTS = [
    ("demo.student1@delfy.fr", "Lucas", "Moreau", "5ème année", "debutant"),
    ("demo.student2@delfy.fr", "Emma", "Petit", "5ème année", "intermediaire"),
    ("demo.student3@delfy.fr", "Youssef", "Benali", "7ème année", "debutant"),
    ("demo.student4@delfy.fr", "Chloé", "Roux", "7ème année", "avance"),
    ("demo.student5@delfy.fr", "Inès", "Garcia", "9ème année", "intermediaire"),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _pwd() -> str:
    return hash_password(DEMO_PASSWORD)


def seed_lessons(session) -> int:
    created = 0
    now = _now()
    for class_level in CLASS_LEVELS:
        for sort_idx, category in enumerate(LESSON_CATEGORIES, start=1):
            exists = session.scalar(
                select(LessonORM.id)
                .where(
                    LessonORM.level == class_level,
                    LessonORM.category == category,
                )
                .limit(1)
            )
            if exists is not None:
                continue
            title_base, content_base = LESSON_SNIPPETS[category]
            session.add(
                LessonORM(
                    title=f"{title_base} — {class_level}",
                    content=f"# {title_base}\n\nNiveau : {class_level}\n\n{content_base}",
                    category=category,
                    level=class_level,
                    sort_order=sort_idx,
                    created_at=now,
                )
            )
            created += 1
    if created:
        print(f"Lessons: {created} created.")
    else:
        print("Lessons: already complete, skipping.")
    return created


def seed_stories(session) -> int:
    created = 0
    now = _now()
    for class_level in CLASS_LEVELS:
        exists = session.scalar(
            select(StoryORM.id).where(StoryORM.level == class_level).limit(1)
        )
        if exists is not None:
            continue
        title, content = STORY_BY_LEVEL[class_level]
        session.add(
            StoryORM(
                title=f"{title} ({class_level})",
                content=content,
                level=class_level,
                created_at=now,
            )
        )
        created += 1
    if created:
        print(f"Stories: {created} created.")
    else:
        print("Stories: already complete, skipping.")
    return created


def seed_games(session) -> None:
    existing = session.scalar(select(GameORM).limit(1))
    if existing is not None:
        print("Games: already seeded, skipping.")
        return
    now = _now()
    session.add_all(
        [
            GameORM(
                slug="quiz_duel",
                name="Quiz Duel",
                description="Défiez vos amis avec des questions DELF",
                min_players=2,
                max_players=8,
                default_question_count=10,
                is_active=True,
                created_at=now,
            ),
            GameORM(
                slug="friend_challenge",
                name="Défi entre amis",
                description="Apprenez le français en jouant avec vos camarades",
                min_players=2,
                max_players=4,
                default_question_count=8,
                is_active=True,
                created_at=now,
            ),
        ]
    )
    print("Games: 2 created.")


def seed_learning_paths(session) -> None:
    existing = session.scalar(select(LearningPathORM).limit(1))
    if existing is not None:
        print("Learning paths: already seeded, skipping.")
        return
    now = _now()
    for class_level in CLASS_LEVELS:
        path = LearningPathORM(
            class_level=class_level,
            title=f"Parcours DELF — {class_level}",
            description=f"Parcours d'apprentissage du français pour la {class_level}",
            delf_target_level=DELF_TARGETS_BY_CLASS[class_level],
            is_active=True,
            created_at=now,
        )
        session.add(path)
        session.flush()
        previous_step_id: uuid.UUID | None = None
        step_order = 1
        for category in LESSON_CATEGORIES:
            lesson = session.scalar(
                select(LessonORM)
                .where(
                    LessonORM.level == class_level,
                    LessonORM.category == category,
                )
                .order_by(LessonORM.sort_order)
                .limit(1)
            )
            if lesson is not None:
                lesson_step = LearningPathStepORM(
                    path_id=path.id,
                    step_order=step_order,
                    step_type="lesson",
                    title=f"Leçon — {category}",
                    xp_reward=10,
                    lesson_id=lesson.id,
                    required_step_id=previous_step_id,
                    created_at=now,
                )
                session.add(lesson_step)
                session.flush()
                previous_step_id = lesson_step.id
                step_order += 1
            if category in QUIZ_CATEGORIES:
                quiz_step = LearningPathStepORM(
                    path_id=path.id,
                    step_order=step_order,
                    step_type="quiz",
                    title=f"Quiz — {category}",
                    xp_reward=15,
                    quiz_category=category,
                    required_step_id=previous_step_id,
                    created_at=now,
                )
                session.add(quiz_step)
                session.flush()
                previous_step_id = quiz_step.id
                step_order += 1
        story = session.scalar(
            select(StoryORM).where(StoryORM.level == class_level).limit(1)
        )
        if story is not None:
            story_step = LearningPathStepORM(
                path_id=path.id,
                step_order=step_order,
                step_type="story",
                title=f"Histoire — {class_level}",
                xp_reward=20,
                story_id=story.id,
                required_step_id=previous_step_id,
                created_at=now,
            )
            session.add(story_step)
        print(f"Learning path: {class_level} seeded.")


def _get_admin(session) -> UserORM | None:
    return session.scalar(
        select(UserORM).where(UserORM.role == "admin").order_by(UserORM.created_at).limit(1)
    )


def seed_demo_school_and_users(session) -> tuple[SchoolORM | None, list[UserORM]]:
    school = session.scalar(
        select(SchoolORM).where(SchoolORM.email == DEMO_SCHOOL["email"]).limit(1)
    )
    admin = _get_admin(session)
    now = _now()
    if school is None:
        school = SchoolORM(
            name=DEMO_SCHOOL["name"],
            address=DEMO_SCHOOL["address"],
            city=DEMO_SCHOOL["city"],
            postal_code=DEMO_SCHOOL["postal_code"],
            phone=DEMO_SCHOOL["phone"],
            email=DEMO_SCHOOL["email"],
            password_hash=_pwd(),
            director_name=DEMO_SCHOOL["director_name"],
            must_change_password=False,
            is_active=True,
            created_at=now,
            created_by_admin_id=admin.id if admin else None,
        )
        session.add(school)
        session.flush()
        print(f"School: created {DEMO_SCHOOL['email']}")
    else:
        print("School: demo school already exists.")
    professors: list[UserORM] = []
    for prof_data in DEMO_PROFESSORS:
        prof = session.scalar(
            select(UserORM).where(UserORM.email == prof_data["email"]).limit(1)
        )
        if prof is None:
            prof = UserORM(
                email=prof_data["email"],
                password_hash=_pwd(),
                first_name=prof_data["first_name"],
                last_name=prof_data["last_name"],
                level="intermediaire",
                role="prof",
                teacher_school_id=school.id,
                is_active=True,
                must_change_password=False,
                created_at=now,
            )
            session.add(prof)
            session.flush()
            print(f"Professor: created {prof_data['email']}")
        elif prof.teacher_school_id is None:
            prof.teacher_school_id = school.id
        professors.append(prof)
    students: list[UserORM] = []
    for email, first_name, last_name, class_level, skill in DEMO_STUDENTS:
        student = session.scalar(select(UserORM).where(UserORM.email == email).limit(1))
        if student is None:
            student = UserORM(
                email=email,
                password_hash=_pwd(),
                first_name=first_name,
                last_name=last_name,
                level=skill,
                class_level=class_level,
                role="user",
                school_id=school.id,
                phone="+33 6 00 00 00 01",
                date_of_birth=date(2012, 3, 15),
                is_active=True,
                must_change_password=False,
                created_at=now,
            )
            session.add(student)
            session.flush()
            print(f"Student: created {email}")
        students.append(student)
    return school, students


def seed_user_progress(session, students: list[UserORM]) -> None:
    created = 0
    for student in students:
        exists = session.get(UserProgressORM, student.id)
        if exists is not None:
            continue
        class_level = student.class_level or "5ème année"
        session.add(
            UserProgressORM(
                user_id=student.id,
                data={
                    "lessonsCompleted": [
                        f"lesson-demo-{class_level}-1",
                        f"lesson-demo-{class_level}-2",
                    ],
                    "quizScores": {
                        "Grammaire": [72, 85, 90],
                        "Conjugaison": [68, 78],
                        "Vocabulaire": [88],
                    },
                    "exerciseScores": {
                        "Orthographe": [75, 80],
                    },
                },
            )
        )
        created += 1
    if created:
        print(f"User progress: {created} records created.")
    else:
        print("User progress: already seeded, skipping.")


def seed_student_stats(session, students: list[UserORM]) -> None:
    created = 0
    now = _now()
    xp_values = [120, 340, 560, 890, 150]
    for idx, student in enumerate(students):
        exists = session.get(StudentStatsORM, student.id)
        if exists is not None:
            continue
        session.add(
            StudentStatsORM(
                user_id=student.id,
                total_xp=xp_values[idx % len(xp_values)],
                current_streak=3 + idx,
                longest_streak=7 + idx,
                last_activity_date=date.today() - timedelta(days=idx),
                preferred_difficulty="medium" if idx % 2 == 0 else "easy",
                updated_at=now,
            )
        )
        created += 1
    if created:
        print(f"Student stats: {created} records created.")
    else:
        print("Student stats: already seeded, skipping.")


def seed_step_progress(session, students: list[UserORM]) -> None:
    if not students:
        return
    created = 0
    now = _now()
    student = students[0]
    class_level = student.class_level or "5ème année"
    path = session.scalar(
        select(LearningPathORM).where(LearningPathORM.class_level == class_level).limit(1)
    )
    if path is None:
        print("Step progress: no learning path found, skipping.")
        return
    steps = session.scalars(
        select(LearningPathStepORM)
        .where(LearningPathStepORM.path_id == path.id)
        .order_by(LearningPathStepORM.step_order)
    ).all()
    statuses = ["completed", "completed", "in_progress", "available", "locked"]
    for idx, step in enumerate(steps[:5]):
        exists = session.scalar(
            select(StudentStepProgressORM.id)
            .where(
                StudentStepProgressORM.user_id == student.id,
                StudentStepProgressORM.step_id == step.id,
            )
            .limit(1)
        )
        if exists is not None:
            continue
        status = statuses[idx] if idx < len(statuses) else "locked"
        session.add(
            StudentStepProgressORM(
                user_id=student.id,
                step_id=step.id,
                status=status,
                score=85 if status == "completed" else None,
                attempts=1 if status in ("completed", "in_progress") else 0,
                completed_at=now if status == "completed" else None,
                updated_at=now,
            )
        )
        created += 1
    if created:
        print(f"Step progress: {created} records created for {student.email}.")
    else:
        print("Step progress: already seeded, skipping.")


def _sample_question_ids(
    session, class_level: str, per_category: int = 5
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for category in QUIZ_CATEGORIES:
        rows = session.scalars(
            select(QuizQuestionORM.id)
            .where(
                QuizQuestionORM.level == class_level,
                QuizQuestionORM.category == category,
            )
            .limit(per_category)
        ).all()
        result[category] = [str(qid) for qid in rows]
    return result


def seed_delf_test_sessions(session, students: list[UserORM]) -> None:
    existing = session.scalar(select(DelfTestSessionORM).limit(1))
    if existing is not None:
        print("DELF test sessions: already seeded, skipping.")
        return
    now = _now()
    if len(students) < 2:
        print("DELF test sessions: not enough students, skipping.")
        return
    completed_student = students[2] if len(students) > 2 else students[0]
    in_progress_student = students[3] if len(students) > 3 else students[1]
    class_level = completed_student.class_level or "7ème année"
    question_map = _sample_question_ids(session, class_level)
    category_scores = {
        "Grammaire": 82,
        "Conjugaison": 74,
        "Orthographe": 88,
        "Vocabulaire": 79,
    }
    answers: list[dict[str, Any]] = []
    for category, qids in question_map.items():
        for qid in qids[:3]:
            answers.append(
                {
                    "category": category,
                    "questionId": qid,
                    "selectedIndex": 0,
                    "correct": True,
                }
            )
    overall = sum(category_scores.values()) // len(category_scores)
    session.add(
        DelfTestSessionORM(
            user_id=completed_student.id,
            class_level=class_level,
            target_delf_level=DELF_TARGETS_BY_CLASS.get(class_level, "A2"),
            status="completed",
            question_ids_by_category=question_map,
            answers=answers,
            category_scores=category_scores,
            overall_score=overall,
            achieved_delf_level="A2",
            started_at=now - timedelta(hours=2),
            finished_at=now - timedelta(hours=1),
            created_at=now - timedelta(hours=2),
        )
    )
    ip_class = in_progress_student.class_level or "7ème année"
    ip_questions = _sample_question_ids(session, ip_class)
    session.add(
        DelfTestSessionORM(
            user_id=in_progress_student.id,
            class_level=ip_class,
            target_delf_level=DELF_TARGETS_BY_CLASS.get(ip_class, "A2"),
            status="in_progress",
            question_ids_by_category=ip_questions,
            answers=[],
            category_scores={"Grammaire": 70},
            overall_score=None,
            achieved_delf_level=None,
            started_at=now - timedelta(minutes=30),
            finished_at=None,
            created_at=now - timedelta(minutes=30),
        )
    )
    print("DELF test sessions: 2 created (1 completed, 1 in progress).")


def seed_multiplayer(session, school: SchoolORM | None, students: list[UserORM]) -> None:
    existing = session.scalar(select(MultiplayerRoomORM).limit(1))
    if existing is not None:
        print("Multiplayer: already seeded, skipping.")
        return
    game = session.scalar(select(GameORM).where(GameORM.slug == "quiz_duel").limit(1))
    if game is None or len(students) < 2:
        print("Multiplayer: missing game or students, skipping.")
        return
    prof = session.scalar(
        select(UserORM).where(UserORM.role == "prof").limit(1)
    )
    now = _now()
    class_level = students[0].class_level or "5ème année"
    question_ids = [
        str(qid)
        for qid in session.scalars(
            select(QuizQuestionORM.id)
            .where(QuizQuestionORM.level == class_level)
            .limit(10)
        ).all()
    ]
    room = MultiplayerRoomORM(
        room_code="DEMO01",
        label="Salle démo — Quiz Duel",
        data={
            "hostName": "Prof. Martin",
            "participants": [students[0].email, students[1].email],
            "status": "finished",
        },
        professor_id=prof.id if prof else None,
        school_id=school.id if school else None,
        class_level=class_level,
        created_at=now - timedelta(hours=3),
        updated_at=now - timedelta(hours=2),
    )
    session.add(room)
    session.flush()
    game_session = GameSessionORM(
        room_id=room.id,
        game_id=game.id,
        difficulty="medium",
        class_level=class_level,
        status="finished",
        question_ids=question_ids,
        current_round=10,
        total_rounds=10,
        settings={"questionCount": 10},
        started_at=now - timedelta(hours=3),
        ended_at=now - timedelta(hours=2),
        created_at=now - timedelta(hours=3),
        updated_at=now - timedelta(hours=2),
    )
    session.add(game_session)
    session.flush()
    room.active_session_id = game_session.id
    scores = [920, 780]
    for idx, student in enumerate(students[:2]):
        session.add(
            GameParticipantORM(
                session_id=game_session.id,
                user_id=student.id,
                score=scores[idx],
                rank=idx + 1,
                answers=[{"questionIndex": i, "correct": i % 2 == 0} for i in range(10)],
                joined_at=now - timedelta(hours=3),
                finished_at=now - timedelta(hours=2),
            )
        )
    waiting_room = MultiplayerRoomORM(
        room_code="DEMO02",
        label="Salle en attente — Défi amis",
        data={
            "hostName": students[2].email if len(students) > 2 else "Hôte",
            "participants": [],
            "status": "waiting",
        },
        professor_id=prof.id if prof else None,
        school_id=school.id if school else None,
        class_level=students[2].class_level if len(students) > 2 else class_level,
        created_at=now - timedelta(minutes=15),
        updated_at=now - timedelta(minutes=10),
    )
    session.add(waiting_room)
    print("Multiplayer: 2 rooms and 1 finished game session created.")


def seed_contact_messages(session) -> None:
    existing = session.scalar(
        select(ContactMessageORM)
        .where(ContactMessageORM.subject.like("Demo:%"))
        .limit(1)
    )
    if existing is not None:
        print("Contact messages: already seeded, skipping.")
        return
    now = _now()
    messages = [
        (
            "Marie Dupont",
            "marie.dupont@example.fr",
            "Demo: Question sur les parcours",
            "Bonjour, comment puis-je suivre la progression de ma fille sur le parcours DELF ?",
            False,
        ),
        (
            "Jean Leroy",
            "jean.leroy@example.fr",
            "Demo: Problème de connexion",
            "Je n'arrive pas à me connecter à l'application mobile depuis hier soir.",
            True,
        ),
        (
            "École Voltaire",
            "contact@ecole-voltaire.fr",
            "Demo: Demande de démonstration",
            "Nous souhaiterions une démonstration de la plateforme pour notre établissement.",
            False,
        ),
    ]
    for idx, (name, email, subject, message, is_read) in enumerate(messages):
        session.add(
            ContactMessageORM(
                name=name,
                email=email,
                subject=subject,
                message=message,
                read=is_read,
                created_at=now - timedelta(days=idx),
            )
        )
    print(f"Contact messages: {len(messages)} created.")


def seed_recommendations(session, students: list[UserORM]) -> None:
    existing = session.scalar(select(RecommendationORM).limit(1))
    if existing is not None:
        print("Recommendations: already seeded, skipping.")
        return
    prof = session.scalar(
        select(UserORM).where(UserORM.email == DEMO_PROFESSORS[0]["email"]).limit(1)
    )
    if prof is None or not students:
        print("Recommendations: missing professor or students, skipping.")
        return
    now = _now()
    notes = [
        "Excellent travail en grammaire cette semaine. Continue comme ça !",
        "Révise les temps du passé (imparfait vs passé composé) avant le prochain quiz.",
        "Bravo pour ta participation au débat en classe. Ton vocabulaire progresse bien.",
    ]
    for idx, student in enumerate(students[:3]):
        session.add(
            RecommendationORM(
                student_id=student.id,
                professor_id=prof.id,
                content=notes[idx],
                created_at=now - timedelta(days=idx + 1),
            )
        )
    print(f"Recommendations: {min(3, len(students))} created.")


def seed_quiz_questions_if_needed() -> None:
    from scripts.seed_delf_test_questions import seed as seed_quiz

    seed_quiz()


def seed_delf_mock_exams_if_needed() -> None:
    from scripts.seed_delf_mock_exams import seed as seed_mock_exams

    seed_mock_exams()


def print_summary(session) -> None:
    tables = [
        "users",
        "schools",
        "lessons",
        "stories",
        "quiz_questions",
        "learning_paths",
        "learning_path_steps",
        "games",
        "multiplayer_rooms",
        "game_sessions",
        "game_participants",
        "delf_test_sessions",
        "delf_mock_exams",
        "delf_mock_sections",
        "delf_mock_items",
        "contact_messages",
        "recommendations",
        "student_stats",
        "student_step_progress",
        "user_progress",
    ]
    print("\n── Table counts ──")
    for table in tables:
        count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        print(f"  {table}: {count}")
    print("\n── Demo credentials (password for all: Demo2024!) ──")
    print(f"  School : {DEMO_SCHOOL['email']}")
    print(f"  Prof   : {DEMO_PROFESSORS[0]['email']}")
    print(f"  Student: {DEMO_STUDENTS[0][0]}")


def main() -> None:
    session = SessionLocal()
    try:
        print("=== Seeding demo data ===\n")
        seed_lessons(session)
        seed_stories(session)
        session.commit()
        seed_quiz_questions_if_needed()
        seed_delf_mock_exams_if_needed()
        seed_games(session)
        seed_learning_paths(session)
        school, students = seed_demo_school_and_users(session)
        seed_user_progress(session, students)
        seed_student_stats(session, students)
        seed_step_progress(session, students)
        seed_delf_test_sessions(session, students)
        seed_multiplayer(session, school, students)
        seed_contact_messages(session)
        seed_recommendations(session, students)
        session.commit()
        print("\n=== Demo seed completed ===")
        print_summary(session)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
