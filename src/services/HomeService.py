import asyncio
import logging
import math
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timedelta
from typing import Literal, Optional
from zoneinfo import ZoneInfo

import aiohttp

from src.clients.HttpClient import get_http_session

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
DISMISSAL_TIME = datetime_time(hour=16, minute=20)
_WEEKDAY_NAMES = ("월", "화", "수", "목", "금", "토", "일")
_HOLIDAY_TYPES = {"공휴일", "휴업일"}
_GRADE_FLAGS = (
    "ONE_GRADE_EVENT_YN",
    "TW_GRADE_EVENT_YN",
    "THREE_GRADE_EVENT_YN",
)


@dataclass(frozen=True)
class HomeStatus:
    state: Literal["countdown", "dismissal_time", "dismissed", "day_off"]
    now: datetime
    target: Optional[datetime] = None
    reason: str = ""
    day_off_name: str = ""
    schedule_available: bool = True


class SchoolScheduleService:
    """NEIS 학사일정에서 학교 전체 휴일을 조회하고 짧게 캐시한다."""

    base_url = "https://open.neis.go.kr/hub/SchoolSchedule"
    cache_ttl = 6 * 60 * 60

    def __init__(self) -> None:
        self.api_key = os.getenv("NEIS_API_KEY") or os.getenv("MEAL_API_KEY", "")
        self.education_office_code = os.getenv("ATPT_OFCDC_SC_CODE", "F10")
        # 2026년 NEIS 학교 코드. 배포 환경에서는 환경 변수로 덮어쓸 수 있다.
        self.school_code = os.getenv("SD_SCHUL_CODE", "7140392")
        self._cache: dict[tuple[date, date], tuple[float, dict[date, str]]] = {}
        self._cache_lock = asyncio.Lock()
        self._timeout = aiohttp.ClientTimeout(total=8, connect=3, sock_read=5)

    async def get_holidays(self, start: date, end: date) -> dict[date, str]:
        key = (start, end)
        cached = self._cache.get(key)
        if cached is not None and time.monotonic() < cached[0]:
            return cached[1]

        async with self._cache_lock:
            cached = self._cache.get(key)
            if cached is not None and time.monotonic() < cached[0]:
                return cached[1]

            rows, total_count = await self._request_rows(start, end)
            if total_count > len(rows):
                # 인증키가 없으면 한 번에 5건만 내려올 수 있다. 조회 범위가 최대
                # 한 주이므로 날짜별 요청을 병렬로 보내 누락을 막는다.
                results = await asyncio.gather(
                    *(
                        self._request_rows(day, day)
                        for day in self._date_range(start, end)
                    )
                )
                rows = [row for day_rows, _ in results for row in day_rows]

            holidays = self._parse_holidays(rows)
            self._cache[key] = (time.monotonic() + self.cache_ttl, holidays)
            return holidays

    async def _request_rows(self, start: date, end: date) -> tuple[list[dict], int]:
        params = {
            "Type": "json",
            "pIndex": 1,
            "pSize": 100,
            "ATPT_OFCDC_SC_CODE": self.education_office_code,
            "SD_SCHUL_CODE": self.school_code,
            "AA_FROM_YMD": start.strftime("%Y%m%d"),
            "AA_TO_YMD": end.strftime("%Y%m%d"),
        }
        if self.api_key:
            params["KEY"] = self.api_key

        session = await get_http_session()
        async with session.get(
            self.base_url,
            params=params,
            timeout=self._timeout,
        ) as response:
            response.raise_for_status()
            data = await response.json(content_type=None)

        result = data.get("RESULT")
        if result:
            if result.get("CODE") == "INFO-200":
                return [], 0
            raise RuntimeError(result.get("MESSAGE", "NEIS 학사일정 조회 실패"))

        schedule = data.get("SchoolSchedule")
        if not schedule or len(schedule) < 2:
            raise RuntimeError("NEIS 학사일정 응답 형식이 올바르지 않습니다.")

        head = schedule[0].get("head", [])
        total_count = next(
            (item["list_total_count"] for item in head if "list_total_count" in item),
            0,
        )
        return schedule[1].get("row", []), int(total_count)

    @staticmethod
    def _date_range(start: date, end: date):
        for offset in range((end - start).days + 1):
            yield start + timedelta(days=offset)

    @staticmethod
    def _parse_holidays(rows: list[dict]) -> dict[date, str]:
        names_by_date: dict[date, list[str]] = {}

        for row in rows:
            if row.get("SBTR_DD_SC_NM") not in _HOLIDAY_TYPES:
                continue
            if not all(row.get(flag) == "Y" for flag in _GRADE_FLAGS):
                continue

            try:
                event_date = datetime.strptime(row["AA_YMD"], "%Y%m%d").date()
            except (KeyError, TypeError, ValueError):
                continue

            event_name = (row.get("EVENT_NM") or "휴일").strip()
            names = names_by_date.setdefault(event_date, [])
            if event_name not in names:
                names.append(event_name)

        return {
            event_date: " · ".join(names) for event_date, names in names_by_date.items()
        }


class HomeService:
    def __init__(self, schedule_service: Optional[SchoolScheduleService] = None):
        self.schedule_service = schedule_service or SchoolScheduleService()

    async def get_status(self, now: Optional[datetime] = None) -> HomeStatus:
        current = self._as_kst(now or datetime.now(KST))

        if current.weekday() >= 5:
            return HomeStatus(
                state="day_off",
                now=current,
                day_off_name="주말",
            )

        friday = current.date() + timedelta(days=(4 - current.weekday()) % 7)
        schedule_available = True
        try:
            holidays = await self.schedule_service.get_holidays(current.date(), friday)
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError, ValueError):
            logger.warning(
                "학사일정 조회 실패, 금요일 기준으로 계산합니다.", exc_info=True
            )
            holidays = {}
            schedule_available = False

        # 네트워크 조회 중에도 초 단위 카운트다운이 오래된 값이 되지 않게 다시 읽는다.
        if now is None:
            current = datetime.now(KST)

        today_holiday = holidays.get(current.date())
        if today_holiday:
            return HomeStatus(
                state="day_off",
                now=current,
                day_off_name=today_holiday,
                schedule_available=schedule_available,
            )

        for day in self._date_range(current.date(), friday):
            if day.weekday() >= 5 or day in holidays:
                continue

            next_holiday = holidays.get(day + timedelta(days=1))
            if day.weekday() != 4 and not next_holiday:
                continue

            target = datetime.combine(day, DISMISSAL_TIME, tzinfo=KST)
            reason = "금요일" if day.weekday() == 4 else f"{next_holiday} 전날"

            if day == current.date() and current >= target:
                state = (
                    "dismissal_time"
                    if current < target + timedelta(minutes=1)
                    else "dismissed"
                )
                return HomeStatus(
                    state=state,
                    now=current,
                    target=target,
                    reason=reason,
                    schedule_available=schedule_available,
                )

            return HomeStatus(
                state="countdown",
                now=current,
                target=target,
                reason=reason,
                schedule_available=schedule_available,
            )

        # 금요일이 휴일인 경우에는 그 전날이 이미 후보가 되므로 정상적으로는 도달하지 않는다.
        raise RuntimeError("다음 하교일을 계산할 수 없습니다.")

    @staticmethod
    def _as_kst(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=KST)
        return value.astimezone(KST)

    @staticmethod
    def _date_range(start: date, end: date):
        for offset in range((end - start).days + 1):
            yield start + timedelta(days=offset)


def format_home_status(status: HomeStatus) -> str:
    if status.state == "day_off":
        return f"🏠 오늘은 {status.day_off_name}이라 쉬는 날이에요!"
    if status.state == "dismissal_time":
        return "🏠 지금 하교 시간이에요!"
    if status.state == "dismissed":
        return "🏠 오늘 하교 시간(16:20)이 이미 지났어요!"

    if status.target is None:
        raise ValueError("카운트다운 상태에는 하교 시각이 필요합니다.")

    remaining_seconds = max(
        0,
        math.ceil((status.target - status.now).total_seconds()),
    )
    duration = _format_duration(remaining_seconds)
    target = status.target
    message = (
        f"🏠 하교까지 **{duration}** 남았어요!\n"
        f"하교 예정: **{target.month}월 {target.day}일"
        f"({_WEEKDAY_NAMES[target.weekday()]}) 16:20** ({status.reason})"
    )
    if not status.schedule_available:
        message += "\n※ 학사일정을 확인하지 못해 금요일 기준으로 계산했어요."
    return message


def _format_duration(total_seconds: int) -> str:
    days, remainder = divmod(total_seconds, 24 * 60 * 60)
    hours, remainder = divmod(remainder, 60 * 60)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}일")
    if hours:
        parts.append(f"{hours}시간")
    if minutes:
        parts.append(f"{minutes}분")
    if seconds or not parts:
        parts.append(f"{seconds}초")
    return " ".join(parts)
