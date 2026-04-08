import logging
import aiohttp
from src.config.settings.base import BaseConfig

logger = logging.getLogger(__name__)


class ApiGatewayClient:
    def __init__(self):
        self.base_url = BaseConfig.API_GATEWAY_URL
        self._timeout = aiohttp.ClientTimeout(total=15)

    async def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.get(url, params=params) as resp:
                return await resp.json()

    async def get_meal(self, meal_type: str = "auto", day: str = "today") -> dict:
        return await self._get("/meal/", {"meal_type": meal_type, "day": day})

    async def get_water_temp(self) -> dict:
        return await self._get("/water/")

    async def get_time(self) -> dict:
        return await self._get("/time/")

    async def get_lol_tier(self, riot_id: str) -> dict:
        return await self._get(f"/riot/lol/tier/{riot_id}")

    async def get_lol_history(self, riot_id: str) -> dict:
        return await self._get(f"/riot/lol/history/{riot_id}")

    async def get_lol_rotation(self) -> dict:
        return await self._get("/riot/lol/rotation")

    async def get_valo_tier(self, riot_id: str) -> dict:
        return await self._get(f"/riot/valo/tier/{riot_id}")

    async def get_valo_history(self, riot_id: str) -> dict:
        return await self._get(f"/riot/valo/history/{riot_id}")

    async def get_random_track(self) -> dict:
        return await self._get("/spotify/random")

    async def health(self) -> bool:
        try:
            result = await self._get("/health")
            return result.get("status") == "ok"
        except Exception:
            return False
