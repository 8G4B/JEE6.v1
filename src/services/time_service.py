from datetime import datetime
from zoneinfo import ZoneInfo

class TimeService:
    def __init__(self, timezone: str = 'Asia/Seoul'):
        self.timezone = timezone

    def get_current_time(self) -> str:
        current_time = datetime.now(ZoneInfo(self.timezone))
        return current_time.strftime("%Y-%m-%d %H:%M:%S")

    def get_current_datetime(self) -> datetime:
        return datetime.now(ZoneInfo(self.timezone))
