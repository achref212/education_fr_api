#!/usr/bin/env python3
"""Seed original DELF mock exams for all supported Prime and Junior levels."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.application.delf_mock_exam_service import DelfMockExamService
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.models.delf_mock_exam import DelfMockExamORM
from app.infrastructure.repositories.sql_delf_mock_exam_repository import (
    SqlDelfMockExamRepository,
)

SUPPORTED_EXAMS: tuple[tuple[str, str], ...] = (
    ("Prime", "A1.1"),
    ("Prime", "A1"),
    ("Prime", "A2"),
    ("Junior", "A1"),
    ("Junior", "A2"),
    ("Junior", "B1"),
    ("Junior", "B2"),
)

DURATION_BY_LEVEL: dict[str, tuple[int, int, int, int]] = {
    "A1.1": (15, 15, 15, 15),
    "A1": (20, 30, 30, 7),
    "A2": (25, 30, 45, 8),
    "B1": (25, 45, 45, 15),
    "B2": (30, 60, 60, 20),
}


def seed() -> None:
    session = SessionLocal()
    created = 0
    try:
        service = DelfMockExamService(SqlDelfMockExamRepository(session))
        for track, level in SUPPORTED_EXAMS:
            exists = session.scalar(
                select(DelfMockExamORM.id)
                .where(
                    DelfMockExamORM.track == track,
                    DelfMockExamORM.level == level,
                    DelfMockExamORM.title == _title(track, level),
                )
                .limit(1)
            )
            if exists is not None:
                continue
            service.create_exam(_payload(track, level))
            created += 1
        session.commit()
        print(f"Seed DELF mock exams: {created} exam(s) created.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _title(track: str, level: str) -> str:
    return f"Examen blanc DELF {track} {level} - Démo originale"


def _payload(track: str, level: str) -> dict[str, Any]:
    listening_duration, reading_duration, writing_duration, speaking_duration = (
        DURATION_BY_LEVEL[level]
    )
    audience = "enfants" if track == "Prime" else "adolescents"
    theme = _theme(level)
    return {
        "track": track,
        "level": level,
        "title": _title(track, level),
        "description": (
            f"Sujet blanc original pour {audience}, niveau {level}, "
            "structuré selon les quatre compétences DELF."
        ),
        "status": "published",
        "sourceNotes": (
            "Contenu original de démonstration. Format inspiré des épreuves DELF, "
            "sans reprise de texte, d'image ou d'audio officiel. Relecture professeur requise."
        ),
        "sections": [
            _listening(level, listening_duration, theme),
            _reading(level, reading_duration, theme),
            _writing(level, writing_duration, theme),
            _speaking(level, speaking_duration, theme),
        ],
        "assets": [],
    }


def _listening(level: str, duration: int, theme: dict[str, str]) -> dict[str, Any]:
    return {
        "sectionOrder": 1,
        "sectionType": "listening",
        "title": "Compréhension de l'oral",
        "durationMinutes": duration,
        "points": 25,
        "instructions": "Écoute les documents deux fois puis réponds aux questions.",
        "audioUrl": None,
        "rubric": {"scoring": "1 point par réponse juste, barème ajusté sur 25."},
        "metadata": {"officialSkill": "CO", "source": "original_seed"},
        "items": [
            {
                "itemOrder": 1,
                "title": "Messages courts",
                "prompt": "Écoute trois messages et choisis l'information correcte.",
                "points": 8,
                "content": {
                    "transcripts": [
                        f"Salut, c'est {theme['name']}. Le club commence à quinze heures dans la salle bleue.",
                        f"Bonjour, le sac de sport est resté près du bureau de la vie scolaire.",
                        f"Rendez-vous samedi matin devant la médiathèque pour l'atelier {theme['activity']}.",
                    ],
                    "questions": [
                        {"question": "À quelle heure commence le club ?", "options": ["14 h", "15 h", "16 h"]},
                        {"question": "Où est le sac ?", "options": ["près du bureau", "dans la cour", "au gymnase"]},
                        {"question": "Où est le rendez-vous ?", "options": ["devant la médiathèque", "au parc", "en classe"]},
                    ],
                },
                "answerKey": {"answers": ["15 h", "près du bureau", "devant la médiathèque"]},
                "rubric": {"pointsPerAnswer": [3, 2, 3]},
                "metadata": {},
            },
            {
                "itemOrder": 2,
                "title": "Dialogue quotidien",
                "prompt": "Écoute le dialogue et associe chaque personne à son choix.",
                "points": 8,
                "content": {
                    "transcripts": [
                        f"- Tu veux préparer quoi pour la sortie ? - Je prends de l'eau et mon carnet. "
                        f"- Moi, je prends l'appareil photo pour le projet {theme['project']}."
                    ],
                    "matching": [
                        {"person": theme["name"], "choices": ["eau", "appareil photo", "ballon"]},
                        {"person": theme["friend"], "choices": ["carnet", "appareil photo", "livre"]},
                    ],
                },
                "answerKey": {"matches": {theme["name"]: "eau", theme["friend"]: "appareil photo"}},
                "rubric": {"pointsPerMatch": 4},
                "metadata": {},
            },
            {
                "itemOrder": 3,
                "title": "Annonce",
                "prompt": "Écoute l'annonce et réponds aux questions ouvertes courtes.",
                "points": 9,
                "content": {
                    "transcripts": [
                        f"Attention, l'activité {theme['activity']} est déplacée. Elle aura lieu jeudi, "
                        f"après le déjeuner, dans la grande salle. Apportez un crayon et une feuille."
                    ],
                    "questions": [
                        "Quel jour a lieu l'activité ?",
                        "Où a lieu l'activité ?",
                        "Que faut-il apporter ?",
                    ],
                },
                "answerKey": {"answers": ["jeudi", "dans la grande salle", "un crayon et une feuille"]},
                "rubric": {"pointsPerAnswer": [3, 3, 3]},
                "metadata": {},
            },
        ],
    }


def _reading(level: str, duration: int, theme: dict[str, str]) -> dict[str, Any]:
    return {
        "sectionOrder": 2,
        "sectionType": "reading",
        "title": "Compréhension des écrits",
        "durationMinutes": duration,
        "points": 25,
        "instructions": "Lis les documents puis réponds aux questions.",
        "audioUrl": None,
        "rubric": {"scoring": "Réponses exactes attendues; synonymes acceptés si le sens est conservé."},
        "metadata": {"officialSkill": "CE", "source": "original_seed"},
        "items": [
            {
                "itemOrder": 1,
                "title": "Liste utile",
                "prompt": "Repère les quatre éléments demandés dans la liste.",
                "points": 8,
                "content": {
                    "document": (
                        f"Pour l'atelier {theme['activity']}, apporte une feuille, deux crayons, "
                        "une règle et une petite photo."
                    ),
                    "task": "Sélectionne les quatre objets nécessaires.",
                },
                "answerKey": {"answers": ["feuille", "crayons", "règle", "photo"]},
                "rubric": {"pointsPerAnswer": 2},
                "metadata": {},
            },
            {
                "itemOrder": 2,
                "title": "Message personnel",
                "prompt": "Lis le message et réponds aux questions.",
                "points": 7,
                "content": {
                    "document": (
                        f"Bonjour, je t'invite vendredi à 17 h pour préparer notre projet {theme['project']}. "
                        f"On travaille chez moi avec {theme['friend']}. À bientôt !"
                    ),
                    "questions": ["Quel jour ?", "À quelle heure ?", "Avec qui ?"],
                },
                "answerKey": {"answers": ["vendredi", "17 h", theme["friend"]]},
                "rubric": {"pointsPerAnswer": [2, 2, 3]},
                "metadata": {},
            },
            {
                "itemOrder": 3,
                "title": "Règlement simple",
                "prompt": "Associe chaque règle à la bonne action.",
                "points": 10,
                "content": {
                    "document": [
                        "Je parle doucement dans le couloir.",
                        "Je range le matériel après l'activité.",
                        "Je demande de l'aide si je ne comprends pas.",
                        "Je respecte le travail des autres groupes.",
                    ],
                    "actions": ["ranger", "demander", "respecter", "parler doucement"],
                },
                "answerKey": {"matches": ["parler doucement", "ranger", "demander", "respecter"]},
                "rubric": {"pointsPerMatch": [2, 3, 2, 3]},
                "metadata": {},
            },
        ],
    }


def _writing(level: str, duration: int, theme: dict[str, str]) -> dict[str, Any]:
    return {
        "sectionOrder": 3,
        "sectionType": "writing",
        "title": "Production écrite",
        "durationMinutes": duration,
        "points": 25,
        "instructions": "Écris tes réponses avec des phrases claires et adaptées au niveau.",
        "audioUrl": None,
        "rubric": {
            "taskCompletion": 10,
            "coherence": 5,
            "lexis": 5,
            "grammar": 5,
        },
        "metadata": {"officialSkill": "PE", "source": "original_seed"},
        "items": [
            {
                "itemOrder": 1,
                "title": "Fiche d'inscription",
                "prompt": "Complète une fiche avec tes informations et deux activités préférées.",
                "points": 7,
                "content": {"fields": ["nom", "prénom", "classe", "activités préférées"]},
                "answerKey": {"type": "rubric"},
                "rubric": {"completeFields": 5, "spelling": 2},
                "metadata": {},
            },
            {
                "itemOrder": 2,
                "title": "Message à compléter",
                "prompt": f"Complète un court message sur une activité {theme['activity']}.",
                "points": 8,
                "content": {
                    "starter": f"Salut, aujourd'hui je prépare {theme['activity']} avec ma classe. Nous avons besoin de..."
                },
                "answerKey": {"type": "rubric"},
                "rubric": {"meaning": 4, "vocabulary": 2, "grammar": 2},
                "metadata": {},
            },
            {
                "itemOrder": 3,
                "title": "Message personnel",
                "prompt": (
                    f"Écris à {theme['friend']} pour l'inviter à participer au projet {theme['project']}. "
                    "Donne le lieu, le moment et deux choses à apporter."
                ),
                "points": 10,
                "content": {"minimumWords": _minimum_words(level)},
                "answerKey": {"type": "rubric"},
                "rubric": {"taskCompletion": 4, "coherence": 2, "lexis": 2, "grammar": 2},
                "metadata": {},
            },
        ],
    }


def _speaking(level: str, duration: int, theme: dict[str, str]) -> dict[str, Any]:
    return {
        "sectionOrder": 4,
        "sectionType": "speaking",
        "title": "Production orale",
        "durationMinutes": duration,
        "points": 25,
        "instructions": "Réponds à l'examinateur, pose des questions et réalise une tâche simple.",
        "audioUrl": None,
        "rubric": {
            "interaction": 8,
            "taskCompletion": 7,
            "lexis": 5,
            "grammarPronunciation": 5,
        },
        "metadata": {"officialSkill": "PO", "source": "original_seed"},
        "items": [
            {
                "itemOrder": 1,
                "title": "Entretien dirigé",
                "prompt": "Présente-toi et réponds à des questions sur tes goûts.",
                "points": 8,
                "content": {"sampleQuestions": ["Comment tu t'appelles ?", "Qu'est-ce que tu aimes faire ?"]},
                "answerKey": {"type": "rubric"},
                "rubric": {"relevance": 4, "clarity": 4},
                "metadata": {},
            },
            {
                "itemOrder": 2,
                "title": "Échange d'informations",
                "prompt": f"Pose des questions pour organiser une activité {theme['activity']}.",
                "points": 8,
                "content": {"cards": ["jour", "heure", "lieu", "matériel"]},
                "answerKey": {"type": "rubric"},
                "rubric": {"questions": 5, "interaction": 3},
                "metadata": {},
            },
            {
                "itemOrder": 3,
                "title": "Dialogue simulé",
                "prompt": f"Imagine un dialogue avec un camarade pour présenter le projet {theme['project']}.",
                "points": 9,
                "content": {"roleA": "élève", "roleB": "camarade"},
                "answerKey": {"type": "rubric"},
                "rubric": {"taskCompletion": 4, "fluency": 3, "accuracy": 2},
                "metadata": {},
            },
        ],
    }


def _theme(level: str) -> dict[str, str]:
    themes = {
        "A1.1": {"name": "Mina", "friend": "Noé", "activity": "dessin", "project": "affiche de classe"},
        "A1": {"name": "Sami", "friend": "Lina", "activity": "lecture", "project": "journal du collège"},
        "A2": {"name": "Inès", "friend": "Hugo", "activity": "sciences", "project": "exposition écologique"},
        "B1": {"name": "Nadia", "friend": "Yanis", "activity": "débat", "project": "semaine sans plastique"},
        "B2": {"name": "Camille", "friend": "Rayan", "activity": "atelier média", "project": "podcast citoyen"},
    }
    return themes[level]


def _minimum_words(level: str) -> int:
    return {"A1.1": 20, "A1": 40, "A2": 60, "B1": 120, "B2": 180}[level]


if __name__ == "__main__":
    seed()
