from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class TimeoutHistory:
    user_id: int
    server_id: int
    moderator_id: int
    reason: str
    duration: timedelta
    created_at: datetime = None
