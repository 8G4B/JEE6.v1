import json
import logging
import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict
from sqlalchemy import select
from src.config.settings.mealSettings import (
    MEAL_API_KEY,
    ATPT_OFCDC_SC_CODE,
    SD_SCHUL_CODE,
    NO_MEAL,
    MEAL_TIMES,
)
from src.infrastructure.database.Session import get_db_session
from src.domain.models.Meal import Meal

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=30, connect=5)
CACHE_TTL = 3600


class MealService:
    _meal_cache: Dict[str, List] = {}
    _meal_cache_time: Dict[str, float] = {}

    base_url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "key": MEAL_API_KEY,
        "type": "json",
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
    }

    _session: Optional[aiohttp.ClientSession] = None

    def __init__(self):
        if MealService._session is None or MealService._session.closed:
            MealService._session = aiohttp.ClientSession(timeout=TIMEOUT)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if MealService._session and not MealService._session.closed:
            await MealService._session.close()

    async def get_meal_info(self, date: str) -> Optional[List]:
        if (
            date in MealService._meal_cache
            and time.time() - MealService._meal_cache_time[date] < CACHE_TTL
        ):
            logger.debug(f"메모리 캐시 hit for {date}")
            return MealService._meal_cache[date]

        try:
            with get_db_session() as session:
                stmt = select(Meal).where(Meal.date == date)
                result = session.execute(stmt).scalars().all()
                if result:
                    logger.debug(f"DB hit for {date}")
                    meals = [
                        {
                            "MMEAL_SC_CODE": row.meal_code,
                            "DDISH_NM": row.menu,
                            "CAL_INFO": row.cal_info,
                        }
                        for row in result
                    ]
                    MealService._meal_cache[date] = meals
                    MealService._meal_cache_time[date] = time.time()
                    return meals
        except Exception as e:
            logger.error(f"DB Error: {e}")

        return await self._fetch_and_save_weekly_meals(date)

    async def _fetch_all_weekly_rows(self, from_ymd: str, to_ymd: str) -> List:
        session = MealService._session
        if session is None or session.closed:
            session = MealService._session = aiohttp.ClientSession(timeout=TIMEOUT)

        all_rows = []
        page = 1

        while True:
            params = self.params.copy()
            params["pIndex"] = page
            params["pSize"] = 100
            params["MLSV_FROM_YMD"] = from_ymd
            params["MLSV_TO_YMD"] = to_ymd

            async with session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    logger.warning(f"API returned status {response.status}")
                    break
                data = await response.json()

                info = data.get("mealServiceDietInfo")
                if not info or len(info) < 2:
                    break

                rows = info[1].get("row", [])
                all_rows.extend(rows)

                total_count = info[0].get("head", [{}])[0].get("list_total_count", 0)
                if len(all_rows) >= total_count:
                    break
                page += 1

        return all_rows

    async def _fetch_and_save_weekly_meals(self, target_date: str) -> Optional[List]:
        dt = datetime.strptime(target_date, "%Y%m%d")
        start_of_week = dt - timedelta(days=dt.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        from_ymd = start_of_week.strftime("%Y%m%d")
        to_ymd = end_of_week.strftime("%Y%m%d")

        try:
            logger.debug(f"Requesting weekly meal info for {from_ymd} ~ {to_ymd}")

            if not MEAL_API_KEY:
                logger.warning("MEAL_API_KEY가 설정되지 않았습니다. NEIS API가 pSize=5로 제한됩니다.")

            all_meals = await self._fetch_all_weekly_rows(from_ymd, to_ymd)

            if all_meals:
                await self._save_meals_to_db(all_meals, from_ymd, to_ymd)

                target_meals = [
                    {
                        "MMEAL_SC_CODE": m["MMEAL_SC_CODE"],
                        "DDISH_NM": "\n".join(
                            f"- {dish.strip()}"
                            for dish in m["DDISH_NM"]
                            .replace("*", "")
                            .split("<br/>")
                            if dish.strip()
                        ),
                        "CAL_INFO": m.get("CAL_INFO", "").strip()
                    }
                    for m in all_meals if m["MLSV_YMD"] == target_date
                ]
                if target_meals:
                    MealService._meal_cache[target_date] = target_meals
                    MealService._meal_cache_time[target_date] = time.time()
                return target_meals if target_meals else None

            logger.warning(f"No meal info returned for {target_date} (week search)")
            return None

        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error fetching meal info: {e}")
            return None

    async def _save_meals_to_db(self, all_meals: List, from_ymd: str, to_ymd: str):
        try:
            with get_db_session() as db_session:
                for meal in all_meals:
                    meal_date = meal["MLSV_YMD"]
                    meal_code = meal["MMEAL_SC_CODE"]

                    formatted_menu = "\n".join(
                        f"- {dish.strip()}"
                        for dish in meal["DDISH_NM"]
                        .replace("*", "")
                        .split("<br/>")
                        if dish.strip()
                    )

                    existing = db_session.execute(
                        select(Meal).where(
                            Meal.date == meal_date,
                            Meal.meal_code == meal_code
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        new_meal = Meal(
                            date=meal_date,
                            meal_code=meal_code,
                            menu=formatted_menu,
                            cal_info=meal.get("CAL_INFO", "").strip()
                        )
                        db_session.add(new_meal)
                    else:
                        existing.menu = formatted_menu
                        existing.cal_info = meal.get("CAL_INFO", "").strip()

                db_session.commit()
                logger.info(f"Saved weekly meals for {from_ymd} ~ {to_ymd}")

        except Exception as e:
            logger.error(f"Failed to save meals to DB: {e}")

    async def _get_menu_and_cal_from_meal_info(self, meal_info: list, meal_code: str) -> Tuple[str, str]:
        for meal in meal_info:
            if meal["MMEAL_SC_CODE"] == meal_code:
                menu = meal["DDISH_NM"]
                cal_info = meal.get("CAL_INFO", "").strip()
                return menu, cal_info
        return NO_MEAL, ""

    async def get_current_meal(
        self, now: datetime
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        today = now.strftime("%Y%m%d")
        current_hour = now.hour
        current_minute = now.minute

        meal_info = await self.get_meal_info(today)

        if not meal_info:
            logger.warning(f"No meal info available for today ({today})")
            return None, None, None

        for time_check, code, title in MEAL_TIMES:
            if time_check(current_hour, current_minute):
                menu, cal_info = await self._get_menu_and_cal_from_meal_info(meal_info, code)
                return title, menu, cal_info

        tomorrow = (now + timedelta(days=1)).strftime("%Y%m%d")
        tomorrow_meal_info = await self.get_meal_info(tomorrow)

        if tomorrow_meal_info:
            menu, cal_info = await self._get_menu_and_cal_from_meal_info(tomorrow_meal_info, "1")
        else:
            menu, cal_info = NO_MEAL, ""

        return "🍳 내일 아침", menu, cal_info

    async def get_meal_by_type(
        self, date: str, meal_code: str, title: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        meal_info = await self.get_meal_info(date)
        if not meal_info:
            logger.warning(f"No meal info available for {date}")
            return None, None, None

        menu, cal_info = await self._get_menu_and_cal_from_meal_info(meal_info, meal_code)
        return title, menu, cal_info
