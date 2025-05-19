import logging
import time
import asyncio
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
# from functools import lru_cache

from src.repositories.user_balance_repository import UserBalanceRepository
from src.repositories.jackpot_repository import JackpotRepository
from src.repositories.cooldown_repository import CooldownRepository
from src.config.settings.gambling_settings import (
    INCOME_TAX_BRACKETS,
    SECURITIES_TRANSACTION_TAX_BRACKETS,
    GIFT_TAX_BRACKETS,
    MIN_BET,
    MAX_BET,
)

logger = logging.getLogger(__name__)


class GamblingManager:
    def __init__(self):
        self.active_games: Dict[int, str] = {}
        self.lock = asyncio.Lock()

    async def start_game(self, user_id: int, game_type: str) -> bool:
        async with self.lock:
            if user_id in self.active_games:
                return False
            self.active_games[user_id] = game_type
            return True

    async def end_game(self, user_id: int) -> None:
        async with self.lock:
            if user_id in self.active_games:
                del self.active_games[user_id]


class GamblingService:

    _instance = None
    _locks: Dict[int, asyncio.Lock] = {}
    _rankings_cache: Dict[int, List[Tuple[int, str, int]]] = {}
    _rankings_cache_time: Dict[int, float] = {}
    CACHE_EXPIRATION = 300

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GamblingService, cls).__new__(cls)
            cls._instance.user_balance_repo = UserBalanceRepository()
            cls._instance.jackpot_repo = JackpotRepository()
            cls._instance.cooldown_repo = CooldownRepository()
        return cls._instance

    async def _get_lock(self, user_id: int) -> asyncio.Lock:
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    def validate_bet(
        self, bet_amount: Optional[int], min_bet: int = MIN_BET, max_bet: int = MAX_BET
    ) -> Optional[str]:
        if bet_amount is None:
            return f"{min_bet:,}원 이상 베팅하세요"
        if bet_amount < min_bet:
            return f"{min_bet:,}원 이상 베팅하세요"
        if bet_amount > max_bet:
            return f"{max_bet:,}원 이상 베팅할 수 없습니다"
        return None

    async def get_balance(self, user_id: int, server_id: int) -> int:
        return await self.user_balance_repo.get_user_balance(user_id, server_id)

    async def add_balance(self, user_id: int, server_id: int, amount: int) -> None:
        await self.user_balance_repo.add_user_balance(user_id, server_id, amount)

    async def subtract_balance(self, user_id: int, server_id: int, amount: int) -> None:
        await self.user_balance_repo.subtract_user_balance(user_id, server_id, amount)

    async def get_jackpot(self, server_id: int) -> int:
        return await self.jackpot_repo.get_jackpot(server_id)

    async def add_jackpot(self, server_id: int, amount: int) -> None:
        await self.jackpot_repo.add_jackpot(server_id, amount)

    async def subtract_jackpot(self, server_id: int, amount: int) -> None:
        await self.jackpot_repo.subtract_jackpot(server_id, amount)

    async def set_cooldown(self, user_id: int, action_type: str) -> None:
        await self.cooldown_repo.set_cooldown(user_id, action_type)

    async def check_cooldown(
        self, user_id: int, action_type: str, cooldown_seconds: int
    ) -> int:
        last_used = await self.cooldown_repo.get_cooldown(user_id, action_type)
        if not last_used:
            return 0

        now = datetime.utcnow()
        cooldown_end = last_used + timedelta(seconds=cooldown_seconds)

        if now < cooldown_end:
            remaining = (cooldown_end - now).total_seconds()
            return int(remaining)
        return 0

    def calculate_tax(self, amount: int, tax_type: str = "income") -> int:
        if tax_type == "securities" or tax_type in [
            "coin",
            "dice",
            "blackjack",
            "baccarat",
            "indian_poker",
        ]:
            return self.calculate_securities_transaction_tax(amount)
        elif tax_type == "gift":
            return self.calculate_gift_tax(amount)
        else:
            return self.calculate_income_tax(amount)

    def calculate_income_tax(self, amount: int) -> int:
        for threshold, rate in INCOME_TAX_BRACKETS:
            if amount > threshold:
                return int(amount * rate)
        return 0

    def calculate_securities_transaction_tax(self, amount: int) -> int:
        for threshold, rate in SECURITIES_TRANSACTION_TAX_BRACKETS:
            if amount > threshold:
                return int(amount * rate)
        return 0

    def calculate_gift_tax(self, amount: int) -> int:
        for threshold, rate in GIFT_TAX_BRACKETS:
            if amount > threshold:
                return int(amount * rate)
        return 0

    async def get_rankings(
        self, server_id: int, limit: int = 10
    ) -> List[Tuple[int, int]]:
        return await self.user_balance_repo.get_rankings(server_id, limit)

    async def get_cached_rankings(
        self, server_id: int, bot, limit: int = 10
    ) -> List[Tuple[int, str, int]]:
        current_time = time.time()

        if (
            server_id in self._rankings_cache
            and server_id in self._rankings_cache_time
            and current_time - self._rankings_cache_time[server_id]
            < self.CACHE_EXPIRATION
        ):
            return self._rankings_cache[server_id][:limit]

        rankings = await self.get_rankings(server_id, limit)
        result = []

        for user_id, balance in rankings:
            try:
                user = await bot.fetch_user(user_id)
                username = user.name
            except Exception:
                username = f"알 수 없음({user_id})"

            result.append((user_id, username, balance))

        self._rankings_cache[server_id] = result
        self._rankings_cache_time[server_id] = current_time

        return result[:limit]

    def calculate_hand_value(self, cards: List[str]) -> int:
        value = 0
        aces = 0

        for card in cards:
            if card in ["J", "Q", "K"]:
                value += 10
            elif card == "A":
                aces += 1
                value += 11
            else:
                value += int(card)

        while value > 21 and aces > 0:
            value -= 10
            aces -= 1

        return value

    def calculate_baccarat_value(self, cards: List[str]) -> int:
        value = 0

        for card in cards:
            if card in ["J", "Q", "K", "10"]:
                value += 0
            elif card == "A":
                value += 1
            else:
                value += int(card)

        return value % 10
