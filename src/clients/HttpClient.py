import asyncio
from typing import Optional

import aiohttp


_session: Optional[aiohttp.ClientSession] = None
_session_lock = asyncio.Lock()
_default_timeout = aiohttp.ClientTimeout(total=15, connect=3, sock_read=12)


async def get_http_session() -> aiohttp.ClientSession:
    global _session

    if _session is not None and not _session.closed:
        return _session

    async with _session_lock:
        if _session is None or _session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                ttl_dns_cache=300,
                enable_cleanup_closed=True,
            )
            _session = aiohttp.ClientSession(
                connector=connector,
                timeout=_default_timeout,
            )

    return _session


async def close_http_session() -> None:
    global _session

    if _session is not None and not _session.closed:
        await _session.close()
    _session = None
