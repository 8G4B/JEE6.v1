import asyncio
from functools import wraps
from typing import Awaitable, Callable, ParamSpec, TypeVar


P = ParamSpec("P")
R = TypeVar("R")


def offload_db(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    """Run a synchronous database operation outside the Discord event loop."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper
