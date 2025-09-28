import discord
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Tuple
from src.config.settings.slowSettings import SLOW_TIMES

logger = logging.getLogger(__name__)


class SlowModeService:
    def __init__(self):
        pass

    def is_slow_mode_active_time(self, dt: datetime = None) -> bool:
        if dt is None:
            dt = datetime.now(ZoneInfo("Asia/Seoul"))
        else:
            dt = dt.astimezone(ZoneInfo("Asia/Seoul"))

        weekday = dt.weekday()  # 0=월요일, 6=일요일

        if 0 <= weekday <= 3:
            return True

        if weekday == 4:
            hour = dt.hour
            minute = dt.minute
            if hour < 16 or (hour == 16 and minute < 30):
                return True

        return False

    def get_current_slow_period(self, dt: datetime = None) -> Optional[str]:
        if dt is None:
            dt = datetime.now(ZoneInfo("Asia/Seoul"))
        else:
            dt = dt.astimezone(ZoneInfo("Asia/Seoul"))

        hour = dt.hour
        minute = dt.minute

        for check_func, period in SLOW_TIMES:
            if check_func(hour, minute):
                return period

        return None

    async def apply_slow_mode(
        self, channel: discord.TextChannel, delay: int
    ) -> Tuple[bool, str]:
        try:
            if delay < 0:
                delay = 0
            elif delay > 21600:
                delay = 21600

            await channel.edit(slowmode_delay=delay)
            logger.info(f"슬로우 모드 적용: {channel.name} ({delay}초)")
            return True, f"슬로우 모드 적용됨 ({delay}초)"

        except discord.Forbidden:
            return False, "권한이 부족합니다."
        except Exception as e:
            logger.error(f"슬로우 모드 적용 중 오류: {e}")
            return False, str(e)

    async def remove_slow_mode(self, channel: discord.TextChannel) -> Tuple[bool, str]:
        try:
            await channel.edit(slowmode_delay=0)
            return True, "슬로우 모드 제거됨"

        except discord.Forbidden:
            logger.error(f"슬로우 모드 제거 권한 부족: {channel.name}")
            return False, "권한이 부족합니다."
        except Exception as e:
            logger.error(f"슬로우 모드 제거 중 오류: {e}")
            return False, str(e)

    def get_period_name(self, period: str) -> str:
        period_names = {
            "1": "1교시",
            "2": "2교시",
            "3": "3교시",
            "4": "4교시",
            "5": "5교시",
            "6": "6교시",
            "7": "7교시",
            "8": "8교시",
            "9": "9교시",
            "10": "10교시",
            "11": "11교시",
        }
        return period_names.get(period, f"{period}교시")
