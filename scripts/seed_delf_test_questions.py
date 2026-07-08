#!/usr/bin/env python3
"""Ensure enough quiz questions exist for DELF level tests (5+ per category per class level)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app.domain.constants import CLASS_LEVELS, QUIZ_CATEGORIES
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.models.quiz_question import QuizQuestionORM

MIN_QUESTIONS = 5

SAMPLE_TEMPLATES: dict[str, list[tuple[str, list[str], int, str]]] = {
    "Grammaire": [
        (
            "Choisissez l'article correct : ___ chat est sur la table.",
            ["Le", "La", "Les", "Un"],
            0,
            "« Chat » est masculin singulier → « Le ».",
        ),
        (
            "Quel est le pluriel de « cheval » ?",
            ["chevals", "chevaux", "chevales", "chevauxs"],
            1,
            "Le pluriel irrégulier de « cheval » est « chevaux ».",
        ),
        (
            "Complétez : Marie ___ à l'école chaque matin.",
            ["va", "vas", "allez", "allons"],
            0,
            "Avec « Marie » (3e personne singulier), on utilise « va ».",
        ),
        (
            "Quelle phrase est correcte ?",
            ["Il mange des pomme.", "Il mange des pommes.", "Il mange de pommes.", "Il manges des pommes."],
            1,
            "« Des pommes » est la forme correcte au pluriel.",
        ),
        (
            "Trouvez l'adjectif accordé correctement : Les filles sont ___. ",
            ["content", "contents", "contentes", "contente"],
            2,
            "Avec « filles » (féminin pluriel), l'adjectif prend « -es ».",
        ),
        (
            "Quel pronom remplace « Paul et moi » ?",
            ["Nous", "Vous", "Ils", "Elles"],
            0,
            "« Paul et moi » = 1re personne du pluriel → « nous ».",
        ),
    ],
    "Conjugaison": [
        (
            "Conjuguez : Nous ___ (finir) nos devoirs.",
            ["finissons", "finissez", "finirons", "finissent"],
            0,
            "Au présent, « nous finissons » avec -issons pour les verbes en -ir.",
        ),
        (
            "Quel est le participe passé de « prendre » ?",
            ["pris", "prendu", "pré", "prenu"],
            0,
            "Le participe passé de « prendre » est « pris ».",
        ),
        (
            "Conjuguez au futur : Tu ___ (aller) au cinéma.",
            ["iras", "vas", "allais", "alleras"],
            0,
            "Futur simple de « aller » : « tu iras ».",
        ),
        (
            "Quelle forme est à l'imparfait ?",
            ["Je chantais", "Je chante", "Je chanterai", "J'ai chanté"],
            0,
            "« Je chantais » est à l'imparfait.",
        ),
        (
            "Conjuguez : Ils ___ (être) en retard.",
            ["sont", "es", "sommes", "est"],
            0,
            "3e personne du pluriel de « être » : « sont ».",
        ),
        (
            "Conjuguez au passé composé : Elle ___ (manger) une pomme.",
            ["a mangé", "est mangé", "mange", "mangeait"],
            0,
            "« Manger » avec « avoir » : « elle a mangé ».",
        ),
    ],
    "Orthographe": [
        (
            "Quelle orthographe est correcte ?",
            ["apeller", "appeler", "apeler", "appeler"],
            1,
            "Le verbe s'écrit « appeler » avec deux « p ».",
        ),
        (
            "Trouvez le mot bien écrit :",
            ["beaucoup", "beaucoups", "bocoup", "beaucou"],
            0,
            "« Beaucoup » s'écrit sans « s » et avec « eau ».",
        ),
        (
            "Quel mot contient « é » ou « er » correct ?",
            ["compris", "compri", "comprie", "comprisent"],
            0,
            "Participe passé de « comprendre » : « compris ».",
        ),
        (
            "Choisissez la bonne forme : C'est ___ livre.",
            ["mon", "mone", "ma", "mes"],
            0,
            "« Livre » est masculin → « mon livre ».",
        ),
        (
            "Quelle phrase est bien orthographiée ?",
            ["Je suis très heureux.", "Je suis trés heureux.", "Je suis trè heureux.", "Je suis tres heureux."],
            0,
            "« Très » prend un accent grave.",
        ),
        (
            "Trouvez l'accord correct : Les ___ sont ouvertes.",
            ["fenêtre", "fenêtres", "fenetres", "fenêtré"],
            1,
            "Pluriel de « fenêtre » : « fenêtres ».",
        ),
    ],
    "Vocabulaire": [
        (
            "Que signifie « bonjour » ?",
            ["Goodbye", "Hello", "Thank you", "Please"],
            1,
            "« Bonjour » est une salutation = Hello.",
        ),
        (
            "Quel mot désigne un endroit où l'on achète du pain ?",
            ["boulangerie", "pharmacie", "bibliothèque", "librairie"],
            0,
            "La « boulangerie » vend du pain.",
        ),
        (
            "Trouvez le synonyme de « rapide » :",
            ["lent", "vite", "grand", "petit"],
            1,
            "« Vite » est proche de « rapide ».",
        ),
        (
            "Quel mot désigne la saison après l'hiver ?",
            ["automne", "printemps", "été", "hiver"],
            1,
            "Après l'hiver vient le « printemps ».",
        ),
        (
            "Que signifie « merci » ?",
            ["Sorry", "Please", "Thank you", "Hello"],
            2,
            "« Merci » exprime la gratitude.",
        ),
        (
            "Quel mot désigne un animal domestique qui miaule ?",
            ["chien", "chat", "cheval", "oiseau"],
            1,
            "Le « chat » miaule.",
        ),
    ],
}


def _count_for(level: str, category: str, session) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(QuizQuestionORM)
            .where(
                QuizQuestionORM.level == level,
                QuizQuestionORM.category == category,
            )
        )
        or 0
    )


def seed() -> None:
    session = SessionLocal()
    created = 0
    try:
        for class_level in CLASS_LEVELS:
            for category in QUIZ_CATEGORIES:
                existing = _count_for(class_level, category, session)
                needed = max(0, MIN_QUESTIONS - existing)
                if needed == 0:
                    continue
                templates = SAMPLE_TEMPLATES.get(category, [])
                for index in range(needed):
                    template = templates[index % len(templates)]
                    question_text, options, correct_index, explanation = template
                    row = QuizQuestionORM(
                        question=f"[{class_level}] {question_text}",
                        options=list(options),
                        correct_index=correct_index,
                        explanation=explanation,
                        category=category,
                        level=class_level,
                    )
                    session.add(row)
                    created += 1
        session.commit()
        print(f"Seed DELF test questions: {created} question(s) created.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
