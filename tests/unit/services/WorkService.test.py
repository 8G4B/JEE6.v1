from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from src.interfaces.commands.school.WorkCommand import WorkCommand
from src.services.WorkService import WorkService, WorkStatus
from src.utils.embeds.WorkEmbed import WorkEmbed

KST = ZoneInfo("Asia/Seoul")


def test_regular_countdown_targets_1630_today():
    now = datetime(2026, 9, 2, 9, 0, tzinfo=KST)

    status = WorkService().get_status("regular", now)

    assert status.state == "countdown"
    assert status.target == datetime(2026, 9, 2, 16, 30, tzinfo=KST)
    embed = WorkEmbed.create_work_embed(status)
    assert embed.title == "🎉 퇴근까지"
    assert embed.description == "## 7시간 30분 0초 남았습니다"
    assert embed.footer.text == ("퇴근 예정 · 9월 2일(수) 오후 4시 30분 · KST")


def test_regular_countdown_uses_tomorrow_after_1630_every_day():
    friday_after_work = datetime(2026, 9, 4, 16, 31, tzinfo=KST)

    status = WorkService().get_status("regular", friday_after_work)

    assert status.state == "countdown"
    assert status.target == datetime(2026, 9, 5, 16, 30, tzinfo=KST)


def test_overtime_countdown_targets_2130():
    now = datetime(2026, 9, 2, 20, 0, tzinfo=KST)

    status = WorkService().get_status("overtime", now)

    assert status.target == datetime(2026, 9, 2, 21, 30, tzinfo=KST)
    embed = WorkEmbed.create_work_embed(status)
    assert embed.title == "🌙 야근 종료까지"
    assert embed.description == "## 1시간 30분 0초 남았습니다"
    assert embed.footer.text == ("야근 종료 예정 · 9월 2일(수) 오후 9시 30분 · KST")


@pytest.mark.parametrize(
    ("mode", "hour", "title"),
    [
        ("regular", 16, "🎉 지금 퇴근 시간이에요!"),
        ("overtime", 21, "🌙 야근이 끝났어요!"),
    ],
)
def test_target_minute_is_reported_as_completion(mode, hour, title):
    now = datetime(2026, 9, 2, hour, 30, 30, tzinfo=KST)

    status = WorkService().get_status(mode, now)

    assert status.state == "target_time"
    assert WorkEmbed.create_work_embed(status).title == title


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback", "mode"),
    [
        (WorkCommand.leave_work, "regular"),
        (WorkCommand.overtime, "overtime"),
    ],
)
async def test_commands_use_their_daily_target(callback, mode):
    command = WorkCommand(MagicMock(), MagicMock())
    command._reply = AsyncMock()

    await callback.callback(command, MagicMock())

    command._reply.assert_awaited_once()
    assert command._reply.call_args.args[1] == mode


@pytest.mark.asyncio
async def test_work_countdown_compensates_for_message_edit_latency():
    target = datetime(2026, 9, 2, 16, 30, tzinfo=KST)
    initial = WorkStatus(
        mode="regular",
        state="countdown",
        now=target - timedelta(seconds=2),
        target=target,
    )
    completed = WorkStatus(
        mode="regular",
        state="target_time",
        now=target,
        target=target,
    )
    command = WorkCommand(MagicMock(), MagicMock())
    command._now = MagicMock(side_effect=[target - timedelta(seconds=1), target])
    command.work_service.get_status = MagicMock(return_value=completed)
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
        "src.interfaces.commands.school.WorkCommand.asyncio.sleep",
        side_effect=advance_clock,
    ) as sleep:
        with patch(
            "src.interfaces.commands.school.WorkCommand.asyncio.get_running_loop",
            return_value=loop,
        ):
            await command._update_countdown(message, initial)

    assert sleep.await_count == 2
    delays = [call.args[0] for call in sleep.await_args_list]
    assert delays == pytest.approx([1, 0.8])
    assert message.edit.await_count == 2
    assert message.edit.await_args_list[0].kwargs["embed"].description == (
        "## 0시간 0분 1초 남았습니다"
    )
    assert message.edit.await_args_list[1].kwargs["embed"].title == (
        "🎉 지금 퇴근 시간이에요!"
    )
