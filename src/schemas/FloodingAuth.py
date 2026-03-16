from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TokenInfo:
    access_token: str
    refresh_token: Optional[str]
    expires_at: Optional[datetime]
    token_type: str = "Bearer"


@dataclass
class FloodingUserProfile:
    user_id: str
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class LinkStatus:
    is_linked: bool
    flooding_user_id: Optional[str] = None
    linked_at: Optional[datetime] = None
    token_expires_at: Optional[datetime] = None
