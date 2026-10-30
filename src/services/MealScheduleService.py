import asyncio
import logging
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from src.clients.ApiGatewayClient import ApiGatewayClient


logger = logging.getLogger(__name__)
_SEOUL = ZoneInfo("Asia/Seoul")
_NO_MEAL = "급식이 없습니다."
_UNAVAILABLE = "급식 정보를 불러오지 못했어요. 잠시 후 다시 시도해주세요."
_MEAL_NAMES = {"1": "🍳 아침", "2": "🍚 점심", "3": "🍖 저녁"}
_MEAL_CODES = {"breakfast": "1", "lunch": "2", "dinner": "3"}
_CACHE_TTL = 300
_EMPTY_TTL = 60
_MAX_STALE = 24 * 3600
_RETRY_INTERVAL = 15
_WAIT_TIMEOUT = 3
_MAX_WEEKS = 8
_REFRESH_AHEAD = 30


@dataclass
class _Week:
    expires_at: float
    stale_until: float
    meals: dict[tuple[str, str], dict]


class MealScheduleService:
    """Keep dated menus locally; select the current meal at request time."""

    def __init__(
        self,
        api: ApiGatewayClient,
        now: Optional[Callable[[], datetime]] = None,
        cache_path: Optional[str] = None,
    ):
        self.api = api
        self._now = now or (lambda: datetime.now(_SEOUL))
        self._weeks: OrderedDict[str, _Week] = OrderedDict()
        self._inflight: dict[str, asyncio.Task] = {}
        self._failed_until: dict[str, float] = {}
        self._primary = None
        self._cache_path = Path(cache_path) if cache_path else None
        self._persist_task: Optional[asyncio.Task] = None
        self._persist_dirty = False

    @staticmethod
    def _decode_meals(monday: str, rows: list) -> dict:
        end = (datetime.strptime(monday, "%Y%m%d") + timedelta(days=6)).strftime(
            "%Y%m%d"
        )
        if not isinstance(rows, list):
            raise ValueError("주간 급식 목록이 없습니다.")
        meals = {}
        for row in rows:
            date, code, menu = (
                row.get("date", ""),
                row.get("meal_code"),
                row.get("menu"),
            )
            if not (monday <= date <= end and code in _MEAL_NAMES and menu):
                raise ValueError("주간 급식 항목을 확인할 수 없습니다.")
            meals[(date, code)] = row
        return meals

    async def restore(self) -> None:
        """Restore dated data before connecting to Discord, without blocking its loop."""
        if self._cache_path is None:
            return
        try:
            raw = await asyncio.to_thread(self._cache_path.read_text, encoding="utf-8")
            stored = json.loads(raw)
            if stored.get("version") != 1 or stored.get("source") != self.api.base_url:
                return
            clock, wall = time.monotonic(), time.time()
            for monday, week in list(stored["weeks"].items())[-_MAX_WEEKS:]:
                age = wall - week["saved_at"]
                if not 0 <= age < _MAX_STALE:
                    continue
                meals = self._decode_meals(monday, week["meals"])
                ttl = _CACHE_TTL if meals else _EMPTY_TTL
                # An expired negative result must be confirmed again.
                if not meals and age >= ttl:
                    continue
                self._weeks[monday] = _Week(
                    clock + ttl - age, clock + _MAX_STALE - age, meals
                )
        except FileNotFoundError:
            pass
        except Exception:
            logger.warning("저장된 급식 캐시 복원 실패", exc_info=True)

    def _schedule_persist(self) -> None:
        if self._cache_path is None:
            return
        self._persist_dirty = True
        if self._persist_task is None or self._persist_task.done():
            self._persist_task = asyncio.create_task(
                self._persist(), name="meal-cache-save"
            )

    async def _persist(self) -> None:
        while self._persist_dirty:
            self._persist_dirty = False
            clock, wall = time.monotonic(), time.time()
            snapshot = {
                "version": 1,
                "source": self.api.base_url,
                "weeks": {
                    monday: {
                        "saved_at": wall - (_MAX_STALE - (entry.stale_until - clock)),
                        "meals": list(entry.meals.values()),
                    }
                    for monday, entry in self._weeks.items()
                    if clock < entry.stale_until
                },
            }
            try:
                await asyncio.to_thread(self._write_snapshot, snapshot)
            except Exception:
                logger.warning("급식 캐시 저장 실패", exc_info=True)

    def _write_snapshot(self, snapshot: dict) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._cache_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self._cache_path)

    @staticmethod
    def _week_start(target: datetime) -> str:
        return (target - timedelta(days=target.weekday())).strftime("%Y%m%d")

    def _refresh(self, monday: str) -> Optional[asyncio.Task]:
        task = self._inflight.get(monday)
        if task is None and time.monotonic() >= self._failed_until.get(monday, 0):
            task = asyncio.create_task(
                self._load_week(monday), name=f"meal-week-{monday}"
            )
            self._inflight[monday] = task
            task.add_done_callback(lambda done: done.cancelled() or done.exception())
        return task

    async def _load_week(self, monday: str) -> _Week:
        try:
            data = await self.api.get_meal_week(monday)
            if data.get("error") or data.get("week_start") != monday:
                raise ValueError("주간 급식 응답을 확인할 수 없습니다.")
            meals = self._decode_meals(monday, data.get("meals"))
            now = time.monotonic()
            entry = _Week(
                expires_at=now + (_CACHE_TTL if meals else _EMPTY_TTL),
                stale_until=now + _MAX_STALE,
                meals=meals,
            )
            self._weeks[monday] = entry
            self._primary = None
            self._weeks.move_to_end(monday)
            while len(self._weeks) > _MAX_WEEKS:
                self._weeks.popitem(last=False)
            self._failed_until.pop(monday, None)
            self._schedule_persist()
            return entry
        except Exception:
            self._failed_until[monday] = time.monotonic() + _RETRY_INTERVAL
            logger.warning("주간 급식 갱신 실패 (%s)", monday, exc_info=True)
            raise
        finally:
            self._inflight.pop(monday, None)

    async def _wait_for_week(self, monday: str) -> _Week:
        task = self._refresh(monday)
        if task is None:
            raise RuntimeError("급식 조회가 최근 실패했습니다.")
        # One user's timeout/cancellation must not cancel the shared refresh.
        return await asyncio.wait_for(asyncio.shield(task), _WAIT_TIMEOUT)

    async def warm(self) -> None:
        current = self._now().astimezone(_SEOUL)
        weeks = [
            self._week_start(current),
            self._week_start(current + timedelta(days=7)),
        ]
        now = time.monotonic()
        await asyncio.gather(
            *(
                self._wait_for_week(monday)
                for monday in weeks
                if monday not in self._weeks
                or now >= self._weeks[monday].expires_at - _REFRESH_AHEAD
            ),
            return_exceptions=True,
        )

    async def close(self) -> None:
        tasks = list(self._inflight.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self._persist_task is not None:
            await self._persist_task

    async def get_meal(
        self, meal_type: str = "auto", day: str = "today", date: Optional[str] = None
    ) -> dict:
        if meal_type not in ("auto", *_MEAL_CODES) or day not in ("today", "tomorrow"):
            return {"error": "올바르지 않은 급식 조회 옵션이에요."}
        now = self._now().astimezone(_SEOUL)
        primary = meal_type == "auto" and day == "today" and date is None
        if primary and self._primary is not None:
            start, end, expires, result = self._primary
            if start <= now < end and time.monotonic() < expires:
                return result.copy()
        target = now + timedelta(days=day == "tomorrow")
        if date is not None:
            try:
                target = datetime.strptime(date, "%Y%m%d").replace(tzinfo=_SEOUL)
            except ValueError:
                return {"error": "올바르지 않은 날짜예요."}
            if target.year != now.year:
                return {"error": f"올해({now.year}년) 날짜만 조회할 수 있어요."}

        if meal_type == "auto":
            minutes = now.hour * 60 + now.minute
            code = "1" if minutes < 450 else "2" if minutes < 750 else "3"
            if date is None and day == "tomorrow":
                code = "1"
            elif minutes >= 1110:
                code = "1"
                if date is None:
                    target = now + timedelta(days=1)
        else:
            code = _MEAL_CODES[meal_type]

        title = _MEAL_NAMES[code]
        if date is not None:
            title = f"{title} ({target.month}/{target.day})"
        elif target.date() > now.date():
            title = title.replace(" ", " 내일 ", 1)

        date_str = target.strftime("%Y%m%d")
        monday = self._week_start(target)
        key = (date_str, code)
        cached = self._weeks.get(monday)
        clock = time.monotonic()
        if cached is not None and clock < cached.expires_at:
            entry = cached
        elif cached is not None and key in cached.meals and clock < cached.stale_until:
            self._refresh(monday)
            entry = cached
        else:
            try:
                entry = await self._wait_for_week(monday)
            except Exception:
                return {"error": _UNAVAILABLE}

        row = entry.meals.get(key)
        result = (
            {"title": title, "menu": _NO_MEAL, "cal_info": ""}
            if row is None
            else {
                "title": title,
                "menu": row["menu"],
                "cal_info": row.get("cal_info", ""),
                "date": date_str,
                "meal_code": code,
            }
        )
        if primary:
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = next(
                boundary
                for boundary in (
                    midnight + timedelta(minutes=450),
                    midnight + timedelta(minutes=750),
                    midnight + timedelta(minutes=1110),
                    midnight + timedelta(days=1),
                )
                if boundary > now
            )
            self._primary = (now, end, entry.expires_at, result)
        return result.copy()
