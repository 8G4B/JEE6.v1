import asyncio
import importlib
import io
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from PIL import Image

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
async def command():
    meal_command = MealCommands(MagicMock(), MagicMock())
    meal_command.meal_service._now = lambda: datetime(
        2026, 8, 22, 12, tzinfo=ZoneInfo("Asia/Seoul")
    )
    meal_command.api.get_meal_week = AsyncMock(
        return_value={"week_start": "20260817", "meals": [_meal_data()]}
    )
    image_cache = importlib.import_module(
        "src.interfaces.commands.meal.MealCommand"
    )._IMG_CACHE
    image_cache.clear()
    yield meal_command
    await meal_command.cog_unload()
    image_cache.clear()


@pytest.mark.asyncio
async def test_primary_meal_uses_the_preloaded_response(command):
    await command.meal_service._wait_for_week("20260817")
    command.api.get_meal_week.reset_mock()

    result = await command._get_meal("auto", "today", None)

    assert result == _meal_data()
    command.api.get_meal_week.assert_not_awaited()


@pytest.mark.asyncio
async def test_primary_meal_serves_stale_data_without_waiting_for_api(command):
    await command.meal_service._wait_for_week("20260817")
    command.meal_service._weeks["20260817"].expires_at = 0
    command.api.get_meal_week.reset_mock()
    command.api.get_meal_week.side_effect = RuntimeError("API unavailable")

    result = await command._get_meal("auto", "today", None)

    assert result == _meal_data()
    command.api.get_meal_week.assert_not_awaited()


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


async def test_concurrent_photo_lookups_share_one_request(command):
    command.api.get_meal_image = AsyncMock(
        return_value={"image_url": "https://photo.test/1"}
    )

    results = await asyncio.gather(
        *(command._get_image_url("20260822", "2") for _ in range(8))
    )

    assert results == ["https://photo.test/1"] * 8
    assert await command._get_image_url("20260822", "2") == results[0]
    command.api.get_meal_image.assert_awaited_once_with("20260822", "2")


async def test_concurrent_photos_download_and_resize_once(command, monkeypatch):
    entered, release = asyncio.Event(), asyncio.Event()
    response = AsyncMock()
    response.status = 200
    response.__aenter__.return_value = response

    async def read():
        entered.set()
        await release.wait()
        return b"source image"

    response.read.side_effect = read
    session = MagicMock()
    session.get.return_value = response
    module = importlib.import_module("src.interfaces.commands.meal.MealCommand")
    monkeypatch.setattr(module, "get_http_session", AsyncMock(return_value=session))
    command._resize_to_jpeg = MagicMock(return_value=b"jpeg")

    requests = [
        asyncio.create_task(command._get_resized_image("https://photo.test/1"))
        for _ in range(8)
    ]
    await entered.wait()
    release.set()
    assert await asyncio.gather(*requests) == [b"jpeg"] * 8
    assert await command._get_resized_image("https://photo.test/1") == b"jpeg"
    session.get.assert_called_once()
    command._resize_to_jpeg.assert_called_once_with(b"source image")


async def test_photo_failure_keeps_the_menu_reply(command):
    command._get_meal = AsyncMock(return_value=_meal_data())
    command.api.get_meal_image = AsyncMock(side_effect=RuntimeError("photo offline"))
    ctx = MagicMock()
    ctx.reply = AsyncMock(return_value=MagicMock())
    ctx.send = AsyncMock()

    await command._send_meal(ctx, "auto", "today")
    await asyncio.gather(*command._image_tasks)

    ctx.reply.assert_awaited_once()
    ctx.send.assert_not_awaited()


def test_resize_preserves_aspect_ratio_and_produces_a_small_jpeg():
    raw = io.BytesIO()
    Image.new("RGB", (4000, 2000), "white").save(raw, format="JPEG")

    jpeg = MealCommands._resize_to_jpeg(raw.getvalue())

    with Image.open(io.BytesIO(jpeg)) as image:
        assert image.format == "JPEG"
        assert image.size == (1280, 640)
