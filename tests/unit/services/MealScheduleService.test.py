import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from src.services.MealScheduleService import MealScheduleService


SEOUL = ZoneInfo("Asia/Seoul")


def week_data(monday):
    start = datetime.strptime(monday, "%Y%m%d")
    return {
        "week_start": monday,
        "meals": [
            {
                "date": (start + timedelta(days=day)).strftime("%Y%m%d"),
                "meal_code": code,
                "menu": f"- {day}/{code}",
                "cal_info": "700 Kcal",
            }
            for day in range(7)
            for code in ("1", "2", "3")
        ],
    }


@pytest.fixture
async def schedule():
    clock = [datetime(2026, 10, 29, 7, 29, 59, tzinfo=SEOUL)]
    api = AsyncMock()
    api.get_meal_week.side_effect = week_data
    service = MealScheduleService(api, now=lambda: clock[0])
    yield service, api, clock
    await service.close()


async def test_warm_cache_serves_all_meals_without_network(schedule):
    service, api, _ = schedule
    await service.warm()
    api.get_meal_week.reset_mock()

    for meal_type, code in (("breakfast", "1"), ("lunch", "2"), ("dinner", "3")):
        result = await service.get_meal(meal_type)
        assert result["meal_code"] == code
        assert result["date"] == "20261029"
    assert (await service.get_meal("dinner", "tomorrow"))["date"] == "20261030"
    api.get_meal_week.assert_not_awaited()


@pytest.mark.parametrize(
    "hour,minute,second,code,date,title",
    [
        (7, 29, 59, "1", "20261029", "🍳 아침"),
        (7, 30, 0, "2", "20261029", "🍚 점심"),
        (12, 29, 59, "2", "20261029", "🍚 점심"),
        (12, 30, 0, "3", "20261029", "🍖 저녁"),
        (18, 29, 59, "3", "20261029", "🍖 저녁"),
        (18, 30, 0, "1", "20261030", "🍳 내일 아침"),
    ],
)
async def test_meal_boundaries_select_the_correct_cached_menu(
    schedule, hour, minute, second, code, date, title
):
    service, api, clock = schedule
    await service.warm()
    api.get_meal_week.reset_mock()
    clock[0] = clock[0].replace(hour=hour, minute=minute, second=second)

    result = await service.get_meal()

    assert (result["meal_code"], result["date"], result["title"]) == (code, date, title)
    api.get_meal_week.assert_not_awaited()


async def test_midnight_changes_title_without_reusing_yesterdays_meal(schedule):
    service, api, clock = schedule
    await service.warm()
    clock[0] = clock[0].replace(hour=23)
    before = await service.get_meal()
    clock[0] = datetime(2026, 10, 30, 0, 0, tzinfo=SEOUL)
    after = await service.get_meal()

    assert before["date"] == after["date"] == "20261030"
    assert before["menu"] == after["menu"]
    assert before["title"] == "🍳 내일 아침"
    assert after["title"] == "🍳 아침"
    assert api.get_meal_week.await_count == 2


@pytest.mark.parametrize(
    "now,expected_date",
    [
        (datetime(2026, 11, 1, 18, 30, tzinfo=SEOUL), "20261102"),
        (datetime(2026, 12, 31, 18, 30, tzinfo=SEOUL), "20270101"),
    ],
)
async def test_week_and_year_rollovers_use_preloaded_dated_rows(
    schedule, now, expected_date
):
    service, api, clock = schedule
    clock[0] = now.replace(hour=12)
    await service.warm()
    api.get_meal_week.reset_mock()
    clock[0] = now

    result = await service.get_meal()

    assert result["date"] == expected_date
    assert result["title"] == "🍳 내일 아침"
    api.get_meal_week.assert_not_awaited()


async def test_explicit_date_and_tomorrow_auto_keep_the_existing_semantics(schedule):
    service, _, clock = schedule
    clock[0] = clock[0].replace(hour=20)
    assert (await service.get_meal(date="20261026"))["title"] == "🍳 아침 (10/26)"
    assert (await service.get_meal(day="tomorrow"))["date"] == "20261030"
    assert "error" in await service.get_meal(date="20260230")
    assert "error" in await service.get_meal(date="20270101")


async def test_concurrent_cold_requests_share_one_week_load(schedule):
    service, api, _ = schedule

    async def load(monday):
        await asyncio.sleep(0)
        return week_data(monday)

    api.get_meal_week.side_effect = load
    results = await asyncio.gather(*(service.get_meal() for _ in range(8)))

    assert all(result["meal_code"] == "1" for result in results)
    api.get_meal_week.assert_awaited_once_with("20261026")


async def test_a_slow_other_week_does_not_block_the_primary_meal(schedule):
    service, api, _ = schedule
    entered, release = asyncio.Event(), asyncio.Event()

    async def load(monday):
        if monday == "20261019":
            entered.set()
            await release.wait()
        return week_data(monday)

    api.get_meal_week.side_effect = load
    other = asyncio.create_task(service.get_meal(date="20261019"))
    await entered.wait()
    result = await asyncio.wait_for(service.get_meal(), 1)
    assert result["date"] == "20261029"
    release.set()
    await other


async def test_stale_cache_is_only_used_for_the_requested_date_and_meal(schedule):
    service, api, clock = schedule
    await service.warm()
    entry = service._weeks["20261026"]
    entry.expires_at = 0
    api.get_meal_week.side_effect = RuntimeError("offline")

    result = await service.get_meal()
    assert result["date"] == "20261029"
    await asyncio.gather(*service._inflight.values(), return_exceptions=True)

    entry.meals.pop(("20261029", "2"))
    clock[0] = clock[0].replace(hour=12)
    assert "error" in await service.get_meal()


async def test_expired_stale_limit_returns_an_error_instead_of_an_old_menu(schedule):
    service, api, _ = schedule
    await service.warm()
    service._weeks["20261026"].expires_at = 0
    service._weeks["20261026"].stale_until = 0
    api.get_meal_week.side_effect = RuntimeError("offline")
    assert "error" in await service.get_meal()


async def test_cancelled_request_does_not_cancel_the_shared_load(schedule):
    service, api, _ = schedule
    entered, release = asyncio.Event(), asyncio.Event()

    async def load(monday):
        entered.set()
        await release.wait()
        return week_data(monday)

    api.get_meal_week.side_effect = load
    first = asyncio.create_task(service.get_meal())
    await entered.wait()
    second = asyncio.create_task(service.get_meal())
    await asyncio.sleep(0)
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    release.set()
    assert (await second)["date"] == "20261029"
    assert api.get_meal_week.await_count == 1


async def test_unavailable_is_not_cached_as_no_meal_and_retries_are_throttled(schedule):
    service, api, _ = schedule
    api.get_meal_week.side_effect = RuntimeError("offline")
    results = await asyncio.gather(*(service.get_meal() for _ in range(8)))
    assert all("error" in result for result in results)
    assert "error" in await service.get_meal()
    assert api.get_meal_week.await_count == 1
    assert not service._weeks


async def test_confirmed_empty_week_is_a_no_meal_response(schedule):
    service, api, _ = schedule
    api.get_meal_week.side_effect = lambda monday: {"week_start": monday, "meals": []}
    result = await service.get_meal()
    assert result == {"title": "🍳 아침", "menu": "급식이 없습니다.", "cal_info": ""}


async def test_wrong_week_response_is_rejected(schedule):
    service, api, _ = schedule
    api.get_meal_week.side_effect = lambda _monday: week_data("20261019")
    assert "error" in await service.get_meal()
    assert not service._weeks


async def test_timeout_leaves_the_shared_refresh_running_for_the_next_request(
    schedule, monkeypatch
):
    import importlib

    module = importlib.import_module("src.services.MealScheduleService")
    monkeypatch.setattr(module, "_WAIT_TIMEOUT", 0.01)
    service, api, _ = schedule
    release = asyncio.Event()

    async def load(monday):
        await release.wait()
        return week_data(monday)

    api.get_meal_week.side_effect = load
    assert "error" in await service.get_meal()
    assert not service._inflight["20261026"].done()

    release.set()
    await asyncio.gather(*service._inflight.values())
    assert (await service.get_meal())["date"] == "20261029"
    assert api.get_meal_week.await_count == 1


async def test_failed_refresh_can_recover_without_restarting_the_bot(schedule):
    service, api, _ = schedule
    api.get_meal_week.side_effect = RuntimeError("offline")
    assert "error" in await service.get_meal()

    service._failed_until["20261026"] = 0
    api.get_meal_week.side_effect = week_data
    assert (await service.get_meal())["date"] == "20261029"
    assert api.get_meal_week.await_count == 2
