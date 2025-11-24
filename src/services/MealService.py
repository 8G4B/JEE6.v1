import json
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from src.config.settings.mealSettings import (
    MEAL_API_KEY,
    ATPT_OFCDC_SC_CODE,
    SD_SCHUL_CODE,
    NO_MEAL,
    MEAL_TIMES,
    CACHE_DURATION,
)

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=5, connect=2)


class MealService:
    base_url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "key": MEAL_API_KEY,
        "type": "json",
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
    }

    _cache: Dict[str, tuple[List, datetime]] = {}
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
        if date in self._cache:
            cached_data, cache_time = self._cache[date]
            if datetime.now() - cache_time < CACHE_DURATION:
                logger.debug(f"Cache hit for {date}")
                return cached_data
            logger.debug(f"Cache expired for {date}")
            del self._cache[date]

        params = self.params.copy()
        params["MLSV_YMD"] = date

        try:
            logger.debug(f"Requesting meal info for {date}")
            session = MealService._session
            if session is None or session.closed:
                session = MealService._session = aiohttp.ClientSession(timeout=TIMEOUT)
            async with session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    logger.warning(f"API returned status {response.status} for {date}")
                    return None
                data = await response.json()

                if "mealServiceDietInfo" in data:
                    meals = data["mealServiceDietInfo"][1]["row"]
                    for meal in meals:
                        meal["DDISH_NM"] = "\n".join(
                            f"- {dish.strip()}"
                            for dish in meal["DDISH_NM"]
                            .replace("*", "")
                            .split("<br/>")
                            if dish.strip()
                        )
                    self._cache[date] = (meals, datetime.now())
                    return meals
                logger.warning(f"No meal info returned for {date}")
                return None

        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error fetching meal info: {e}")
            return None

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
