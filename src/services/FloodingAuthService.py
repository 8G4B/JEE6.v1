from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from src.clients.FloodingApiClient import AuthenticationError, BaseApiClient, ExternalApiError, UserNotLinkedError
from src.repositories.UserLinkRepository import UserLinkRepository
from src.schemas.FloodingAuth import FloodingUserProfile, LinkStatus, TokenInfo

logger = logging.getLogger(__name__)


def _is_expired(dt: Optional[datetime]) -> bool:
    if dt is None:
        return True
    import pytz
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(tz=kst)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return now >= dt.astimezone(kst)


class FloodingAuthService:
    def __init__(
        self,
        client: BaseApiClient,
        user_link_repo: UserLinkRepository,
        auth_type: str = "bearer",
    ) -> None:
        self._client = client
        self._repo = user_link_repo

    async def login_with_credentials(
        self,
        discord_user_id: str,
        email: str,
        password: str,
    ) -> FloodingUserProfile:
        resp = await self._client.post(
            "/auth/sign-in",
            json={"email": email, "password": password},
        )
        token = self._parse_token_response(resp.data)
        profile = await self._fetch_profile(token.access_token)

        await self._repo.upsert(
            discord_user_id=discord_user_id,
            external_user_id=profile.user_id,
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            token_expires_at=token.expires_at,
        )
        logger.info("[Flooding] linked: discord=%s flooding=%s", discord_user_id, profile.user_id)
        return profile

    async def get_valid_token(self, discord_user_id: str) -> str:
        link = await self._repo.get_by_discord_id(discord_user_id)
        if link is None or not link.is_active or not link.access_token:
            raise UserNotLinkedError()

        if not _is_expired(link.token_expires_at):
            return link.access_token

        if not link.refresh_token:
            raise AuthenticationError()

        try:
            new_token = await self._reissue_token(link.refresh_token)
        except ExternalApiError:
            raise AuthenticationError()

        await self._repo.update_tokens(
            discord_user_id=discord_user_id,
            access_token=new_token.access_token,
            refresh_token=new_token.refresh_token,
            token_expires_at=new_token.expires_at,
        )
        return new_token.access_token

    async def logout(self, discord_user_id: str) -> None:
        link = await self._repo.get_by_discord_id(discord_user_id)
        if link and link.refresh_token:
            try:
                await self._client.post(
                    "/auth/logout",
                    headers={"Refresh-Token": link.refresh_token},
                )
            except Exception as e:
                logger.warning("[Flooding] logout API 호출 실패 (무시): %s", e)
        await self._repo.deactivate(discord_user_id)

    async def get_link_status(self, discord_user_id: str) -> LinkStatus:
        link = await self._repo.get_by_discord_id(discord_user_id)
        if link is None or not link.is_active:
            return LinkStatus(is_linked=False)
        return LinkStatus(
            is_linked=True,
            flooding_user_id=link.external_user_id,
            linked_at=link.created_at,
            token_expires_at=link.token_expires_at,
        )

    def _parse_token_response(self, data: dict) -> TokenInfo:
        import pytz
        kst = pytz.timezone("Asia/Seoul")
        raw_exp = data.get("access_token_expired_at", "")
        try:
            expires_at = kst.localize(datetime.strptime(raw_exp, "%Y-%m-%dT%H:%M:%S"))
        except (ValueError, TypeError):
            expires_at = None

        return TokenInfo(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
        )

    async def _fetch_profile(self, access_token: str) -> FloodingUserProfile:
        resp = await self._client.get(
            "/user/myself",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return self._parse_profile(resp.data)

    async def _reissue_token(self, refresh_token: str) -> TokenInfo:
        resp = await self._client.patch(
            "/auth/re-issue",
            headers={"Refresh-Token": refresh_token},
        )
        return self._parse_token_response(resp.data)

    def _parse_profile(self, data: dict) -> FloodingUserProfile:
        student = data.get("student_info") or {}
        display = None
        if student:
            display = f"{student.get('grade', '')}학년 {student.get('classroom', '')}반 {student.get('number', '')}번"
        return FloodingUserProfile(
            user_id=str(data["id"]),
            username=data["name"],
            email=data.get("email"),
            display_name=display,
        )
