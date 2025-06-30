import json
import logging
import aiohttp
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from src.config.settings.busSettings import (
    BIS_API_KEY,
    BIS_BASE_URL,
    NODE_ID,
    CACHE_DURATION,
    NO_BUS_INFO,
    API_ERROR,
)

logger = logging.getLogger(__name__)


class BusService:
    _cache: Dict[str, tuple[List, datetime]] = {}

    async def get_bus_arrival_info(self) -> Tuple[Optional[str], Optional[List]]:
        cache_key = f"bus_{NODE_ID}"

        if cache_key in self._cache:
            cached_data, cache_time = self._cache[cache_key]
            if datetime.now() - cache_time < CACHE_DURATION:
                logger.debug("Cache hit for bus info")
                return self._format_bus_info(cached_data)
            logger.debug("Cache expired for bus info")
            del self._cache[cache_key]

        params = {
            "serviceKey": BIS_API_KEY,
            "BUSSTOP_ID": NODE_ID
        }

        try:
            async with aiohttp.ClientSession() as session:
                import urllib.parse
                decoded_key = urllib.parse.unquote(BIS_API_KEY)
                params["serviceKey"] = decoded_key

                async with session.get(BIS_BASE_URL, params=params) as response:
                    text = await response.text()

                    if response.status != 200:
                        logger.error(f"API response status: {response.status}, body: {text}")
                        return API_ERROR, None

                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}, raw text: {text}")
                        return API_ERROR, None

                    if "RESULT" in data and data["RESULT"]["RESULT_CODE"] == "SUCCESS":
                        if "BUSSTOP_LIST" in data and data["BUSSTOP_LIST"]:
                            bus_list = data["BUSSTOP_LIST"]

                            self._cache[cache_key] = (bus_list, datetime.now())
                            return self._format_bus_info(bus_list)
                        else:
                            logger.warning(f"No bus arrival info for node {NODE_ID}")
                            return NO_BUS_INFO, None
                    else:
                        error_msg = data.get("RESULT", {}).get("RESULT_MSG", "Unknown error")
                        logger.error(f"API Error: {error_msg}")
                        return API_ERROR, None

        except (aiohttp.ClientError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error fetching bus arrival info: {e}")
            return API_ERROR, None

    def _format_bus_info(self, bus_list: List[Dict]) -> Tuple[str, List[Dict]]:
        if not bus_list:
            return NO_BUS_INFO, None

        sorted_buses = sorted(bus_list, key=lambda x: int(x.get('REMAIN_MIN', 999999)))

        top_buses = sorted_buses[:10]

        formatted_buses = []
        for bus in top_buses:
            remain_min = int(bus.get('REMAIN_MIN', 0))
            route_no = bus.get('SHORT_LINE_NAME', bus.get('LINE_NAME', '알 수 없음'))
            line_kind = bus.get('LINE_KIND', 0)
            low_bus = bus.get('LOW_BUS', '0')
            remaining_stations = bus.get('REMAIN_STOP', '0')
            arrive_flag = int(bus.get('ARRIVE_FLAG', 0))
            current_stop = bus.get('BUSSTOP_NAME', '')

            time_str = f"{remain_min}분"

            vehicle_type = "일반"
            if low_bus == "1":
                vehicle_type = "저상"
            elif line_kind == 6:
                vehicle_type = "마을"

            formatted_buses.append({
                'route_no': route_no,
                'route_type': str(line_kind),
                'vehicle_type': vehicle_type,
                'arrival_time': time_str,
                'remaining_stations': str(remaining_stations),
                'current_stop': current_stop,
                'raw_time': remain_min,
                'arrive_flag': arrive_flag
            })

        return "success", formatted_buses
