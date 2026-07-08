import pytest

from app.application.difficulty_service import DifficultyService
from app.domain.constants import CLASS_LEVELS


@pytest.fixture
def service() -> DifficultyService:
    return DifficultyService()


def test_resolve_question_level_easy_stays_same(service: DifficultyService) -> None:
    for class_level in CLASS_LEVELS:
        assert service.resolve_question_level(class_level, "easy") == class_level


def test_resolve_question_level_hard_advances(service: DifficultyService) -> None:
    assert service.resolve_question_level("2ème année", "hard") == "3ème année"
    assert service.resolve_question_level("8ème année", "hard") == "9ème année"
    assert service.resolve_question_level("9ème année", "hard") == "9ème année"


def test_resolve_question_level_medium_stays_same(service: DifficultyService) -> None:
    assert service.resolve_question_level("5ème année", "medium") == "5ème année"


def test_resolve_question_count_easy_has_fewer(service: DifficultyService) -> None:
    easy_count = service.resolve_question_count(10, "easy")
    hard_count = service.resolve_question_count(10, "hard")
    assert easy_count < hard_count


def test_resolve_time_limit_easy_is_longer(service: DifficultyService) -> None:
    easy_time = service.resolve_time_limit_ms("easy")
    hard_time = service.resolve_time_limit_ms("hard")
    assert easy_time > hard_time


def test_resolve_score_multiplier_factors_user_level(
    service: DifficultyService,
) -> None:
    debutant = service.resolve_score_multiplier("medium", "debutant")
    avance = service.resolve_score_multiplier("medium", "avance")
    assert avance > debutant
