from datetime import datetime
from src.utils.time.formatter import format_time

class TimeService:
    def get_current_time(self):
        current_time = datetime.now()
        return format_time(current_time)
