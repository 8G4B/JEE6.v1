from datetime import datetime
from dataclasses import dataclass

@dataclass
class JusticeRecord:
    user_id: int
    server_id: int
    count: int
    last_timeout: datetime 