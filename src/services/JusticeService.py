import logging
from datetime import timedelta
from typing import Tuple, Optional
import discord
from src.repositories.JusticeRepository import JusticeRepository
from src.domain.models.timeout_history import TimeoutHistory
from src.utils.time.timeParser import parse_time_string

logger = logging.getLogger(__name__)


class JusticeService:
    def __init__(self, justice_repository: JusticeRepository):
        self.repository = justice_repository

    async def judge_user(
        self, 
        member: discord.Member, 
        server_id: int, 
        moderator_id: int, 
        reason: str,
        custom_duration: Optional[str] = None
    ) -> Tuple[int, timedelta]:
        user_id = member.id

        count = await self.repository.get_user_count(user_id, server_id) + 1
        await self.repository.set_user_count(user_id, server_id, count)

        if custom_duration:
            seconds = parse_time_string(custom_duration)
            if seconds:
                timeout_duration = timedelta(seconds=seconds)
            else:
                timeout_duration = timedelta(minutes=1)
        else:
            if count <= 3:
                timeout_duration = timedelta(minutes=1)
            else:
                timeout_duration = timedelta(weeks=1)

        history = TimeoutHistory(
            user_id=user_id,
            server_id=server_id,
            moderator_id=moderator_id,
            reason=reason,
            duration=timeout_duration,
        )
        await self.repository.add_timeout_history(history)

        return count, timeout_duration

    async def release_user(
        self, member: discord.Member, server_id: int, clear_record: bool = False
    ) -> Tuple[bool, int]:
        user_id = member.id
        count = await self.repository.get_user_count(user_id, server_id)

        if member.timed_out_until is None:
            return False, count

        if clear_record and count > 0:
            count -= 1
            await self.repository.set_user_count(user_id, server_id, count)

        return True, count
