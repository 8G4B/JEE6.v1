from datetime import datetime
from zoneinfo import ZoneInfo


class TimeService:
    def __init__(self, timezone: str = "Asia/Seoul"):
        self.timezone = timezone

    def get_current_time(self, format: str = "korean") -> str:
        current_time = datetime.now(ZoneInfo(self.timezone))
        if format == "korean":
            return f"{current_time.strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}"
        return current_time.strftime("%Y-%m-%d %H:%M:%S")

    def get_current_datetime(self) -> datetime:
        return datetime.now(ZoneInfo(self.timezone))

    def format_datetime(self, dt: datetime, format: str = "korean") -> str:
        if format == "korean":
            return f"{dt.strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}"
        return dt.strftime("%Y-%m-%d %H:%M:%S")
