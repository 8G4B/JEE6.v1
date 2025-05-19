from datetime import datetime
from zoneinfo import ZoneInfo


def format_time(dt: datetime, timezone: str = "Asia/Seoul") -> str:
    local_dt = dt.astimezone(ZoneInfo(timezone))
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")
