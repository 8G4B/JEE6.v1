import logging
import aiohttp
import time
from typing import Optional, Tuple
from src.config.settings.waterSettings import SEOUL_DATA_API_KEY, SEOUL_DATA_BASE_URL

logger = logging.getLogger(__name__)

CACHE_TTL = 600


class WaterService:
    _cache: Optional[Tuple[str, str, str]] = None
    _cache_time: float = 0.0

    def __init__(self):
        self.url = f"{SEOUL_DATA_BASE_URL}/{SEOUL_DATA_API_KEY}/json/WPOSInformationTime/1/5/"

    async def get_han_river_temp(self) -> Optional[Tuple[str, str, str]]:
        if WaterService._cache is not None and time.time() - WaterService._cache_time < CACHE_TTL:
            logger.debug("한강 수온 캐시 사용")
            return WaterService._cache

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as response:
                    if response.status != 200:
                        logger.error(f"Seoul Data API Error: {response.status}")
                        return None

                    data = await response.json()

                    if "WPOSInformationTime" not in data:
                        logger.error("Invalid API Response: WPOSInformationTime key missing")
                        return None

                    rows = data["WPOSInformationTime"]["row"]
                    if not rows:
                        logger.warning("No data rows found in API response")
                        return None

                    target_station = "선유"
                    latest_data = None

                    for row in rows:
                        if row.get("MSRSTN_NM") == target_station:
                            latest_data = row
                            break

                    if not latest_data:
                        latest_data = rows[0]

                    msr_time = latest_data.get("HR", "00:00")
                    w_temp = latest_data.get("WATT", "0.0")

                    if ":" in msr_time:
                        hour, minute = msr_time.split(":")
                    else:
                        hour, minute = "00", "00"

                    WaterService._cache = (hour, minute, w_temp)
                    WaterService._cache_time = time.time()
                    return WaterService._cache

        except Exception as e:
            logger.error(f"Error fetching water temperature: {e}")
            return None
