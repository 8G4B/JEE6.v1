from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from src.interfaces.commands.school.HomeCommand import HomeCommand
from src.services.HomeService import HomeService, HomeStatus, SchoolScheduleService
from src.utils.embeds.HomeEmbed import HomeEmbed

KST = ZoneInfo("Asia/Seoul")


def _service(holidays=None, error=None):
    schedule = AsyncMock()
    if error:
        schedule.get_holidays.side_effect = error
    else:
        schedule.get_holidays.return_value = holidays or {}
    return HomeService(schedule)


@pytest.mark.asyncio
async def test_normal_week_counts_down_to_friday_at_1620():
    service = _service()
    now = datetime(2026, 8, 24, 9, 0, tzinfo=KST)  # Monday

    status = await service.get_status(now)

    assert status.state == "countdown"
    assert status.target == datetime(2026, 8, 28, 16, 20, tzinfo=KST)
    assert status.reason == "금요일"
    embed = HomeEmbed.create_home_embed(status)
    assert "103시간 20분" in embed.description
    assert "4일" not in embed.description


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


def test_countdown_embed_uses_ceiling_for_partial_seconds():
    status = HomeStatus(
        state="countdown",
        now=datetime(2026, 8, 28, 16, 19, 59, 500_000, tzinfo=KST),
        target=datetime(2026, 8, 28, 16, 20, tzinfo=KST),
        reason="금요일",
    )

    assert "1초" in HomeEmbed.create_home_embed(status).description


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
    ctx = MagicMock()
    ctx.reply = AsyncMock()

    await HomeCommand.home.callback(command, ctx)

    ctx.reply.assert_awaited_once()
    embed = ctx.reply.await_args.kwargs["embed"]
    assert embed.title == "🏠 하교 카운트다운"
    assert "103시간 20분" in embed.description
