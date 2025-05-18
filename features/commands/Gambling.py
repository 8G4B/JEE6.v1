import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import json
import os
import secrets
import random
import threading
import asyncio
import time
from typing import Optional, Tuple, List, Dict, Callable, Any
from shared.database import (
    get_user_balance, set_user_balance,
    get_jackpot, set_jackpot,
    get_cooldown, set_cooldown,
    get_sorted_balances
)

class GamblingConfig:
    MIN_BET = 100
    MIN_JACKPOT_BET = 1000
    MAX_BET = 100_000_000_000_000

    INITIAL_JACKPOT = 1_000_000

    JACKPOT_WIN_COOLDOWN = 1800
    GAME_COOLDOWN = 5
    WORK_COOLDOWN = 60

    INCOME_TAX_BRACKETS = [
        (1_000_000_000_000_000, 0.45),
        (  500_000_000_000_000, 0.42),
        (  300_000_000_000_000, 0.40),
        (  150_000_000_000_000, 0.38),
        (   88_000_000_000_000, 0.35),
        (   50_000_000_000_000, 0.24),
        (   14_000_000_000_000, 0.15),
        (    5_000_000_000_000, 0.06),
        (0, 0)
    ]

    SECURITIES_TRANSACTION_TAX_BRACKETS = [
        (30_000_000_000_000, 0.02),
        (10_000_000_000_000, 0.01),
        (0, 0.005)
    ]

    GIFT_TAX_BRACKETS = [
        (30_000_000_000_000, 0.15),
        (10_000_000_000_000, 0.125),
        ( 5_000_000_000_000, 0.10),
        ( 1_000_000_000_000, 0.075),
        (0, 0.05)
    ]

    GAME_MULTIPLIER_RANGES = {
        'coin': (1.0, 1.2),
        'dice': (4.6, 5.7),
        'blackjack': (1.2, 1.5),
        'baccarat': (1.2, 1.5),
        'indian_poker': (1.0, 1.2)
    }   

    WORK_REWARD_RANGE = (100, 2000)

    RESET_TIMES = [
        (7, 30),
        (12, 30),
        (18, 30)
    ]




class GamblingEmbed:
    @staticmethod
    def create_error_embed(description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류",
            description=description,
            color=discord.Color.red()
        )

    @staticmethod
    def create_game_embed(
        author_name: str,
        is_correct: bool,
        guess: str,
        result: str,
        bet: Optional[int] = None,
        winnings: Optional[int] = None,
        balance: Optional[int] = None,
        game_type: Optional[str] = None,
        tax: Optional[int] = None
    ) -> discord.Embed:
        title = f"{'🪙' if game_type == 'coin' else '🎲' if game_type == 'dice' else '🎰'} {author_name} {'맞음 ㄹㅈㄷ' if is_correct else '틀림ㅋ'}"
        color = discord.Color.green() if is_correct else discord.Color.red()

        description_parts = [
            f"- 예측: {guess}",
            f"- 결과: {result}"
        ]

        if bet is not None and winnings is not None and balance is not None:
            if is_correct:
                total_winnings = winnings + (tax or 0)
                multiplier = total_winnings / bet
                description_parts.extend([
                    f"## 수익: {bet:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)" if tax else f"## 수익: {bet:,}원 × {multiplier:.2f} = {winnings:,}원",
                    f"- 재산: {balance:,}원(+{winnings:,})"
                ])
            else:
                description_parts.extend([
                    f"## 수익: {bet:,}원 × -1 = {winnings:,}원",
                    f"- 재산: {balance:,}원({winnings:,})"
                ])

        return discord.Embed(
            title=title,
            description="\n".join(description_parts),
            color=color
        )

class GamblingService:
    def __init__(self):
        self._locks = {}
        self._lock_lock = asyncio.Lock()

    async def _get_lock(self, user_id: int) -> asyncio.Lock:
        async with self._lock_lock:
            if user_id not in self._locks:
                self._locks[user_id] = asyncio.Lock()
            return self._locks[user_id]

    async def get_balance(self, user_id: int) -> int:
        return await get_user_balance(user_id)

    async def set_balance(self, user_id: int, amount: int) -> None:
        await set_user_balance(user_id, amount)

    async def add_balance(self, user_id: int, amount: int) -> None:
        current_balance = await self.get_balance(user_id)
        await self.set_balance(user_id, current_balance + amount)

    async def subtract_balance(self, user_id: int, amount: int) -> None:
        current_balance = await self.get_balance(user_id)
        await self.set_balance(user_id, current_balance - amount)

    async def get_jackpot(self) -> int:
        return await get_jackpot()

    async def set_jackpot(self, amount: int) -> None:
        await set_jackpot(amount)

    async def add_jackpot(self, amount: int) -> None:
        current_jackpot = await self.get_jackpot()
        await self.set_jackpot(current_jackpot + amount)

    async def subtract_jackpot(self, amount: int) -> None:
        current_jackpot = await self.get_jackpot()
        await self.set_jackpot(current_jackpot - amount)

    async def get_sorted_balances(self) -> List[Tuple[int, int]]:
        return await get_sorted_balances()

    def calculate_gift_tax(self, amount: int) -> int:
        for threshold, rate in GamblingConfig.GIFT_TAX_BRACKETS:
            if amount > threshold:
                return int(amount * rate)
        return 0

    def validate_bet(self, bet: Optional[int], user_id: Optional[int] = None) -> Optional[discord.Embed]:
        if bet is None:
            return GamblingEmbed.create_error_embed("베팅 금액을 입력해주세요.")
        if bet < GamblingConfig.MIN_BET:
            return GamblingEmbed.create_error_embed(f"최소 {GamblingConfig.MIN_BET:,}원 이상 베팅해주세요.")
        if bet > GamblingConfig.MAX_BET:
            return GamblingEmbed.create_error_embed(f"최대 {GamblingConfig.MAX_BET:,}원까지 베팅할 수 있어요.")
        return None

class GamblingManager:
    def __init__(self):
        self.active_games: Dict[int, str] = {}
        self.lock = threading.RLock()
        
    def start_game(self, user_id: int, game_type: str) -> bool:
        with self.lock:
            if user_id in self.active_games:
                return False
            self.active_games[user_id] = game_type
            return True
            
    def end_game(self, user_id: int) -> None:
        with self.lock:
            self.active_games.pop(user_id, None)
            
    def get_active_game(self, user_id: int) -> Optional[str]:
        with self.lock:
            return self.active_games.get(user_id)

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns: Dict[str, datetime] = {}
        self.game_manager = GamblingManager()
        self.gambling_service = GamblingService()
        self.blackjack_players = set()
        self.baccarat_players = set()
        self.indian_poker_players = set()
        self.coin_players = set()
        self.dice_players = set()
        self.reset_jackpot.start()

    def _check_game_cooldown(self, user_id: int, game_type: str) -> Optional[discord.Embed]:
        current_time = datetime.now()
        cooldown_key = f"{game_type}_{user_id}"
        last_used = self.cooldowns.get(cooldown_key)

        if last_used:
            cooldown_time = (GamblingConfig.JACKPOT_WIN_COOLDOWN if game_type == "jackpot_win" 
                           else GamblingConfig.GAME_COOLDOWN)
            if (current_time - last_used).total_seconds() < cooldown_time:
                remaining = cooldown_time - int((current_time - last_used).total_seconds())
                minutes = remaining // 60
                seconds = remaining % 60

                time_str = f"{minutes}분 {seconds}초" if minutes > 0 else f"{seconds}초"

                return GamblingEmbed.create_error_embed(f"{time_str} 후에 다시 시도해주세요.")

        if game_type != "jackpot_win":
            self.cooldowns[cooldown_key] = current_time
        return None

    @tasks.loop(seconds=1)
    async def reset_jackpot(self):
        now = datetime.now()
        for hour, minute in GamblingConfig.RESET_TIMES:
            if now.hour == hour and now.minute == minute:
                await self.gambling_service.set_jackpot(GamblingConfig.INITIAL_JACKPOT)
                return discord.Embed(
                    title="🎰 잭팟 리셋",
                    description="잭팟이 100만원으로 리셋되었습니다.",
                    color=discord.Color.green()
                )

    async def _play_game(
        self,
        author_id: int,
        author_name: str,
        guess: str,
        result: str,
        bet: int,
        game_type: str
    ) -> discord.Embed:
        lock = await self.gambling_service._get_lock(author_id)
        try:
            async with lock:
                is_correct = (guess == result)
                if is_correct:
                    multiplier = random.uniform(*GamblingConfig.GAME_MULTIPLIER_RANGES[game_type])
                    winnings = int(bet * multiplier)
                    tax = self.gambling_service.calculate_tax(winnings, game_type)
                    winnings_after_tax = winnings - tax
                    await self.gambling_service.add_balance(author_id, winnings_after_tax)
                else:
                    winnings = -bet
                    tax = None
                    await self.gambling_service.subtract_balance(author_id, bet)

                return GamblingEmbed.create_game_embed(
                    author_name=author_name,
                    is_correct=is_correct,
                    guess=guess,
                    result=result,
                    bet=bet,
                    winnings=winnings_after_tax if is_correct else winnings,
                    balance=await self.gambling_service.get_balance(author_id),
                    game_type=game_type,
                    tax=tax
                )
        except Exception as e:
            logger.error(f"Error in _play_game: {e}")
            return GamblingEmbed.create_error_embed("게임 진행 중 오류가 발생했습니다.")

    @commands.command(name="도박.동전", description="동전 던지기")
    async def coin(self, ctx, bet: str = None):
        if not self.game_manager.start_game(ctx.author.id, "coin"):
            await ctx.reply(embed=GamblingEmbed.create_error_embed("이미 다른 게임이 진행 중입니다."))
            return

        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "coin"):
            await ctx.reply(embed=cooldown_embed)
            self.game_manager.end_game(ctx.author.id)
            return

        try:
            bet = int(bet) if bet != "올인" else await self.gambling_service.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if error_embed := self.gambling_service.validate_bet(bet, ctx.author.id):
            await ctx.reply(embed=error_embed)
            self.game_manager.end_game(ctx.author.id)
            return

        if bet > await self.gambling_service.get_balance(ctx.author.id):
            await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
            self.game_manager.end_game(ctx.author.id)
            return

        embed = discord.Embed(
            title=f"🪙 {ctx.author.name}의 동전 게임",
            description="앞면 또는 뒷면을 선택하세요",
            color=discord.Color.blue()
        )
        embed.add_field(name="선택", value="⭕ 앞면 / ❌ 뒷면", inline=False)

        game_message = await ctx.reply(embed=embed)
        await game_message.add_reaction("⭕")
        await game_message.add_reaction("❌")

        def check(reaction, user):
            return (user == ctx.author and 
                   str(reaction.emoji) in ["⭕", "❌"] and 
                   reaction.message.id == game_message.id)

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            guess = "앞" if str(reaction.emoji) == "⭕" else "뒤"
            result = secrets.choice(["앞", "뒤"])

            embed = await self._play_game(
                ctx.author.id,
                ctx.author.name,
                guess,
                result,
                bet,
                "coin"
            )
            await game_message.edit(embed=embed)

        except asyncio.TimeoutError:
            embed = GamblingEmbed.create_error_embed("30초 동안 응답이 없어 취소됐어요")
            await game_message.edit(embed=embed)

        finally:
            self.game_manager.end_game(ctx.author.id)

    @commands.command(name="도박.주사위", description="주사위")
    async def dice(self, ctx, bet: str = None):
        if not self.game_manager.start_game(ctx.author.id, "dice"):
            await ctx.reply(embed=GamblingEmbed.create_error_embed("이미 다른 게임이 진행 중입니다."))
            return

        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "dice"):
            await ctx.reply(embed=cooldown_embed)
            self.game_manager.end_game(ctx.author.id)
            return

        try:
            bet = int(bet) if bet != "올인" else await self.gambling_service.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if error_embed := self.gambling_service.validate_bet(bet, ctx.author.id):
            await ctx.reply(embed=error_embed)
            self.game_manager.end_game(ctx.author.id)
            return

        if bet > await self.gambling_service.get_balance(ctx.author.id):
            await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
            self.game_manager.end_game(ctx.author.id)
            return

        embed = discord.Embed(
            title=f"🎲 {ctx.author.name}의 주사위 게임",
            description="1부터 6까지 숫자를 선택하세요",
            color=discord.Color.blue()
        )
        embed.add_field(name="선택", value="1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣", inline=False)

        game_message = await ctx.reply(embed=embed)
        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
        for reaction in reactions:
            await game_message.add_reaction(reaction)

        def check(reaction, user):
            return (user == ctx.author and 
                   str(reaction.emoji) in reactions and 
                   reaction.message.id == game_message.id)

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            guess = str(reactions.index(str(reaction.emoji)) + 1)
            result = secrets.choice([str(i) for i in range(1, 7)])

            embed = await self._play_game(
                ctx.author.id,
                ctx.author.name,
                guess,
                result,
                bet,
                "dice"
            )
            await game_message.edit(embed=embed)

        except asyncio.TimeoutError:
            embed = GamblingEmbed.create_error_embed("30초 동안 응답이 없어 취소됐어요")
            await game_message.edit(embed=embed)

        finally:
            self.game_manager.end_game(ctx.author.id)

    @commands.command(name="도박.잭팟", description="잭팟")
    async def jackpot(self, ctx, bet: str = None):
        if not self.game_manager.start_game(ctx.author.id, "jackpot"):
            await ctx.reply(embed=GamblingEmbed.create_error_embed("이미 다른 게임이 진행 중입니다."))
            return

        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "jackpot"):
            await ctx.reply(embed=cooldown_embed)
            self.game_manager.end_game(ctx.author.id)
            return

        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "jackpot_win"):
            await ctx.reply(embed=cooldown_embed)
            self.game_manager.end_game(ctx.author.id)
            return

        try:
            bet = int(bet) if bet != "올인" else await self.gambling_service.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if bet is None or bet < GamblingConfig.MIN_JACKPOT_BET:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("1,000원 이상 베팅하세요"))
            self.game_manager.end_game(ctx.author.id)
            return

        if bet >= GamblingConfig.MAX_BET:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("100조원 이상 베팅할 수 없습니다"))
            self.game_manager.end_game(ctx.author.id)
            return

        lock = await self.gambling_service._get_lock(ctx.author.id)
        async with lock:
            current_balance = await self.gambling_service.get_balance(ctx.author.id)
            min_bet = current_balance // 100

            if bet > current_balance:
                await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
                self.game_manager.end_game(ctx.author.id)
                return

            if bet < min_bet:
                await ctx.reply(embed=GamblingEmbed.create_error_embed(
                    f"현재 재산의 1% 이상 베팅하세요. (최소 {min_bet:,}원)"))
                self.game_manager.end_game(ctx.author.id)
                return

            await self.gambling_service.subtract_balance(ctx.author.id, bet)
            await self.gambling_service.add_jackpot(bet)

            if secrets.randbelow(100) <= 1:  # 1% 확률
                winnings = await self.gambling_service.get_jackpot() // 10
                tax = self.gambling_service.calculate_tax(winnings)
                winnings_after_tax = winnings - tax
                await self.gambling_service.add_balance(ctx.author.id, winnings_after_tax)
                await self.gambling_service.subtract_jackpot(winnings)
                self.cooldowns[f"jackpot_win_{ctx.author.id}"] = datetime.now()
                
                embed = discord.Embed(
                    title=f"🎉 {ctx.author.name} 당첨",
                    description=(
                        f"- 현재 잭팟: {await self.gambling_service.get_jackpot():,}원(-{winnings:,})\n"
                        f"## 수익: {winnings_after_tax:,}원(세금: {tax:,}원)\n"
                        f"- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원(+{winnings_after_tax:,})"
                    ),
                    color=discord.Color.gold()
                )
            else:
                embed = discord.Embed(
                    title=f"🎰 {ctx.author.name} 잭팟 실패ㅋ",
                    description=(
                        f"- 현재 잭팟: {await self.gambling_service.get_jackpot():,}원\n"
                        f"## 수익: -{bet:,}원\n"
                        f"- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원"
                    ),
                    color=discord.Color.red()
                )

            await ctx.reply(embed=embed)
            self.game_manager.end_game(ctx.author.id)

    @commands.command(name="도박.노동", aliases=['도박.일', '도박.돈'], description="도박.노동")
    async def work(self, ctx):
        if not self.game_manager.start_game(ctx.author.id, "work"):
            await ctx.reply(embed=GamblingEmbed.create_error_embed("이미 다른 게임이 진행 중입니다."))
            return

        lock = await self.gambling_service._get_lock(ctx.author.id)
        async with lock:
            current_time = datetime.now()
            last_used = self.cooldowns.get(ctx.author.id)

            if last_used and (current_time - last_used).total_seconds() < GamblingConfig.WORK_COOLDOWN:
                remaining = GamblingConfig.WORK_COOLDOWN - int((current_time - last_used).total_seconds())
                embed = discord.Embed(
                    title="힘들어서 쉬는 중 ㅋ",
                    description=f"{remaining}초 후에 다시 시도해주세요.",
                    color=discord.Color.red()
                )
            else:
                amount = random.randint(*GamblingConfig.WORK_REWARD_RANGE)
                await self.gambling_service.add_balance(ctx.author.id, amount)
                embed = discord.Embed(
                    title=f"☭ {ctx.author.name} 노동",
                    description=(
                        f"정당한 노동을 통해 {amount:,}원을 벌었다.\n"
                        f"- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원(+{amount:,})"
                    ),
                    color=discord.Color.green()
                )
                self.cooldowns[ctx.author.id] = current_time

            await ctx.reply(embed=embed)
            self.game_manager.end_game(ctx.author.id)

    @commands.command(name="도박.지갑", aliases=['도박.잔액', '도박.직바'], description="잔액 확인")
    async def balance(self, ctx):
        lock = await self.gambling_service._get_lock(ctx.author.id)
        async with lock:
            balance = await self.gambling_service.get_balance(ctx.author.id)
            embed = discord.Embed(
                title=f"💰 {ctx.author.name}의 지갑",
                description=f"현재 잔액: {balance:,}원",
                color=discord.Color.blue()
            )
            await ctx.reply(embed=embed)

    @commands.command(name="도박.랭킹", description="랭킹")
    async def ranking(self, ctx):
        async with ctx.typing():
            rankings = await self.gambling_service.get_cached_rankings(self.bot)
            top_3 = rankings[:3]

            description_lines = []
            for i, (_, username, balance) in enumerate(top_3):
                description_lines.append(f"{i+1}. {username}: {balance:,}원")

            embed = discord.Embed(
                title="🏅 상위 3명 랭킹",
                description="\n".join(description_lines) if description_lines else "랭킹이 없습니다.",
                color=discord.Color.blue()
            )
            await ctx.reply(embed=embed)

    @commands.command(name="도박.전체랭킹", description="전체 랭킹")
    async def all_ranking(self, ctx):
        async with ctx.typing():
            rankings = await self.gambling_service.get_cached_rankings(self.bot)
            
            if not rankings:
                embed = discord.Embed(
                    title="🏅 전체 랭킹",
                    description="랭킹 정보가 없습니다.",
                    color=discord.Color.blue()
                )
                await ctx.reply(embed=embed)
                return

            pages = []
            page_size = 10
            
            # 페이지 미리 생성
            for i in range(0, len(rankings), page_size):
                page_users = rankings[i:i + page_size]
                page_lines = []
                
                for rank, (_, username, balance) in enumerate(page_users, start=i + 1):
                    page_lines.append(f"{rank}. {username}: {balance:,}원")
                    
                pages.append("\n".join(page_lines))

            current_page = 0
            embed = discord.Embed(
                title="🏅 전체 랭킹",
                description=pages[current_page],
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"{current_page + 1}/{len(pages)}")

            message = await ctx.reply(embed=embed)

            if len(pages) > 1:
                await message.add_reaction("◀️")
                await message.add_reaction("▶️")

                def check(reaction, user):
                    return (user == ctx.author and 
                            str(reaction.emoji) in ["◀️", "▶️"] and 
                            reaction.message.id == message.id)

                while True:
                    try:
                        reaction, user = await self.bot.wait_for(
                            "reaction_add",
                            timeout=30.0,
                            check=check
                        )

                        if str(reaction.emoji) == "▶️" and current_page < len(pages) - 1:
                            current_page += 1
                        elif str(reaction.emoji) == "◀️" and current_page > 0:
                            current_page -= 1

                        embed.description = pages[current_page]
                        embed.set_footer(text=f"{current_page + 1}/{len(pages)}")
                        await message.edit(embed=embed)
                        await message.remove_reaction(reaction, user)

                    except asyncio.TimeoutError:
                        await message.clear_reactions()
                        break

    @commands.command(name="도박.송금", description="송금")
    async def transfer(self, ctx, recipient: discord.Member = None, amount: str = None):
        if recipient is None or amount is None:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("!도박.송금 [유저] [금액] <-- 이렇게 써"))
            return

        try:
            amount = int(amount) if amount != "올인" else await self.gambling_service.get_balance(ctx.author.id)
        except ValueError:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("올바른 금액을 입력하세요"))
            return

        if amount <= GamblingConfig.MIN_JACKPOT_BET:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("1,000원 이하는 송금할 수 없습니다."))
            return

        if amount >= GamblingConfig.MAX_BET:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("100조원 이상 송금할 수 없습니다"))
            return

        sender_lock = await self.gambling_service._get_lock(ctx.author.id)
        recipient_lock = await self.gambling_service._get_lock(recipient.id)
        
        async with sender_lock:
            async with recipient_lock:
                sender_balance = await self.gambling_service.get_balance(ctx.author.id)

                if amount > sender_balance:
                    await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
                    return

                tax = self.gambling_service.calculate_gift_tax(amount)
                amount_after_tax = amount - tax

                await self.gambling_service.subtract_balance(ctx.author.id, amount)
                await self.gambling_service.add_balance(recipient.id, amount_after_tax)
                await self.gambling_service.add_jackpot(tax)

                embed = discord.Embed(
                    title="💸 송금 완료",
                    description=(
                        f"{ctx.author.name} → {recipient.name}\n"
                        f"## {amount:,}원 송금(세금: {tax:,}원)\n"
                        f"- 잔액: {await self.gambling_service.get_balance(ctx.author.id):,}원"
                    ),
                    color=discord.Color.green()
                )

                await ctx.reply(embed=embed)

    @commands.command(name="도박.블랙잭", description="블랙잭")
    async def blackjack(self, ctx, bet: str = None):
        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "blackjack"):
            await ctx.reply(embed=cooldown_embed)
            return

        try:
            bet = int(bet) if bet != "올인" else await self.gambling_service.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if error_embed := self.gambling_service.validate_bet(bet, ctx.author.id):
            await ctx.reply(embed=error_embed)
            return

        if bet > await self.gambling_service.get_balance(ctx.author.id):
            await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
            return

        self.blackjack_players.add(ctx.author.id)

        try:
            cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'] * 4
            random.shuffle(cards)

            player_hand = [cards.pop(), cards.pop()]
            dealer_hand = [cards.pop(), cards.pop()]

            player_value = self.gambling_service.calculate_hand_value(player_hand)
            dealer_value = self.gambling_service.calculate_hand_value(dealer_hand)

            embed = discord.Embed(
                title=f"🃏 {ctx.author.name}의 블랙잭",
                description=f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\nJEE6의 패: {dealer_hand[0]} ?",
                color=discord.Color.blue()
            )
            embed.add_field(name="선택", value="👊 Hit / 🛑 Stand", inline=False)

            game_message = await ctx.reply(embed=embed)
            await game_message.add_reaction("👊")
            await game_message.add_reaction("🛑")

            def check(reaction, user):
                return (user == ctx.author and 
                       str(reaction.emoji) in ["👊", "🛑"] and 
                       reaction.message.id == game_message.id)

            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                    await reaction.remove(user)

                    if str(reaction.emoji) == "👊":
                        player_hand.append(cards.pop())
                        player_value = self.gambling_service.calculate_hand_value(player_hand)

                        if player_value > 21:
                            with await self.gambling_service._get_lock(ctx.author.id):
                                await self.gambling_service.subtract_balance(ctx.author.id, bet)

                            embed = discord.Embed(
                                title=f"🃏 {ctx.author.name} 버스트!",
                                description=(
                                    f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                                    f"JEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n"
                                    f"## 수익: {bet:,}원 × -1 = -{bet:,}원\n"
                                    f"- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원"
                                ),
                                color=discord.Color.red()
                            )
                            await game_message.edit(embed=embed)
                            return

                        embed = discord.Embed(
                            title=f"🃏 {ctx.author.name}의 블랙잭",
                            description=(
                                f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                                f"JEE6의 패: {dealer_hand[0]} ?"
                            ),
                            color=discord.Color.blue()
                        )
                        embed.add_field(name="선택", value="👊 Hit 또는 🛑 Stand", inline=False)
                        await game_message.edit(embed=embed)

                    elif str(reaction.emoji) == "🛑":
                        while dealer_value < 17:
                            dealer_hand.append(cards.pop())
                            dealer_value = self.gambling_service.calculate_hand_value(dealer_hand)

                        with await self.gambling_service._get_lock(ctx.author.id):
                            if dealer_value > 21 or player_value > dealer_value:
                                multiplier = 2.0 if player_value == 21 else random.uniform(*GamblingConfig.GAME_MULTIPLIER_RANGES["blackjack"])
                                winnings = int(bet * multiplier)
                                tax = self.gambling_service.calculate_tax(winnings, "blackjack")
                                winnings_after_tax = winnings - tax
                                await self.gambling_service.add_balance(ctx.author.id, winnings_after_tax)

                                embed = discord.Embed(
                                    title=f"🃏 {ctx.author.name} 승리",
                                    description=(
                                        f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                                        f"JEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n"
                                        f"## 수익: {bet:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)\n"
                                        f"- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원"
                                    ),
                                    color=discord.Color.green()
                                )
                            else:
                                await self.gambling_service.subtract_balance(ctx.author.id, bet)
                                embed = discord.Embed(
                                    title=f"🃏 {ctx.author.name} {'패배' if player_value < dealer_value else '무승부'}",
                                    description=(
                                        f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                                        f"JEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n"
                                        f"## 수익: {bet:,}원 × -1 = -{bet:,}원\n"
                                        f"- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원"
                                    ),
                                    color=discord.Color.red()
                                )

                            await game_message.edit(embed=embed)
                            return

                except asyncio.TimeoutError:
                    with await self.gambling_service._get_lock(ctx.author.id):
                        await self.gambling_service.subtract_balance(ctx.author.id, bet)
                        embed = discord.Embed(
                            title="⏳️ 시간 초과",
                            description=f"30초 동안 응답이 없어 베팅금 {bet:,}원을 잃었습니다.\n- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원",
                            color=discord.Color.red()
                        )
                    await game_message.edit(embed=embed)
                    return

        finally:
            self.blackjack_players.remove(ctx.author.id)

    @commands.command(name="도박.바카라", description="바카라")
    async def baccarat(self, ctx, bet: str = None):
        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "baccarat"):
            await ctx.reply(embed=cooldown_embed)
            return

        try:
            bet = int(bet) if bet != "올인" else await self.gambling_service.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if error_embed := self.gambling_service.validate_bet(bet, ctx.author.id):
            await ctx.reply(embed=error_embed)
            return

        if bet > await self.gambling_service.get_balance(ctx.author.id):
            await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
            return

        self.baccarat_players.add(ctx.author.id)

        try:
            embed = discord.Embed(
                title=f"🃏 {ctx.author.name}의 바카라",
                description="베팅할 곳을 선택하세요",
                color=discord.Color.blue()
            )
            embed.add_field(name="선택", value=f"👤 Player: {ctx.author.name} / 🏦 Banker: JEE6 / 🤝 Tie", inline=False)

            game_message = await ctx.reply(embed=embed)
            await game_message.add_reaction("👤")
            await game_message.add_reaction("🏦")
            await game_message.add_reaction("🤝")

            def check(reaction, user):
                return (user == ctx.author and 
                       str(reaction.emoji) in ["👤", "🏦", "🤝"] and 
                       reaction.message.id == game_message.id)

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)

                guess = {"👤": "Player", "🏦": "Banker", "🤝": "Tie"}[str(reaction.emoji)]

                cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'] * 4
                random.shuffle(cards)

                player_hand = [cards.pop(), cards.pop()]
                banker_hand = [cards.pop(), cards.pop()]

                player_value = self.gambling_service.calculate_baccarat_value(player_hand)
                banker_value = self.gambling_service.calculate_baccarat_value(banker_hand)

                if player_value <= 5:
                    player_hand.append(cards.pop())
                    player_value = self.gambling_service.calculate_baccarat_value(player_hand)

                if banker_value <= 5:
                    banker_hand.append(cards.pop())
                    banker_value = self.gambling_service.calculate_baccarat_value(banker_hand)

                if player_value > banker_value:
                    result = "Player"
                elif banker_value > player_value:
                    result = "Banker"
                else:
                    result = "Tie"

                with await self.gambling_service._get_lock(ctx.author.id):
                    if guess == result:
                        multiplier = 8 if result == "Tie" else random.uniform(*GamblingConfig.GAME_MULTIPLIER_RANGES["baccarat"])
                        winnings = int(bet * multiplier)
                        tax = self.gambling_service.calculate_tax(winnings, "baccarat")
                        winnings_after_tax = winnings - tax
                        await self.gambling_service.add_balance(ctx.author.id, winnings_after_tax - bet)

                        embed = discord.Embed(
                            title=f"🃏 {ctx.author.name} 맞음 ㄹㅈㄷ",
                            description=(
                                f"{ctx.author.name}: {' '.join(player_hand)} (합계: {player_value})\n"
                                f"JEE6: {' '.join(banker_hand)} (합계: {banker_value})\n"
                                f"## 수익: {bet:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)\n"
                                f"- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원"
                            ),
                            color=discord.Color.green()
                        )
                    else:
                        await self.gambling_service.subtract_balance(ctx.author.id, bet)
                        embed = discord.Embed(
                            title=f"🃏 {ctx.author.name} 틀림ㅋ",
                            description=(
                                f"{ctx.author.name}: {' '.join(player_hand)} (합계: {player_value})\n"
                                f"JEE6: {' '.join(banker_hand)} (합계: {banker_value})\n"
                                f"## 수익: {bet:,}원 × -1 = -{bet:,}원\n"
                                f"- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원"
                            ),
                            color=discord.Color.red()
                        )

                    await game_message.edit(embed=embed)

            except asyncio.TimeoutError:
                with await self.gambling_service._get_lock(ctx.author.id):
                    await self.gambling_service.subtract_balance(ctx.author.id, bet)
                    embed = discord.Embed(
                        title="⏳️ 시간 초과",
                        description=f"30초 동안 응답이 없어 베팅금 {bet:,}원을 잃었습니다.\n- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원",
                        color=discord.Color.red()
                    )
                await game_message.edit(embed=embed)

        finally:
            self.baccarat_players.remove(ctx.author.id)

    @commands.command(name="도박.인디언", aliases=['도박.인디언포커'], description="인디언 포커")
    async def indian_poker(self, ctx, bet: str = None):
        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "indian_poker"):
            await ctx.reply(embed=cooldown_embed)
            return

        try:
            bet = int(bet) if bet != "올인" else await self.gambling_service.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if error_embed := self.gambling_service.validate_bet(bet, ctx.author.id):
            await ctx.reply(embed=error_embed)
            return

        if bet > await self.gambling_service.get_balance(ctx.author.id):
            await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
            return

        self.indian_poker_players.add(ctx.author.id)

        try:
            player_card = random.randint(1, 10)
            banker_card = random.randint(1, 10)

            embed = discord.Embed(
                title=f"🃏 {ctx.author.name}의 인디언 포커",
                description=f"{ctx.author.name}의 카드: ?\nJEE6의 카드: {banker_card}",
                color=discord.Color.blue()
            )
            embed.add_field(name="선택", value="💀 Die / ✅ Call", inline=False)

            game_message = await ctx.reply(embed=embed)
            await game_message.add_reaction("💀")
            await game_message.add_reaction("✅")

            def check(reaction, user):
                return (user == ctx.author and 
                       str(reaction.emoji) in ["💀", "✅"] and 
                       reaction.message.id == game_message.id)

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)

                with await self.gambling_service._get_lock(ctx.author.id):
                    if str(reaction.emoji) == "💀":  # 다이
                        loss = bet // 2
                        await self.gambling_service.subtract_balance(ctx.author.id, loss)
                        embed = discord.Embed(
                            title=f"🃏 {ctx.author.name} Die",
                            description=(
                                f"{ctx.author.name}의 카드: {player_card}\n"
                                f"JEE6의 카드: {banker_card}\n"
                                f"## 수익: {bet:,}원 × -0.5 = -{loss:,}원\n"
                                f"- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원"
                            ),
                            color=discord.Color.red()
                        )
                    else:  # 콜
                        if player_card > banker_card:
                            multiplier = random.uniform(*GamblingConfig.GAME_MULTIPLIER_RANGES["indian_poker"])
                            winnings = int(bet * multiplier)
                            tax = self.gambling_service.calculate_tax(winnings, "indian_poker")
                            winnings_after_tax = winnings - tax
                            await self.gambling_service.add_balance(ctx.author.id, winnings_after_tax)
                            embed = discord.Embed(
                                title=f"🃏 {ctx.author.name} 승리",
                                description=(
                                    f"{ctx.author.name}의 카드: {player_card}\n"
                                    f"JEE6의 카드: {banker_card}\n"
                                    f"## 수익: {bet:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)\n"
                                    f"- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원"
                                ),
                                color=discord.Color.green()
                            )
                        else:
                            await self.gambling_service.subtract_balance(ctx.author.id, bet)
                            embed = discord.Embed(
                                title=f"🃏 {ctx.author.name} 패배",
                                description=(
                                    f"{ctx.author.name}의 카드: {player_card}\n"
                                    f"JEE6의 카드: {banker_card}\n"
                                    f"## 수익: {bet:,}원 × -1 = -{bet:,}원\n"
                                    f"- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원"
                                ),
                                color=discord.Color.red()
                            )

                    await game_message.edit(embed=embed)

            except asyncio.TimeoutError:
                with await self.gambling_service._get_lock(ctx.author.id):
                    await self.gambling_service.subtract_balance(ctx.author.id, bet)
                    embed = discord.Embed(
                        title="⏳️ 시간 초과",
                        description=f"30초 동안 응답이 없어 베팅금 {bet:,}원을 잃었습니다.\n- 재산: {await self.gambling_service.get_balance(ctx.author.id):,}원",
                        color=discord.Color.red()
                    )
                await game_message.edit(embed=embed)

        finally:
            self.indian_poker_players.remove(ctx.author.id)

    async def cog_check(self, ctx):
        if ctx.author.id in (self.blackjack_players | self.baccarat_players | 
                           self.indian_poker_players | self.coin_players | self.dice_players):
            
            current_game = None
            if ctx.author.id in self.blackjack_players:
                current_game = "블랙잭"
            elif ctx.author.id in self.baccarat_players:
                current_game = "바카라" 
            elif ctx.author.id in self.indian_poker_players:
                current_game = "인디언 포커"
            elif ctx.author.id in self.coin_players:
                current_game = "동전"
            elif ctx.author.id in self.dice_players:
                current_game = "주사위"
                
            await ctx.reply(embed=GamblingEmbed.create_error_embed(f"이미 {current_game} 게임이 진행 중입니다."))
            return False
            
        return True