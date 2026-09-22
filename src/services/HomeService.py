import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timedelta
from typing import Awaitable, Callable, Generic, Hashable, Literal, Optional, TypeVar
from zoneinfo import ZoneInfo

import aiohttp

from src.clients.HttpClient import get_http_session

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
DISMISSAL_TIME = datetime_time(hour=16, minute=20)
# 마지막 교시(7교시)가 공강이면 6교시 끝나고 바로 종례하므로 한 시간 당겨진다.
EARLY_DISMISSAL_TIME = datetime_time(hour=15, minute=20)
LAST_PERIOD = 7
_HOLIDAY_TYPES = {"공휴일", "휴업일"}
_GRADE_FLAGS = (
    "ONE_GRADE_EVENT_YN",
    "TW_GRADE_EVENT_YN",
    "THREE_GRADE_EVENT_YN",
)
_FETCH_ERRORS = (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError, ValueError)

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


@dataclass(frozen=True)
class HomeStatus:
    state: Literal["countdown", "dismissal_time", "dismissed", "day_off"]
    now: datetime
    target: Optional[datetime] = None
    reason: str = ""
    day_off_name: str = ""
    schedule_available: bool = True
    early_dismissal: bool = False


class StaleWhileRevalidateCache(Generic[K, V]):
    def __init__(
        self,
        name: str,
        ttl: float,
        failure_ttl: float = 30,
        wait_timeout: float = 3,
    ) -> None:
        self.name = name
        self.ttl = ttl
        self.failure_ttl = failure_ttl
        self.wait_timeout = wait_timeout
        self._values: dict[K, tuple[float, V]] = {}
        self._failed_until: dict[K, float] = {}
        self._inflight: dict[K, asyncio.Task] = {}

    async def get(self, key: K, loader: Callable[[], Awaitable[V]]) -> V:
        now = time.monotonic()
        entry = self._values.get(key)
        if entry is not None:
            if now >= entry[0] and now >= self._failed_until.get(key, 0):
                self._refresh(key, loader)
            return entry[1]

        if now < self._failed_until.get(key, 0):
            raise RuntimeError(f"{self.name} 조회가 최근 실패했습니다.")

        task = self._refresh(key, loader)
        return await asyncio.wait_for(asyncio.shield(task), self.wait_timeout)

    def _refresh(self, key: K, loader: Callable[[], Awaitable[V]]) -> asyncio.Task:
        task = self._inflight.get(key)
        if task is None:
            task = asyncio.create_task(self._load(key, loader), name=f"{self.name}-{key}")
            task.add_done_callback(lambda done: done.cancelled() or done.exception())
            self._inflight[key] = task
        return task

    async def _load(self, key: K, loader: Callable[[], Awaitable[V]]) -> V:
        try:
            value = await loader()
        except BaseException:
            self._failed_until[key] = time.monotonic() + self.failure_ttl
            if key in self._values:
                logger.warning("%s 갱신 실패, 이전 값을 유지합니다.", self.name, exc_info=True)
            raise
        else:
            self._values[key] = (time.monotonic() + self.ttl, value)
            self._failed_until.pop(key, None)
            self._prune(key)
            return value
        finally:
            self._inflight.pop(key, None)

    def _prune(self, current: K) -> None:
        while len(self._values) > 4:
            oldest = next(key for key in self._values if key != current)
            self._values.pop(oldest)


def _week_bounds(day: date) -> tuple[date, date]:
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=4)


def _date_range(start: date, end: date):
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)


class _NeisClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("NEIS_API_KEY") or os.getenv("MEAL_API_KEY", "")
        self.education_office_code = os.getenv("ATPT_OFCDC_SC_CODE", "F10")
        # 2026년 NEIS 학교 코드. 배포 환경에서는 환경 변수로 덮어쓸 수 있다.
        self.school_code = os.getenv("SD_SCHUL_CODE", "7140392")
        self._timeout = aiohttp.ClientTimeout(total=8, connect=3, sock_read=5)

    async def request_rows(
        self,
        service: str,
        params: dict,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[dict], int]:
        query = {
            "Type": "json",
            "pIndex": page,
            "pSize": page_size,
            "ATPT_OFCDC_SC_CODE": self.education_office_code,
            "SD_SCHUL_CODE": self.school_code,
            **params,
        }
        if self.api_key:
            query["KEY"] = self.api_key

        session = await get_http_session()
        async with session.get(
            f"https://open.neis.go.kr/hub/{service}",
            params=query,
            timeout=self._timeout,
        ) as response:
            response.raise_for_status()
            data = await response.json(content_type=None)

        result = data.get("RESULT")
        if result:
            if result.get("CODE") == "INFO-200":
                return [], 0
            raise RuntimeError(result.get("MESSAGE", f"NEIS {service} 조회 실패"))

        body = data.get(service)
        if not body or len(body) < 2:
            raise RuntimeError(f"NEIS {service} 응답 형식이 올바르지 않습니다.")

        head = body[0].get("head", [])
        total_count = next(
            (item["list_total_count"] for item in head if "list_total_count" in item),
            0,
        )
        return body[1].get("row", []), int(total_count)


class SchoolScheduleService(_NeisClient):

    def __init__(self) -> None:
        super().__init__()
        self._cache: StaleWhileRevalidateCache[date, dict[date, str]] = (
            StaleWhileRevalidateCache("학사일정", ttl=6 * 60 * 60)
        )

    async def get_holidays(self, day: date) -> dict[date, str]:
        monday, friday = _week_bounds(day)
        return await self._cache.get(monday, lambda: self._fetch(monday, friday))

    async def _fetch(self, start: date, end: date) -> dict[date, str]:
        rows, total_count = await self._request(start, end)
        if total_count > len(rows):
            results = await asyncio.gather(
                *(self._request(day, day) for day in _date_range(start, end))
            )
            rows = [row for day_rows, _ in results for row in day_rows]
        return self._parse_holidays(rows)

    async def _request(self, start: date, end: date) -> tuple[list[dict], int]:
        return await self.request_rows(
            "SchoolSchedule",
            {
                "AA_FROM_YMD": start.strftime("%Y%m%d"),
                "AA_TO_YMD": end.strftime("%Y%m%d"),
            },
        )

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


class TimetableService(_NeisClient):
    page_size = 1000

    def __init__(self) -> None:
        super().__init__()
        self.grade = os.getenv("HOME_GRADE", "").strip()
        self.class_name = os.getenv("HOME_CLASS_NM", "").strip()
        self._cache: StaleWhileRevalidateCache[date, dict[date, frozenset[int]]] = (
            StaleWhileRevalidateCache("시간표", ttl=30 * 60)
        )
        self._warned_missing_key = False

    async def get_periods(self, day: date) -> dict[date, frozenset[int]]:
        if not self.api_key:
            if not self._warned_missing_key:
                logger.warning("NEIS_API_KEY가 없어 7교시 공강 여부를 확인하지 않습니다.")
                self._warned_missing_key = True
            return {}

        monday, friday = _week_bounds(day)
        return await self._cache.get(monday, lambda: self._fetch(monday, friday))

    async def _fetch(self, start: date, end: date) -> dict[date, frozenset[int]]:
        rows, total_count = await self._request(start, end, 1)
        if total_count > len(rows):
            pages = -(-total_count // self.page_size)
            results = await asyncio.gather(
                *(self._request(start, end, page) for page in range(2, pages + 1))
            )
            rows += [row for page_rows, _ in results for row in page_rows]
        return self._parse_periods(rows)

    async def _request(self, start: date, end: date, page: int):
        params = {
            "TI_FROM_YMD": start.strftime("%Y%m%d"),
            "TI_TO_YMD": end.strftime("%Y%m%d"),
        }
        if self.grade:
            params["GRADE"] = self.grade
        if self.class_name:
            params["CLASS_NM"] = self.class_name
        return await self.request_rows(
            "hisTimetable", params, page=page, page_size=self.page_size
        )

    @staticmethod
    def _parse_periods(rows: list[dict]) -> dict[date, frozenset[int]]:
        periods_by_date: dict[date, set[int]] = {}

        for row in rows:
            if not (row.get("ITRT_CNTNT") or "").strip():
                continue
            try:
                day = datetime.strptime(row["ALL_TI_YMD"], "%Y%m%d").date()
                period = int(row["PERIO"])
            except (KeyError, TypeError, ValueError):
                continue
            periods_by_date.setdefault(day, set()).add(period)

        return {day: frozenset(periods) for day, periods in periods_by_date.items()}


class HomeService:
    def __init__(
        self,
        schedule_service: Optional[SchoolScheduleService] = None,
        timetable_service: Optional[TimetableService] = None,
    ):
        self.schedule_service = schedule_service or SchoolScheduleService()
        self.timetable_service = timetable_service or TimetableService()

    async def warm_up(self, now: Optional[datetime] = None) -> None:
        day = self._as_kst(now or datetime.now(KST)).date()
        if day.weekday() >= 5:
            day += timedelta(days=7 - day.weekday())
        await asyncio.gather(
            self.schedule_service.get_holidays(day),
            self.timetable_service.get_periods(day),
            return_exceptions=True,
        )

    async def get_status(self, now: Optional[datetime] = None) -> HomeStatus:
        current = self._as_kst(now or datetime.now(KST))

        if current.weekday() >= 5:
            return HomeStatus(
                state="day_off",
                now=current,
                day_off_name="주말",
            )

        friday = _week_bounds(current.date())[1]
        holidays_result, periods_result = await asyncio.gather(
            self.schedule_service.get_holidays(current.date()),
            self.timetable_service.get_periods(current.date()),
            return_exceptions=True,
        )

        schedule_available = True
        if isinstance(holidays_result, BaseException):
            self._raise_unexpected(holidays_result)
            logger.warning(
                "학사일정 조회 실패, 금요일 기준으로 계산합니다.",
                exc_info=holidays_result,
            )
            holidays: dict[date, str] = {}
            schedule_available = False
        else:
            holidays = holidays_result

        if isinstance(periods_result, BaseException):
            self._raise_unexpected(periods_result)
            logger.warning(
                "시간표 조회 실패, 7교시가 있다고 보고 계산합니다.",
                exc_info=periods_result,
            )
            periods: dict[date, frozenset[int]] = {}
        else:
            periods = periods_result

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

        for day in _date_range(current.date(), friday):
            if day.weekday() >= 5 or day in holidays:
                continue

            next_holiday = holidays.get(day + timedelta(days=1))
            if day.weekday() != 4 and not next_holiday:
                continue

            day_periods = periods.get(day)
            early = bool(day_periods) and LAST_PERIOD not in day_periods
            target = datetime.combine(
                day,
                EARLY_DISMISSAL_TIME if early else DISMISSAL_TIME,
                tzinfo=KST,
            )
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
                    early_dismissal=early,
                )

            return HomeStatus(
                state="countdown",
                now=current,
                target=target,
                reason=reason,
                schedule_available=schedule_available,
                early_dismissal=early,
            )

        # 금요일이 휴일인 경우에는 그 전날이 이미 후보가 되므로 정상적으로는 도달하지 않는다.
        raise RuntimeError("다음 하교일을 계산할 수 없습니다.")

    @staticmethod
    def _raise_unexpected(error: BaseException) -> None:
        if not isinstance(error, _FETCH_ERRORS):
            raise error

    @staticmethod
    def _as_kst(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=KST)
        return value.astimezone(KST)
