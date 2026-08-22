import asyncio
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


@pytest.mark.asyncio
async def test_meal_image_work_does_not_delay_the_initial_reply(command):
    image_started = asyncio.Event()
    image_can_finish = asyncio.Event()

    async def attach_image(*_args):
        image_started.set()
        await image_can_finish.wait()

    command._get_meal = AsyncMock(return_value=_meal_data())
    command._attach_meal_image = attach_image
    ctx = MagicMock()
    ctx.reply = AsyncMock(return_value=MagicMock())

    await command._send_meal(ctx, "auto", "today")
    await image_started.wait()

    ctx.reply.assert_awaited_once()
    assert len(command._image_tasks) == 1

    image_can_finish.set()
    await asyncio.gather(*command._image_tasks)
