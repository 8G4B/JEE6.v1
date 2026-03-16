from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class BotBaseError(Exception):
    def __init__(self, user_message: str = "오류가 발생했습니다."):
        self.user_message = user_message
        super().__init__(user_message)


class ExternalApiError(BotBaseError):
    def __init__(self, status: int = 0, user_message: str = "API 오류가 발생했습니다.", data: Any = None):
        self.status = status
        self.data = data
        super().__init__(user_message)


class AuthenticationError(BotBaseError):
    def __init__(self, user_message: str = "인증에 실패했습니다. 다시 로그인해주세요."):
        super().__init__(user_message)


class AuthorizationError(BotBaseError):
    def __init__(self, user_message: str = "접근 권한이 없습니다."):
        super().__init__(user_message)


class NotFoundError(BotBaseError):
    def __init__(self, user_message: str = "요청한 정보를 찾을 수 없습니다."):
        super().__init__(user_message)


class RateLimitError(BotBaseError):
    def __init__(self, user_message: str = "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."):
        super().__init__(user_message)


class ExternalApiUnavailableError(BotBaseError):
    def __init__(self, user_message: str = "플러딩 서비스에 연결할 수 없습니다."):
        super().__init__(user_message)


class UserNotLinkedError(BotBaseError):
    def __init__(self, user_message: str = "플러딩 계정이 연동되지 않았습니다. `!플러딩.로그인`으로 연동해주세요."):
        super().__init__(user_message)


@dataclass
class ApiResponse:
    status: int
    data: Any
    headers: dict[str, str] = field(default_factory=dict)


class BaseApiClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def _build_headers(self, extra: Optional[dict] = None) -> dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if extra:
            h.update(extra)
        return h

    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[dict] = None,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        cookies: Optional[dict] = None,
    ) -> ApiResponse:
        url = f"{self._base_url}{path}"
        merged = self._build_headers(headers)
        session = await self._get_session()
        last_exc: Exception = RuntimeError("No attempts")

        for attempt in range(self._max_retries):
            try:
                logger.debug("[Flooding] %s %s attempt=%d", method, url, attempt + 1)
                async with session.request(
                    method,
                    url,
                    headers=merged,
                    json=json,
                    params=params,
                    cookies=cookies,
                ) as resp:
                    try:
                        data = await resp.json(content_type=None)
                    except Exception:
                        data = await resp.text()

                    logger.debug("[Flooding] %s %s status=%d", method, url, resp.status)
                    return self._handle_status(resp.status, data, dict(resp.headers))

            except (
                AuthenticationError,
                AuthorizationError,
                NotFoundError,
                RateLimitError,
                ExternalApiUnavailableError,
                ExternalApiError,
            ):
                raise
            except asyncio.TimeoutError as exc:
                last_exc = exc
                logger.warning("[Flooding] Timeout %s attempt=%d", url, attempt + 1)
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2**attempt)
            except aiohttp.ClientError as exc:
                last_exc = exc
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2**attempt)

        raise ExternalApiUnavailableError(
            f"플러딩 서비스 연결 실패 ({self._max_retries}회 재시도): {last_exc}"
        )

    def _handle_status(
        self,
        status: int,
        data: Any,
        headers: dict[str, str],
    ) -> ApiResponse:
        if status in (200, 201):
            return ApiResponse(status=status, data=data, headers=headers)
        if status == 204:
            return ApiResponse(status=status, data=None, headers=headers)
        if status == 400:
            raise ExternalApiError(status, "잘못된 요청입니다.", data)
        if status == 401:
            raise AuthenticationError()
        if status == 403:
            raise AuthorizationError()
        if status == 404:
            raise NotFoundError()
        if status == 429:
            retry_after = headers.get("Retry-After", "잠시")
            raise RateLimitError(f"{retry_after}초 후 다시 시도해주세요.")
        if status >= 500:
            raise ExternalApiUnavailableError()
        raise ExternalApiError(status, f"예상치 못한 응답 코드: {status}", data)

    async def get(self, path: str, **kw) -> ApiResponse:
        return await self.request("GET", path, **kw)

    async def post(self, path: str, **kw) -> ApiResponse:
        return await self.request("POST", path, **kw)

    async def put(self, path: str, **kw) -> ApiResponse:
        return await self.request("PUT", path, **kw)

    async def patch(self, path: str, **kw) -> ApiResponse:
        return await self.request("PATCH", path, **kw)

    async def delete(self, path: str, **kw) -> ApiResponse:
        return await self.request("DELETE", path, **kw)


class AuthenticatedApiClient(BaseApiClient):
    async def request_with_bearer(
        self,
        method: str,
        path: str,
        access_token: str,
        **kw,
    ) -> ApiResponse:
        headers = kw.pop("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"
        return await self.request(method, path, headers=headers, **kw)

    async def request_with_cookie(
        self,
        method: str,
        path: str,
        session_cookie: str,
        cookie_name: str = "sessionid",
        **kw,
    ) -> ApiResponse:
        cookies = kw.pop("cookies", {})
        cookies[cookie_name] = session_cookie
        return await self.request(method, path, cookies=cookies, **kw)

    async def get_with_bearer(
        self, path: str, access_token: str, **kw
    ) -> ApiResponse:
        return await self.request_with_bearer("GET", path, access_token, **kw)

    async def post_with_bearer(
        self, path: str, access_token: str, **kw
    ) -> ApiResponse:
        return await self.request_with_bearer("POST", path, access_token, **kw)
