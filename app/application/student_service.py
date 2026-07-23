from collections import Counter, defaultdict
from uuid import UUID

from app.application.ai_content_service import AIContentError, AIContentService
from app.application.delf_test_service import DelfTestService
from app.application.parcours_service import ParcoursError, ParcoursService
from app.application.student_stats_service import StudentStatsService
from app.domain.entities import (
    StudentLeaderboardEntry,
    StudentReviewItem,
    User,
)
from app.domain.ports import (
    IDelfTestRepository,
    IStudentProgressRepository,
    IStudentReviewRepository,
)


class StudentService:
    def __init__(
        self,
        *,
        reviews: IStudentReviewRepository,
        progress: IStudentProgressRepository,
        stats: StudentStatsService,
        parcours: ParcoursService,
        delf_tests: IDelfTestRepository,
        delf_service: DelfTestService,
        ai: AIContentService | None = None,
    ) -> None:
        self._reviews = reviews
        self._progress = progress
        self._stats = stats
        self._parcours = parcours
        self._delf_tests = delf_tests
        self._delf_service = delf_service
        self._ai = ai

    def get_hub(self, user: User) -> dict:
        stats = self._stats.get_or_create(user.id)
        summary = self._safe_summary(user)
        review = self.get_review(user)
        history = self._completed_delf_sessions(user.id)
        recent = self._recent_delf(history[0]) if history else None
        achievements = self.get_achievements(user)["items"]
        next_action = self._next_action(summary, review, recent)
        level = max(1, stats.total_xp // 100 + 1)
        return {
            "firstName": user.first_name,
            "lastName": user.last_name,
            "classLevel": user.class_level,
            "profilePictureUrl": user.profile_picture_url,
            "totalXp": stats.total_xp,
            "currentStreak": stats.current_streak,
            "longestStreak": stats.longest_streak,
            "level": level,
            "completedSteps": summary["completedSteps"],
            "totalSteps": summary["totalSteps"],
            "parcoursPercent": summary["completionPercent"],
            "nextStepId": summary["nextStepId"],
            "nextStepTitle": summary["nextStepTitle"],
            "reviewOpenCount": review["totalOpen"],
            "weakCategories": review["weakCategories"],
            "recentDelf": recent,
            "achievementsPreview": achievements[:4],
            "nextAction": next_action,
        }

    def get_leaderboard(self, user: User, scope: str) -> dict:
        if scope not in {"class", "school"}:
            scope = "class"
        school_id = user.school_id if scope == "school" else user.school_id
        class_level = user.class_level if scope == "class" else None
        entries = self._progress.list_leaderboard(
            school_id=school_id,
            class_level=class_level,
        )
        summary = self._safe_summary(user)
        total_steps = summary["totalSteps"]
        resolved: list[dict] = []
        current: dict | None = None
        for entry in entries:
            item = self._leaderboard_entry(entry, user.id, total_steps)
            resolved.append(item)
            if entry.user_id == user.id:
                current = item
        return {
            "scope": scope,
            "currentRank": current["rank"] if current else None,
            "currentStudent": current,
            "entries": resolved[:50],
        }

    def get_achievements(self, user: User) -> dict:
        stats = self._stats.get_or_create(user.id)
        summary = self._safe_summary(user)
        review_items = self._reviews.list_for_user(user.id)
        completed_review = sum(1 for item in review_items if item.status == "completed")
        open_review = sum(1 for item in review_items if item.status == "open")
        best_delf = max(
            (s.overall_score or 0 for s in self._completed_delf_sessions(user.id)),
            default=0,
        )
        raw = [
            self._achievement(
                "first_step",
                "Premier pas",
                "Terminer une étape du parcours.",
                "flag",
                summary["completedSteps"],
                1,
                "parcours",
            ),
            self._achievement(
                "xp_100",
                "100 XP",
                "Gagner 100 points d'expérience.",
                "sparkles",
                stats.total_xp,
                100,
                "progression",
            ),
            self._achievement(
                "streak_3",
                "Série de 3",
                "Réviser trois jours de suite.",
                "flame",
                stats.current_streak,
                3,
                "habitude",
            ),
            self._achievement(
                "streak_7",
                "Semaine solide",
                "Garder une série de sept jours.",
                "calendar",
                stats.current_streak,
                7,
                "habitude",
            ),
            self._achievement(
                "review_5",
                "Révision active",
                "Corriger cinq erreurs dans le centre de révision.",
                "check",
                completed_review,
                5,
                "revision",
            ),
            self._achievement(
                "review_clear",
                "Boîte claire",
                "Terminer toutes les révisions disponibles.",
                "inbox",
                1 if review_items and open_review == 0 else 0,
                1,
                "revision",
            ),
            self._achievement(
                "delf_70",
                "Objectif DELF",
                "Obtenir au moins 70% à un test DELF.",
                "award",
                best_delf,
                70,
                "delf",
            ),
        ]
        next_badge = next((item for item in raw if not item["unlocked"]), None)
        return {
            "unlockedCount": sum(1 for item in raw if item["unlocked"]),
            "totalCount": len(raw),
            "nextBadge": next_badge,
            "items": raw,
        }

    def get_review(self, user: User) -> dict:
        items = self._reviews.list_for_user(user.id)
        open_items = [item for item in items if item.status == "open"]
        completed_items = [item for item in items if item.status == "completed"]
        counts = Counter(item.category for item in open_items)
        groups: dict[str, list[StudentReviewItem]] = defaultdict(list)
        for item in open_items:
            groups[item.category].append(item)
        return {
            "totalOpen": len(open_items),
            "totalCompleted": len(completed_items),
            "weakCategories": [
                {"category": category, "count": count}
                for category, count in counts.most_common()
            ],
            "groups": [
                {
                    "category": category,
                    "total": len(group_items),
                    "openCount": len(group_items),
                    "items": [self._review_item(item) for item in group_items],
                }
                for category, group_items in sorted(groups.items())
            ],
        }

    def complete_review_item(self, user: User, item_id: UUID) -> dict:
        item = self._reviews.mark_completed(user.id, item_id)
        if item is None:
            raise StudentError("Révision introuvable")
        return self._review_item(item)

    def get_hint(self, user: User, item_id: UUID) -> dict:
        item = self._reviews.get_for_user(user.id, item_id)
        if item is None:
            raise StudentError("Révision introuvable")
        selected = _answer_at(item.options, item.selected_index)
        correct = _answer_at(item.options, item.correct_index)
        fallback = item.explanation or (
            "Relis la question, compare les indices de la phrase, puis vérifie la règle avant de répondre."
        )
        if self._ai is None:
            return {"itemId": item.id, "hint": fallback, "source": "fallback", "provider": None}
        try:
            hint, provider = self._ai.generate_student_hint(
                question=item.question,
                selected_answer=selected,
                correct_answer=correct,
                explanation=item.explanation,
                category=item.category,
            )
            return {
                "itemId": item.id,
                "hint": hint,
                "source": "ai",
                "provider": provider.model_dump(by_alias=True),
            }
        except AIContentError:
            return {"itemId": item.id, "hint": fallback, "source": "fallback", "provider": None}

    def _safe_summary(self, user: User) -> dict:
        try:
            summary = self._parcours.get_summary(user)
            return {
                "completionPercent": summary.completion_percent,
                "totalSteps": summary.total_steps,
                "completedSteps": summary.completed_steps,
                "nextStepId": summary.next_step_id,
                "nextStepTitle": summary.next_step_title,
            }
        except ParcoursError:
            return {
                "completionPercent": 0.0,
                "totalSteps": 0,
                "completedSteps": 0,
                "nextStepId": None,
                "nextStepTitle": None,
            }

    def _completed_delf_sessions(self, user_id: UUID):
        return [
            session
            for session in self._delf_tests.list_sessions_for_user(user_id)
            if session.status == "completed"
        ]

    def _next_action(self, summary: dict, review: dict, recent: dict | None) -> dict:
        if review["totalOpen"] > 0:
            return {
                "type": "review",
                "title": "Réviser tes erreurs",
                "subtitle": f"{review['totalOpen']} carte(s) à terminer",
                "route": "review",
                "itemId": None,
            }
        if summary["nextStepId"] is not None:
            return {
                "type": "parcours",
                "title": summary["nextStepTitle"] or "Continuer le parcours",
                "subtitle": "Prochaine étape recommandée",
                "route": "parcours",
                "itemId": str(summary["nextStepId"]),
            }
        return {
            "type": "delf",
            "title": "Faire un entraînement DELF",
            "subtitle": "Mesure ton niveau et ajuste ton parcours",
            "route": "delf",
            "itemId": str(recent["sessionId"]) if recent else None,
        }

    def _recent_delf(self, session) -> dict:
        return {
            "sessionId": session.id,
            "targetDelfLevel": session.target_delf_level,
            "achievedDelfLevel": session.achieved_delf_level,
            "overallScore": session.overall_score,
            "categoryScores": session.category_scores,
            "finishedAt": session.finished_at,
        }

    def _leaderboard_entry(
        self,
        entry: StudentLeaderboardEntry,
        current_user_id: UUID,
        total_steps: int,
    ) -> dict:
        progress_percent = (
            round(entry.completed_steps / total_steps * 100, 1)
            if total_steps
            else entry.progress_percent
        )
        return {
            "userId": entry.user_id,
            "firstName": entry.first_name,
            "lastName": entry.last_name,
            "classLevel": entry.class_level,
            "profilePictureUrl": entry.profile_picture_url,
            "totalXp": entry.total_xp,
            "currentStreak": entry.current_streak,
            "completedSteps": entry.completed_steps,
            "progressPercent": progress_percent,
            "rank": entry.rank,
            "isCurrentUser": entry.user_id == current_user_id,
        }

    def _review_item(self, item: StudentReviewItem) -> dict:
        return {
            "id": item.id,
            "sourceType": item.source_type,
            "sourceId": item.source_id,
            "questionId": item.question_id,
            "category": item.category,
            "question": item.question,
            "options": item.options,
            "selectedIndex": item.selected_index,
            "correctIndex": item.correct_index,
            "explanation": item.explanation,
            "status": item.status,
            "timesReviewed": item.times_reviewed,
            "createdAt": item.created_at,
            "updatedAt": item.updated_at,
            "lastReviewedAt": item.last_reviewed_at,
        }

    def _achievement(
        self,
        badge_id: str,
        title: str,
        description: str,
        icon: str,
        current: int,
        target: int,
        category: str,
    ) -> dict:
        progress = min(max(current, 0), target)
        return {
            "id": badge_id,
            "title": title,
            "description": description,
            "icon": icon,
            "unlocked": current >= target,
            "progress": progress,
            "target": target,
            "category": category,
        }


class StudentError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _answer_at(options: list, index: int | None) -> str | None:
    if index is None or index < 0 or index >= len(options):
        return None
    return str(options[index])
