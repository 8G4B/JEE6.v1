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
        'coin': (0.6, 1.7),
        'dice': (4.6, 5.7),
        'blackjack': (1.2, 1.5),
        'baccarat': (1.2, 1.5),
        'indian_poker': (0.5, 1.5)
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

class DataManager:
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.balances: Dict[int, int] = {}
        self.jackpot: int = 0
        self.locks: Dict[int, threading.RLock] = {}
        self.global_lock = threading.RLock()
        self.dirty: bool = False
        self.last_save = datetime.now()
        self._load_data()
        self._start_batch_save()

    def _start_batch_save(self) -> None:
        def save_periodically() -> None:
            while True:
                time.sleep(60)
                self._batch_save()

        save_thread = threading.Thread(target=save_periodically, daemon=True)
        save_thread.start()

    def _batch_save(self) -> None:
        with self.global_lock:
            if not self.dirty:
                return

            try:
                data = {
                    'balances': self.balances,
                    'jackpot': self.jackpot
                }
                temp_file = f"{self.data_file}.tmp"
                with open(temp_file, 'w') as f:
                    json.dump(data, f)
                os.replace(temp_file, self.data_file)
                self.dirty = False
                self.last_save = datetime.now()
            except Exception as e:
                print(f"Batch save error: {e}")

    def _load_data(self) -> None:
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.balances = {int(k): v for k, v in data.get('balances', {}).items()}
                    self.jackpot = data.get('jackpot', 0)
        except Exception as e:
            print(f"Load error: {e}")

    def _save_data(self) -> None:
        self.dirty = True
        if (datetime.now() - self.last_save).total_seconds() > 300:
            self._batch_save()

    def _get_lock(self, user_id: int) -> threading.RLock:
        if user_id not in self.locks:
            self.locks[user_id] = threading.RLock()
        return self.locks[user_id]

    def get_balance(self, user_id: int) -> int:
        return self.balances.get(user_id, 0)

    def set_balance(self, user_id: int, amount: int) -> None:
        self.balances[user_id] = amount
        self._save_data()

    def add_balance(self, user_id: int, amount: int) -> None:
        current_balance = self.get_balance(user_id)
        self.set_balance(user_id, current_balance + amount)

    def subtract_balance(self, user_id: int, amount: int) -> None:
        current_balance = self.get_balance(user_id)
        self.set_balance(user_id, current_balance - amount)

    def get_jackpot(self) -> int:
        return self.jackpot

    def set_jackpot(self, amount: int) -> None:
        self.jackpot = amount
        self._save_data()

    def add_jackpot(self, amount: int) -> None:
        self.jackpot += amount
        self._save_data()

    def subtract_jackpot(self, amount: int) -> None:
        self.jackpot -= amount
        self._save_data()

    def get_sorted_balances(self) -> List[Tuple[int, int]]:
        return sorted(
            self.balances.items(),
            key=lambda item: item[1],
            reverse=True
        )

class GamblingService:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def calculate_tax(self, income: int, game_type: Optional[str] = None) -> int:
        if income <= 0:
            return 0

        if game_type in ["coin", "dice", "blackjack", "baccarat", "indian_poker"]:
            for threshold, rate in GamblingConfig.SECURITIES_TRANSACTION_TAX_BRACKETS:
                if income > threshold:
                    return int(income * rate)
            return 0

        for threshold, rate in GamblingConfig.INCOME_TAX_BRACKETS:
            if income > threshold:
                return int(income * rate)
        return 0

    def calculate_gift_tax(self, amount: int) -> int:
        for threshold, rate in GamblingConfig.GIFT_TAX_BRACKETS:
            if amount > threshold:
                return int(amount * rate)
        return 0

    def validate_bet(self, bet: Optional[int], user_id: Optional[int] = None) -> Optional[discord.Embed]:
        if isinstance(bet, str) and bet == "올인" and user_id is not None:
            bet = self.data_manager.get_balance(user_id)

        if (bet is None) or (bet < GamblingConfig.MIN_BET):
            return GamblingEmbed.create_error_embed("100원 이상 베팅하세요")

        if bet >= GamblingConfig.MAX_BET:
            return GamblingEmbed.create_error_embed("100조원 이상 베팅할 수 없습니다")

        return None

    def get_card_value(self, card: str) -> int:
        if card in ['J', 'Q', 'K']:
            return 10
        elif card == 'A':
            return 11
        return int(card)

    def calculate_hand_value(self, hand: List[str]) -> int:
        value = 0
        aces = 0

        for card in hand:
            if card == 'A':
                aces += 1
            else:
                value += self.get_card_value(card)

        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1

        return value

    def calculate_baccarat_value(self, hand: List[str]) -> int:
        value = 0
        for card in hand:
            if card in ['J', 'Q', 'K', '10']:
                continue
            elif card == 'A':
                value += 1
            else:
                value += int(card)
        return value % 10

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns: Dict[str, datetime] = {}
        self.blackjack_players: set = set()
        self.baccarat_players: set = set()
        self.indian_poker_players: set = set()
        self.coin_players: set = set()
        self.dice_players: set = set()
        self.data_manager = DataManager('gambling_data.json')
        self.gambling_service = GamblingService(self.data_manager)
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
                self.data_manager.set_jackpot(GamblingConfig.INITIAL_JACKPOT)
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
        lock = self.data_manager._get_lock(author_id)
        if not lock.acquire(timeout=5):
            return GamblingEmbed.create_error_embed("서버 이슈")

        try:
            is_correct = (guess == result)
            if is_correct:
                multiplier = random.uniform(*GamblingConfig.GAME_MULTIPLIER_RANGES[game_type])
                winnings = int(bet * multiplier)
                tax = self.gambling_service.calculate_tax(winnings, game_type)
                winnings_after_tax = winnings - tax
                self.data_manager.add_balance(author_id, winnings_after_tax)
            else:
                winnings = -bet
                tax = None
                self.data_manager.subtract_balance(author_id, bet)

            return GamblingEmbed.create_game_embed(
                author_name=author_name,
                is_correct=is_correct,
                guess=guess,
                result=result,
                bet=bet,
                winnings=winnings_after_tax if is_correct else winnings,
                balance=self.data_manager.get_balance(author_id),
                game_type=game_type,
                tax=tax
            )
        finally:
            lock.release()

    @commands.command(name="도박.동전", description="동전 던지기")
    async def coin(self, ctx, bet: str = None):
        self.coin_players.add(ctx.author.id)
        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "coin"):
            await ctx.reply(embed=cooldown_embed)
            return

        try:
            bet = int(bet) if bet != "올인" else self.data_manager.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if error_embed := self.gambling_service.validate_bet(bet, ctx.author.id):
            await ctx.reply(embed=error_embed)
            return

        if bet > self.data_manager.get_balance(ctx.author.id):
            await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
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
            self.coin_players.remove(ctx.author.id)

    @commands.command(name="도박.주사위", description="주사위")
    async def dice(self, ctx, bet: str = None):
        self.dice_players.add(ctx.author.id)
        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "dice"):
            await ctx.reply(embed=cooldown_embed)
            return

        try:
            bet = int(bet) if bet != "올인" else self.data_manager.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if error_embed := self.gambling_service.validate_bet(bet, ctx.author.id):
            await ctx.reply(embed=error_embed)
            return

        if bet > self.data_manager.get_balance(ctx.author.id):
            await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
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
            self.dice_players.remove(ctx.author.id)

    @commands.command(name="도박.잭팟", description="잭팟")
    async def jackpot(self, ctx, bet: str = None):
        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "jackpot"):
            await ctx.reply(embed=cooldown_embed)
            return

        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "jackpot_win"):
            await ctx.reply(embed=cooldown_embed)
            return

        try:
            bet = int(bet) if bet != "올인" else self.data_manager.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if bet is None or bet < GamblingConfig.MIN_JACKPOT_BET:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("1,000원 이상 베팅하세요"))
            return

        if bet >= GamblingConfig.MAX_BET:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("100조원 이상 베팅할 수 없습니다"))
            return

        with self.data_manager._get_lock(ctx.author.id):
            current_balance = self.data_manager.get_balance(ctx.author.id)
            min_bet = current_balance // 100

            if bet > current_balance:
                await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
                return

            if bet < min_bet:
                await ctx.reply(embed=GamblingEmbed.create_error_embed(
                    f"현재 재산의 1% 이상 베팅하세요. (최소 {min_bet:,}원)"))
                return

            self.data_manager.subtract_balance(ctx.author.id, bet)
            self.data_manager.add_jackpot(bet)

            if secrets.randbelow(100) <= 1:  # 1% 확률
                winnings = self.data_manager.get_jackpot() // 10
                tax = self.gambling_service.calculate_tax(winnings)
                winnings_after_tax = winnings - tax
                self.data_manager.add_balance(ctx.author.id, winnings_after_tax)
                self.data_manager.subtract_jackpot(winnings)
                self.cooldowns[f"jackpot_win_{ctx.author.id}"] = datetime.now()
                
                embed = discord.Embed(
                    title=f"🎉 {ctx.author.name} 당첨",
                    description=(
                        f"- 현재 잭팟: {self.data_manager.get_jackpot():,}원(-{winnings:,})\n"
                        f"## 수익: {winnings_after_tax:,}원(세금: {tax:,}원)\n"
                        f"- 재산: {self.data_manager.get_balance(ctx.author.id):,}원(+{winnings_after_tax:,})"
                    ),
                    color=discord.Color.gold()
                )
            else:
                embed = discord.Embed(
                    title=f"🎰 {ctx.author.name} 잭팟 실패ㅋ",
                    description=(
                        f"- 현재 잭팟: {self.data_manager.get_jackpot():,}원\n"
                        f"## 수익: -{bet:,}원\n"
                        f"- 재산: {self.data_manager.get_balance(ctx.author.id):,}원"
                    ),
                    color=discord.Color.red()
                )

            await ctx.reply(embed=embed)

    @commands.command(name="도박.노동", aliases=['도박.일', '도박.돈'], description="도박.노동")
    async def work(self, ctx):
        with self.data_manager._get_lock(ctx.author.id):
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
                self.data_manager.add_balance(ctx.author.id, amount)
                embed = discord.Embed(
                    title=f"☭ {ctx.author.name} 노동",
                    description=(
                        f"정당한 노동을 통해 {amount:,}원을 벌었다.\n"
                        f"- 재산: {self.data_manager.get_balance(ctx.author.id):,}원(+{amount:,})"
                    ),
                    color=discord.Color.green()
                )
                self.cooldowns[ctx.author.id] = current_time

            await ctx.reply(embed=embed)

    @commands.command(name="도박.지갑", aliases=['도박.잔액', '도박.직바'], description="잔액 확인")
    async def balance(self, ctx):
        with self.data_manager._get_lock(ctx.author.id):
            balance = self.data_manager.get_balance(ctx.author.id)
            embed = discord.Embed(
                title=f"💰 {ctx.author.name}의 지갑",
                description=f"현재 잔액: {balance:,}원",
                color=discord.Color.blue()
            )
            await ctx.reply(embed=embed)

    @commands.command(name="도박.랭킹", description="랭킹")
    async def ranking(self, ctx):
        with self.data_manager.global_lock:
            sorted_balances = self.data_manager.get_sorted_balances()
            top_3 = sorted_balances[:3]

            description_lines = []
            for i, (user_id, balance) in enumerate(top_3):
                user = await self.bot.fetch_user(user_id)
                description_lines.append(f"{i+1}. {user.name}: {balance:,}원")

            embed = discord.Embed(
                title="🏅 상위 3명 랭킹",
                description="\n".join(description_lines) if description_lines else "랭킹이 없습니다.",
                color=discord.Color.blue()
            )
            await ctx.reply(embed=embed)

    @commands.command(name="도박.전체랭킹", description="전체 랭킹")
    async def all_ranking(self, ctx):
        with self.data_manager.global_lock:
            sorted_balances = self.data_manager.get_sorted_balances()
            member_dict = {member.id: member.display_name for member in ctx.guild.members} if ctx.guild else {}

            pages = []
            page_size = 10
            total_users = len(sorted_balances)

            for page_num in range((total_users + page_size - 1) // page_size):
                start_idx = page_num * page_size
                end_idx = min(start_idx + page_size, total_users)
                page_users = sorted_balances[start_idx:end_idx]
                page_lines = []

                for rank, (user_id, balance) in enumerate(page_users, start=start_idx + 1):
                    username = member_dict.get(user_id)
                    if not username:
                        try:
                            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                            username = user.name
                        except:
                            username = f"알 수 없음({user_id})"
                    page_lines.append(f"{rank}. {username}: {balance:,}원")

                pages.append("\n".join(page_lines))

            if not pages:
                embed = discord.Embed(
                    title="🏅 전체 랭킹",
                    description="랭킹 정보가 없습니다.",
                    color=discord.Color.blue()
                )
                await ctx.reply(embed=embed)
                return

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
            amount = int(amount) if amount != "올인" else self.data_manager.get_balance(ctx.author.id)
        except ValueError:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("올바른 금액을 입력하세요"))
            return

        if amount <= GamblingConfig.MIN_JACKPOT_BET:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("1,000원 이하는 송금할 수 없습니다."))
            return

        if amount >= GamblingConfig.MAX_BET:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("100조원 이상 송금할 수 없습니다"))
            return

        with self.data_manager._get_lock(ctx.author.id), self.data_manager._get_lock(recipient.id):
            sender_balance = self.data_manager.get_balance(ctx.author.id)

            if amount > sender_balance:
                await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
                return

            tax = self.gambling_service.calculate_gift_tax(amount)
            amount_after_tax = amount - tax

            self.data_manager.subtract_balance(ctx.author.id, amount)
            self.data_manager.add_balance(recipient.id, amount_after_tax)
            self.data_manager.add_jackpot(tax)

            embed = discord.Embed(
                title="💸 송금 완료",
                description=(
                    f"{ctx.author.name} → {recipient.name}\n"
                    f"## {amount:,}원 송금(세금: {tax:,}원)\n"
                    f"- 잔액: {self.data_manager.get_balance(ctx.author.id):,}원"
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
            bet = int(bet) if bet != "올인" else self.data_manager.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if error_embed := self.gambling_service.validate_bet(bet, ctx.author.id):
            await ctx.reply(embed=error_embed)
            return

        if bet > self.data_manager.get_balance(ctx.author.id):
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
                            with self.data_manager._get_lock(ctx.author.id):
                                self.data_manager.subtract_balance(ctx.author.id, bet)

                            embed = discord.Embed(
                                title=f"🃏 {ctx.author.name} 버스트!",
                                description=(
                                    f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                                    f"JEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n"
                                    f"## 수익: {bet:,}원 × -1 = -{bet:,}원\n"
                                    f"- 재산: {self.data_manager.get_balance(ctx.author.id):,}원"
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

                        with self.data_manager._get_lock(ctx.author.id):
                            if dealer_value > 21 or player_value > dealer_value:
                                multiplier = 2.0 if player_value == 21 else random.uniform(*GamblingConfig.GAME_MULTIPLIER_RANGES["blackjack"])
                                winnings = int(bet * multiplier)
                                tax = self.gambling_service.calculate_tax(winnings, "blackjack")
                                winnings_after_tax = winnings - tax
                                self.data_manager.add_balance(ctx.author.id, winnings_after_tax)

                                embed = discord.Embed(
                                    title=f"🃏 {ctx.author.name} 승리",
                                    description=(
                                        f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                                        f"JEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n"
                                        f"## 수익: {bet:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)\n"
                                        f"- 재산: {self.data_manager.get_balance(ctx.author.id):,}원"
                                    ),
                                    color=discord.Color.green()
                                )
                            else:
                                self.data_manager.subtract_balance(ctx.author.id, bet)
                                embed = discord.Embed(
                                    title=f"🃏 {ctx.author.name} {'패배' if player_value < dealer_value else '무승부'}",
                                    description=(
                                        f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                                        f"JEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n"
                                        f"## 수익: {bet:,}원 × -1 = -{bet:,}원\n"
                                        f"- 재산: {self.data_manager.get_balance(ctx.author.id):,}원"
                                    ),
                                    color=discord.Color.red()
                                )

                            await game_message.edit(embed=embed)
                            return

                except asyncio.TimeoutError:
                    with self.data_manager._get_lock(ctx.author.id):
                        self.data_manager.subtract_balance(ctx.author.id, bet)
                        embed = discord.Embed(
                            title="⏳️ 시간 초과",
                            description=f"30초 동안 응답이 없어 베팅금 {bet:,}원을 잃었습니다.\n- 재산: {self.data_manager.get_balance(ctx.author.id):,}원",
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
            bet = int(bet) if bet != "올인" else self.data_manager.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if error_embed := self.gambling_service.validate_bet(bet, ctx.author.id):
            await ctx.reply(embed=error_embed)
            return

        if bet > self.data_manager.get_balance(ctx.author.id):
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

                with self.data_manager._get_lock(ctx.author.id):
                    if guess == result:
                        multiplier = 8 if result == "Tie" else random.uniform(*GamblingConfig.GAME_MULTIPLIER_RANGES["baccarat"])
                        winnings = int(bet * multiplier)
                        tax = self.gambling_service.calculate_tax(winnings, "baccarat")
                        winnings_after_tax = winnings - tax
                        self.data_manager.add_balance(ctx.author.id, winnings_after_tax - bet)

                        embed = discord.Embed(
                            title=f"🃏 {ctx.author.name} 맞음 ㄹㅈㄷ",
                            description=(
                                f"{ctx.author.name}: {' '.join(player_hand)} (합계: {player_value})\n"
                                f"JEE6: {' '.join(banker_hand)} (합계: {banker_value})\n"
                                f"## 수익: {bet:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)\n"
                                f"- 재산: {self.data_manager.get_balance(ctx.author.id):,}원"
                            ),
                            color=discord.Color.green()
                        )
                    else:
                        self.data_manager.subtract_balance(ctx.author.id, bet)
                        embed = discord.Embed(
                            title=f"🃏 {ctx.author.name} 틀림ㅋ",
                            description=(
                                f"{ctx.author.name}: {' '.join(player_hand)} (합계: {player_value})\n"
                                f"JEE6: {' '.join(banker_hand)} (합계: {banker_value})\n"
                                f"## 수익: {bet:,}원 × -1 = -{bet:,}원\n"
                                f"- 재산: {self.data_manager.get_balance(ctx.author.id):,}원"
                            ),
                            color=discord.Color.red()
                        )

                    await game_message.edit(embed=embed)

            except asyncio.TimeoutError:
                with self.data_manager._get_lock(ctx.author.id):
                    self.data_manager.subtract_balance(ctx.author.id, bet)
                    embed = discord.Embed(
                        title="⏳️ 시간 초과",
                        description=f"30초 동안 응답이 없어 베팅금 {bet:,}원을 잃었습니다.\n- 재산: {self.data_manager.get_balance(ctx.author.id):,}원",
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
            bet = int(bet) if bet != "올인" else self.data_manager.get_balance(ctx.author.id)
        except (ValueError, TypeError):
            bet = None

        if error_embed := self.gambling_service.validate_bet(bet, ctx.author.id):
            await ctx.reply(embed=error_embed)
            return

        if bet > self.data_manager.get_balance(ctx.author.id):
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

                with self.data_manager._get_lock(ctx.author.id):
                    if str(reaction.emoji) == "💀":  # 다이
                        loss = bet // 2
                        self.data_manager.subtract_balance(ctx.author.id, loss)
                        embed = discord.Embed(
                            title=f"🃏 {ctx.author.name} Die",
                            description=(
                                f"{ctx.author.name}의 카드: {player_card}\n"
                                f"JEE6의 카드: {banker_card}\n"
                                f"## 수익: {bet:,}원 × -0.5 = -{loss:,}원\n"
                                f"- 재산: {self.data_manager.get_balance(ctx.author.id):,}원"
                            ),
                            color=discord.Color.red()
                        )
                    else:  # 콜
                        if player_card > banker_card:
                            multiplier = random.uniform(*GamblingConfig.GAME_MULTIPLIER_RANGES["indian_poker"])
                            winnings = int(bet * multiplier)
                            tax = self.gambling_service.calculate_tax(winnings, "indian_poker")
                            winnings_after_tax = winnings - tax
                            self.data_manager.add_balance(ctx.author.id, winnings_after_tax)
                            embed = discord.Embed(
                                title=f"🃏 {ctx.author.name} 승리",
                                description=(
                                    f"{ctx.author.name}의 카드: {player_card}\n"
                                    f"JEE6의 카드: {banker_card}\n"
                                    f"## 수익: {bet:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)\n"
                                    f"- 재산: {self.data_manager.get_balance(ctx.author.id):,}원"
                                ),
                                color=discord.Color.green()
                            )
                        else:
                            self.data_manager.subtract_balance(ctx.author.id, bet)
                            embed = discord.Embed(
                                title=f"🃏 {ctx.author.name} 패배",
                                description=(
                                    f"{ctx.author.name}의 카드: {player_card}\n"
                                    f"JEE6의 카드: {banker_card}\n"
                                    f"## 수익: {bet:,}원 × -1 = -{bet:,}원\n"
                                    f"- 재산: {self.data_manager.get_balance(ctx.author.id):,}원"
                                ),
                                color=discord.Color.red()
                            )

                    await game_message.edit(embed=embed)

            except asyncio.TimeoutError:
                with self.data_manager._get_lock(ctx.author.id):
                    self.data_manager.subtract_balance(ctx.author.id, bet)
                    embed = discord.Embed(
                        title="⏳️ 시간 초과",
                        description=f"30초 동안 응답이 없어 베팅금 {bet:,}원을 잃었습니다.\n- 재산: {self.data_manager.get_balance(ctx.author.id):,}원",
                        color=discord.Color.red()
                    )
                await game_message.edit(embed=embed)

        finally:
            self.indian_poker_players.remove(ctx.author.id)

    async def cog_check(self, ctx):
        if ctx.author.id in self.blackjack_players and ctx.command.name == "도박.블랙잭":
            await ctx.reply(embed=GamblingEmbed.create_error_embed("이미 블랙잭 게임이 진행 중입니다."))
            return False
        if ctx.author.id in self.baccarat_players and ctx.command.name == "도박.바카라":
            await ctx.reply(embed=GamblingEmbed.create_error_embed("이미 바카라 게임이 진행 중입니다."))
            return False
        if ctx.author.id in self.indian_poker_players and ctx.command.name == "도박.인디언":
            await ctx.reply(embed=GamblingEmbed.create_error_embed("이미 인디언 포커 게임이 진행 중입니다."))
            return False
        if ctx.author.id in self.coin_players and ctx.command.name == "도박.동전":
            await ctx.reply(embed=GamblingEmbed.create_error_embed("이미 동전 게임이 진행 중입니다."))
            return False
        if ctx.author.id in self.dice_players and ctx.command.name == "도박.주사위":
            await ctx.reply(embed=GamblingEmbed.create_error_embed("이미 주사위 게임이 진행 중입니다."))
            return False
        return True