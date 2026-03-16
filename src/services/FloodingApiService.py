from __future__ import annotations

import logging

from src.clients.FloodingApiClient import AuthenticatedApiClient
from src.schemas.FloodingResponse import UserStatus

logger = logging.getLogger(__name__)


class FloodingApiService:
    def __init__(
        self,
        client: AuthenticatedApiClient,
        auth_service,
    ) -> None:
        self._client = client
        self._auth_service = auth_service

    async def get_user_status(self, discord_user_id: str) -> UserStatus:
        token = await self._auth_service.get_valid_token(discord_user_id)
        resp = await self._client.get_with_bearer("/user/myself", access_token=token)
        return self._to_user_status(resp.data)

    async def request_music(self, discord_user_id: str, music_url: str) -> None:
        token = await self._auth_service.get_valid_token(discord_user_id)
        await self._client.post_with_bearer(
            "/music",
            access_token=token,
            json={"music_url": music_url},
        )

    def _to_user_status(self, data: dict) -> UserStatus:
        student = data.get("student_info") or {}
        roles = data.get("roles", [])
        extra = {}
        if student:
            extra["학번"] = student.get("school_number", "-")
            extra["학년/반/번호"] = (
                f"{student.get('grade')}학년 "
                f"{student.get('classroom')}반 "
                f"{student.get('number')}번"
            )
        if roles:
            extra["역할"] = ", ".join(r.replace("ROLE_", "") for r in roles)
        teacher = data.get("teacher_info") or {}
        if teacher:
            extra["부서"] = teacher.get("department", "-")

        return UserStatus(
            user_id=str(data.get("id", "")),
            name=data.get("name", ""),
            status=data.get("gender", ""),
            extra=extra,
        )
