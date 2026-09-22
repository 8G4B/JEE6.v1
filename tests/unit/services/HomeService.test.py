import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from src.interfaces.commands.school.HomeCommand import HomeCommand
from src.services.HomeService import (
    HomeService,
    HomeStatus,
    SchoolScheduleService,
    StaleWhileRevalidateCache,
    TimetableService,
)
from src.utils.embeds.HomeEmbed import HomeEmbed

KST = ZoneInfo("Asia/Seoul")


def _service(holidays=None, error=None, periods=None, timetable_error=None):
    schedule = AsyncMock()
    if error:
        schedule.get_holidays.side_effect = error
    else:
        schedule.get_holidays.return_value = holidays or {}
    timetable = AsyncMock()
    if timetable_error:
        timetable.get_periods.side_effect = timetable_error
    else:
        timetable.get_periods.return_value = periods or {}
    return HomeService(schedule, timetable)


_FULL_DAY = frozenset(range(1, 8))
_NO_LAST_PERIOD = frozenset(range(1, 7))


@pytest.mark.asyncio
async def test_normal_week_counts_down_to_friday_at_1620():
    service = _service()
    now = datetime(2026, 8, 24, 9, 0, tzinfo=KST)  # Monday

    status = await service.get_status(now)

    assert status.state == "countdown"
    assert status.target == datetime(2026, 8, 28, 16, 20, tzinfo=KST)
    assert status.reason == "금요일"
    embed = HomeEmbed.create_home_embed(status)
    assert embed.description == "## 103시간 20분 0초 남았습니다"
    assert "4일" not in embed.description
    assert embed.footer.text == "하교 예정 · 8월 28일(금) 오후 4시 20분 · KST"
    assert all(field.name != "📅 하교 예정" for field in embed.fields)


@pytest.mark.asyncio
async def test_day_before_school_holiday_is_the_next_dismissal():
    holiday = date(2026, 8, 27)
    service = _service({holiday: "재량휴업일"})
    now = datetime(2026, 8, 24, 9, 0, tzinfo=KST)

    status = await service.get_status(now)

    assert status.target == datetime(2026, 8, 26, 16, 20, tzinfo=KST)
    assert status.reason == "재량휴업일 전날"


@pytest.mark.asyncio
async def test_dismissal_minute_and_time_after_dismissal_are_distinguished():
    service = _service()

    dismissal_time = await service.get_status(
        datetime(2026, 8, 28, 16, 20, 30, tzinfo=KST)
    )
    dismissed = await service.get_status(datetime(2026, 8, 28, 16, 21, tzinfo=KST))

    assert dismissal_time.state == "dismissal_time"
    assert dismissed.state == "dismissed"


@pytest.mark.asyncio
async def test_weekend_and_school_holiday_are_reported_as_days_off():
    weekend = await _service().get_status(datetime(2026, 8, 29, 12, 0, tzinfo=KST))
    holiday = await _service({date(2026, 8, 27): "재량휴업일"}).get_status(
        datetime(2026, 8, 27, 12, 0, tzinfo=KST)
    )

    assert weekend.state == "day_off"
    assert weekend.day_off_name == "주말"
    assert holiday.state == "day_off"
    assert holiday.day_off_name == "재량휴업일"


@pytest.mark.asyncio
async def test_schedule_failure_falls_back_to_friday_and_discloses_it():
    service = _service(error=RuntimeError("NEIS unavailable"))
    now = datetime(2026, 8, 24, 9, 0, tzinfo=KST)

    status = await service.get_status(now)
    embed = HomeEmbed.create_home_embed(status)

    assert status.target == datetime(2026, 8, 28, 16, 20, tzinfo=KST)
    assert status.schedule_available is False
    assert any("금요일 기준" in field.value for field in embed.fields)


def test_only_whole_school_holidays_are_parsed():
    rows = [
        {
            "AA_YMD": "20260924",
            "EVENT_NM": "추석연휴",
            "SBTR_DD_SC_NM": "공휴일",
            "ONE_GRADE_EVENT_YN": "Y",
            "TW_GRADE_EVENT_YN": "Y",
            "THREE_GRADE_EVENT_YN": "Y",
        },
        {
            "AA_YMD": "20260924",
            "EVENT_NM": "추석",
            "SBTR_DD_SC_NM": "공휴일",
            "ONE_GRADE_EVENT_YN": "Y",
            "TW_GRADE_EVENT_YN": "Y",
            "THREE_GRADE_EVENT_YN": "Y",
        },
        {
            "AA_YMD": "20260925",
            "EVENT_NM": "2학년 휴업",
            "SBTR_DD_SC_NM": "휴업일",
            "ONE_GRADE_EVENT_YN": "N",
            "TW_GRADE_EVENT_YN": "Y",
            "THREE_GRADE_EVENT_YN": "N",
        },
    ]

    holidays = SchoolScheduleService._parse_holidays(rows)

    assert holidays == {date(2026, 9, 24): "추석연휴 · 추석"}


def test_countdown_embed_always_shows_hours_minutes_and_seconds():
    target = datetime(2026, 8, 28, 16, 20, tzinfo=KST)
    status = HomeStatus(
        state="countdown",
        now=target - timedelta(hours=20, minutes=24, seconds=21, microseconds=500_000),
        target=target,
        reason="금요일",
    )

    description = HomeEmbed.create_home_embed(status).description
    assert description == "## 20시간 24분 22초 남았습니다"


@pytest.mark.asyncio
async def test_home_command_replies_with_an_embed():
    status = HomeStatus(
        state="countdown",
        now=datetime(2026, 8, 24, 9, 0, tzinfo=KST),
        target=datetime(2026, 8, 28, 16, 20, tzinfo=KST),
        reason="금요일",
    )
    command = HomeCommand(MagicMock(), MagicMock())
    command.home_service.get_status = AsyncMock(return_value=status)
    command._start_countdown = MagicMock()
    ctx = MagicMock()
    ctx.channel.id = 123
    message = MagicMock()
    ctx.reply = AsyncMock(return_value=message)

    await HomeCommand.home.callback(command, ctx)

    ctx.reply.assert_awaited_once()
    embed = ctx.reply.await_args.kwargs["embed"]
    assert embed.title == "🏠 하교까지"
    assert embed.description == "## 103시간 20분 0초 남았습니다"
    assert embed.footer.text.startswith("하교 예정 ·")
    command._start_countdown.assert_called_once_with(123, message, status)


@pytest.mark.asyncio
async def test_home_countdown_compensates_for_message_edit_latency():
    target = datetime(2026, 8, 28, 16, 20, tzinfo=KST)
    initial = HomeStatus(
        state="countdown",
        now=target - timedelta(hours=20, minutes=24, seconds=22),
        target=target,
        reason="금요일",
    )
    dismissal = HomeStatus(
        state="dismissal_time",
        now=target,
        target=target,
        reason="금요일",
    )
    command = HomeCommand(MagicMock(), MagicMock())
    command._now = MagicMock(side_effect=[initial.now + timedelta(seconds=1), target])
    command.home_service.get_status = AsyncMock(return_value=dismissal)
    clock = {"now": 0.0}
    loop = MagicMock()
    loop.time.side_effect = lambda: clock["now"]

    async def advance_clock(delay):
        clock["now"] += delay

    async def edit_message(**kwargs):
        clock["now"] += 0.2

    message = MagicMock()
    message.edit = AsyncMock(side_effect=edit_message)

    with patch(
        "src.interfaces.commands.school.HomeCommand.asyncio.sleep",
        new=AsyncMock(side_effect=advance_clock),
    ) as sleep, patch(
        "src.interfaces.commands.school.HomeCommand.asyncio.get_running_loop",
        return_value=loop,
    ):
        await command._update_countdown(message, initial)

    assert sleep.await_count == 2
    delays = [call.args[0] for call in sleep.await_args_list]
    assert delays == pytest.approx([1, 0.8])
    assert message.edit.await_count == 2
    first_embed = message.edit.await_args_list[0].kwargs["embed"]
    final_embed = message.edit.await_args_list[1].kwargs["embed"]
    assert first_embed.description == "## 20시간 24분 21초 남았습니다"
    assert final_embed.title == "🏠 지금 하교 시간이에요!"
    command.home_service.get_status.assert_awaited_once_with(target)


@pytest.mark.asyncio
async def test_free_last_period_moves_dismissal_one_hour_earlier():
    friday = date(2026, 8, 28)
    service = _service(periods={friday: _NO_LAST_PERIOD})

    status = await service.get_status(datetime(2026, 8, 24, 9, 0, tzinfo=KST))

    assert status.target == datetime(2026, 8, 28, 15, 20, tzinfo=KST)
    assert status.early_dismissal is True
    embed = HomeEmbed.create_home_embed(status)
    assert embed.footer.text == "하교 예정 · 8월 28일(금) 오후 3시 20분 · KST"
    assert embed.fields == []


@pytest.mark.asyncio
async def test_early_dismissal_state_changes_at_1520():
    friday = date(2026, 8, 28)
    service = _service(periods={friday: _NO_LAST_PERIOD})

    status = await service.get_status(datetime(2026, 8, 28, 15, 25, tzinfo=KST))

    assert status.state == "dismissed"
    embed = HomeEmbed.create_home_embed(status)
    assert "오후 3시 20분" in embed.description


@pytest.mark.asyncio
async def test_last_period_class_or_missing_timetable_keeps_1620():
    friday = date(2026, 8, 28)
    now = datetime(2026, 8, 24, 9, 0, tzinfo=KST)

    with_class = await _service(periods={friday: _FULL_DAY}).get_status(now)
    no_data = await _service(periods={}).get_status(now)
    failed = await _service(timetable_error=RuntimeError("down")).get_status(now)

    for status in (with_class, no_data, failed):
        assert status.target == datetime(2026, 8, 28, 16, 20, tzinfo=KST)
        assert status.early_dismissal is False


def test_timetable_rows_are_grouped_by_date_and_blank_subjects_ignored():
    rows = [
        {"ALL_TI_YMD": "20260918", "PERIO": "6", "ITRT_CNTNT": "자바 프로그래밍"},
        {"ALL_TI_YMD": "20260918", "PERIO": "7", "ITRT_CNTNT": " "},
        {"ALL_TI_YMD": "20260917", "PERIO": "7", "ITRT_CNTNT": "영어Ⅱ"},
        {"ALL_TI_YMD": "bad", "PERIO": "7", "ITRT_CNTNT": "영어Ⅱ"},
    ]

    periods = TimetableService._parse_periods(rows)

    assert periods == {
        date(2026, 9, 18): frozenset({6}),
        date(2026, 9, 17): frozenset({7}),
    }


@pytest.mark.asyncio
async def test_cache_serves_stale_value_immediately_and_refreshes_once():
    cache = StaleWhileRevalidateCache("test", ttl=0)
    release = asyncio.Event()
    calls = []

    async def loader():
        calls.append(1)
        if len(calls) > 1:
            await release.wait()
        return len(calls)

    assert await cache.get("k", loader) == 1
    # 만료된 값은 갱신을 기다리지 않고 바로 돌려준다.
    assert await cache.get("k", loader) == 1
    assert await cache.get("k", loader) == 1
    await asyncio.sleep(0)
    assert len(calls) == 2

    release.set()
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert await cache.get("k", loader) == 2


@pytest.mark.asyncio
async def test_cache_cold_miss_gives_up_after_timeout_but_keeps_loading():
    cache = StaleWhileRevalidateCache("test", ttl=60, wait_timeout=0.01)
    release = asyncio.Event()

    async def loader():
        await release.wait()
        return "value"

    with pytest.raises(asyncio.TimeoutError):
        await cache.get("k", loader)

    release.set()
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert await cache.get("k", AsyncMock(side_effect=AssertionError)) == "value"


@pytest.mark.asyncio
async def test_cache_failure_is_backed_off():
    cache = StaleWhileRevalidateCache("test", ttl=60, failure_ttl=60)
    loader = AsyncMock(side_effect=RuntimeError("down"))

    with pytest.raises(RuntimeError):
        await cache.get("k", loader)
    with pytest.raises(RuntimeError):
        await cache.get("k", loader)

    assert loader.await_count == 1
