from unittest.mock import AsyncMock, MagicMock

import pytest

from src.interfaces.commands.meal.MealCommand import MealCommands


def _meal_data() -> dict:
    return {
        "title": "🍚 점심",
        "menu": "- 테스트 급식",
        "cal_info": "700 Kcal",
        "date": "20260822",
        "meal_code": "2",
    }


@pytest.fixture
def command():
    meal_command = MealCommands(MagicMock(), MagicMock())
    meal_command.api.get_meal = AsyncMock(return_value=_meal_data())
    return meal_command


@pytest.mark.asyncio
async def test_primary_meal_uses_the_preloaded_response(command):
    await command._refresh_meal("auto", "today", None)
    command.api.get_meal.reset_mock()

    result = await command._get_meal("auto", "today", None)

    assert result == _meal_data()
    command.api.get_meal.assert_not_awaited()


@pytest.mark.asyncio
async def test_primary_meal_serves_stale_data_without_waiting_for_api(command):
    command._meal_cache[("auto", "today", None)] = (0, _meal_data())
    command.api.get_meal.side_effect = RuntimeError("API unavailable")

    result = await command._get_meal("auto", "today", None)

    assert result == _meal_data()
    command.api.get_meal.assert_not_awaited()
