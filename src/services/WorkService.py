from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal, Optional
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
WorkMode = Literal["regular", "overtime"]

_TARGET_TIMES: dict[WorkMode, time] = {
    "regular": time(hour=16, minute=30),
    "overtime": time(hour=21, minute=30),
}


@dataclass(frozen=True)
class WorkStatus:
    mode: WorkMode
    state: Literal["countdown", "target_time"]
    now: datetime
    target: datetime


class WorkService:
    def get_status(
        self,
        mode: WorkMode,
        now: Optional[datetime] = None,
    ) -> WorkStatus:
        current = self._as_kst(now or datetime.now(KST))
        target = datetime.combine(current.date(), _TARGET_TIMES[mode], tzinfo=KST)

        if target <= current < target + timedelta(minutes=1):
            return WorkStatus(
                mode=mode,
                state="target_time",
                now=current,
                target=target,
            )

        if current >= target:
            target += timedelta(days=1)

        return WorkStatus(
            mode=mode,
            state="countdown",
            now=current,
            target=target,
        )

    @staticmethod
    def _as_kst(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=KST)
        return value.astimezone(KST)
