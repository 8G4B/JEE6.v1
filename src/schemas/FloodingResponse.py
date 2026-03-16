from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar


T = TypeVar("T")


@dataclass
class StandardResponse(Generic[T]):
    """플러딩 API 응답을 표준화한 내부 DTO."""

    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    code: Optional[str] = None


@dataclass
class UserStatus:
    user_id: str
    name: str
    status: str
    extra: dict[str, Any] = field(default_factory=dict)


