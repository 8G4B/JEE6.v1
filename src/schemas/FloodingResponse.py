from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar


T = TypeVar("T")


@dataclass
class StandardResponse(Generic[T]):
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


@dataclass
class MusicItem:
    music_id: str
    music_url: str
    music_name: str
    thumbnail_image_url: str
    like_count: int
    proposer_name: str
    proposer_school_number: str


