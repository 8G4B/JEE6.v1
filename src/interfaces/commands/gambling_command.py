import discord
from discord.ext import commands, tasks
import logging
import random
import secrets
import asyncio
from datetime import datetime

from src.interfaces.commands.base import BaseCommand
from src.services.gambling_service import GamblingService, GamblingManager
from src.utils.embeds.GamblingEmbed import GamblingEmbed
from src.config.settings.gambling_settings import (
    MIN_JACKPOT_BET,
    MAX_BET,
    JACKPOT_WIN_COOLDOWN,
    GAME_COOLDOWN,
    WORK_COOLDOWN,
    RESET_TIMES,
    WORK_REWARD_RANGE,
)

logger = logging.getLogger(__name__)


class GamblingCommands(BaseCommand):

    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.gambling_service = GamblingService()
        self.game_manager = GamblingManager()

        self.blackjack_players = set()
        self.baccarat_players = set()
        self.indian_poker_players = set()
        self.coin_players = set()
        self.dice_players = set()

        self.reset_jackpot.start()

    def cog_unload(self):
        self.reset_jackpot.cancel()

    @tasks.loop(seconds=60)
    async def reset_jackpot(self):
        now = datetime.now()
        for hour, minute in RESET_TIMES:
            if now.hour == hour and now.minute == minute:
                logger.info(f"잭팟 리셋 시간: {hour}:{minute}")
                break

    async def _parse_bet_amount(
        self, bet_str: str, user_id: int, server_id: int
    ) -> int:
        if bet_str == "올인":
            return await self.gambling_service.get_balance(user_id, server_id)
        try:
            return int(bet_str)
        except ValueError:
            return None

    @commands.command(
        name="도박.지갑", aliases=["도박.잔액", "도박.직바"], description="잔액 확인"
    )
    async def balance(self, ctx):
        user_id = ctx.author.id
        server_id = ctx.guild.id

        lock = await self.gambling_service._get_lock(user_id)
        async with lock:
            balance = await self.gambling_service.get_balance(user_id, server_id)
            embed = GamblingEmbed.create_balance_embed(ctx.author.name, balance)
            await ctx.reply(embed=embed)

    @commands.command(
        name="도박.노동", aliases=["도박.일", "도박.돈"], description="도박.노동"
    )
    async def work(self, ctx):
        user_id = ctx.author.id
        server_id = ctx.guild.id

        if not await self.game_manager.start_game(user_id, "work"):
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(
                    "이미 다른 게임이 진행 중입니다."
                )
            )
            return

        try:
            remaining = await self.gambling_service.check_cooldown(
                user_id, "work", WORK_COOLDOWN
            )
            if remaining:
                embed = GamblingEmbed.create_cooldown_embed(remaining)
                await ctx.reply(embed=embed)
                return

            lock = await self.gambling_service._get_lock(user_id)
            async with lock:
                amount = random.randint(*WORK_REWARD_RANGE)
                await self.gambling_service.add_balance(user_id, server_id, amount)

                balance = await self.gambling_service.get_balance(user_id, server_id)
                embed = GamblingEmbed.create_work_embed(
                    ctx.author.name, amount, balance
                )
                await ctx.reply(embed=embed)

                await self.gambling_service.set_cooldown(user_id, "work")

        finally:
            await self.game_manager.end_game(user_id)

    @commands.command(name="도박.랭킹", description="랭킹")
    async def ranking(self, ctx):
        server_id = ctx.guild.id

        async with ctx.typing():
            rankings = await self.gambling_service.get_cached_rankings(
                server_id, self.bot, 3
            )
            top_3 = rankings[:3]

            description_lines = []
            for i, (_, username, balance) in enumerate(top_3):
                description_lines.append(f"{i+1}. {username}: {balance:,}원")

            embed = GamblingEmbed.create_ranking_embed(
                "🏅 상위 3명 랭킹",
                (
                    "\n".join(description_lines)
                    if description_lines
                    else "랭킹이 없습니다."
                ),
            )
            await ctx.reply(embed=embed)

    @commands.command(name="도박.전체랭킹", description="전체 랭킹")
    async def all_ranking(self, ctx):
        server_id = ctx.guild.id

        async with ctx.typing():
            rankings = await self.gambling_service.get_cached_rankings(
                server_id, self.bot, 100
            )

            if not rankings:
                embed = GamblingEmbed.create_ranking_embed(
                    "🏅 전체 랭킹", "랭킹 정보가 없습니다."
                )
                await ctx.reply(embed=embed)
                return

            pages = []
            page_size = 10

            for i in range(0, len(rankings), page_size):
                page_users = rankings[i : i + page_size]
                page_lines = []

                for rank, (_, username, balance) in enumerate(page_users, start=i + 1):
                    page_lines.append(f"{rank}. {username}: {balance:,}원")

                pages.append("\n".join(page_lines))

            current_page = 0
            embed = GamblingEmbed.create_ranking_embed(
                "🏅 전체 랭킹", pages[current_page]
            )
            embed.set_footer(text=f"{current_page + 1}/{len(pages)}")

            message = await ctx.reply(embed=embed)

            if len(pages) > 1:
                await message.add_reaction("◀️")
                await message.add_reaction("▶️")

                def check(reaction, user):
                    return (
                        user == ctx.author
                        and str(reaction.emoji) in ["◀️", "▶️"]
                        and reaction.message.id == message.id
                    )

                while True:
                    try:
                        reaction, user = await self.bot.wait_for(
                            "reaction_add", timeout=30.0, check=check
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
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(
                    "!도박.송금 [유저] [금액] <-- 이렇게 써"
                )
            )
            return

        sender_id = ctx.author.id
        recipient_id = recipient.id
        server_id = ctx.guild.id

        if sender_id == recipient_id:
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(
                    "자기 자신에게는 송금할 수 없습니다."
                )
            )
            return

        try:
            amount_value = await self._parse_bet_amount(amount, sender_id, server_id)
        except ValueError:
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed("올바른 금액을 입력하세요")
            )
            return

        if amount_value is None:
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed("올바른 금액을 입력하세요")
            )
            return

        if amount_value <= MIN_JACKPOT_BET:
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(
                    f"{MIN_JACKPOT_BET:,}원 이하는 송금할 수 없습니다."
                )
            )
            return

        if amount_value >= MAX_BET:
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(
                    f"{MAX_BET:,}원 이상 송금할 수 없습니다"
                )
            )
            return

        sender_lock = await self.gambling_service._get_lock(sender_id)
        recipient_lock = await self.gambling_service._get_lock(recipient_id)

        async with sender_lock:
            async with recipient_lock:
                sender_balance = await self.gambling_service.get_balance(
                    sender_id, server_id
                )

                if amount_value > sender_balance:
                    await ctx.reply(
                        embed=GamblingEmbed.create_error_embed("돈이 부족해...")
                    )
                    return

                tax = self.gambling_service.calculate_gift_tax(amount_value)
                amount_after_tax = amount_value - tax

                await self.gambling_service.subtract_balance(
                    sender_id, server_id, amount_value
                )
                await self.gambling_service.add_balance(
                    recipient_id, server_id, amount_after_tax
                )
                await self.gambling_service.add_jackpot(server_id, tax)

                sender_balance = await self.gambling_service.get_balance(
                    sender_id, server_id
                )
                embed = GamblingEmbed.create_transfer_embed(
                    ctx.author.name, recipient.name, amount_value, tax, sender_balance
                )
                await ctx.reply(embed=embed)

    @commands.command(name="도박.잭팟", description="잭팟")
    async def jackpot(self, ctx, bet: str = None):
        user_id = ctx.author.id
        server_id = ctx.guild.id

        if not await self.game_manager.start_game(user_id, "jackpot"):
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(
                    "이미 다른 게임이 진행 중입니다."
                )
            )
            return

        try:
            remaining = await self.gambling_service.check_cooldown(
                user_id, "jackpot", GAME_COOLDOWN
            )
            if remaining:
                await ctx.reply(embed=GamblingEmbed.create_cooldown_embed(remaining))
                return

            remaining = await self.gambling_service.check_cooldown(
                user_id, "jackpot_win", JACKPOT_WIN_COOLDOWN
            )
            if remaining:
                minutes = remaining // 60
                seconds = remaining % 60
                time_str = f"{minutes}분 {seconds}초" if minutes > 0 else f"{seconds}초"
                await ctx.reply(
                    embed=GamblingEmbed.create_error_embed(
                        f"{time_str} 후에 다시 시도해주세요."
                    )
                )
                return

            bet_amount = await self._parse_bet_amount(bet, user_id, server_id)

            if bet_amount is None or bet_amount < MIN_JACKPOT_BET:
                await ctx.reply(
                    embed=GamblingEmbed.create_error_embed(
                        f"{MIN_JACKPOT_BET:,}원 이상 베팅하세요"
                    )
                )
                return

            if bet_amount >= MAX_BET:
                await ctx.reply(
                    embed=GamblingEmbed.create_error_embed(
                        f"{MAX_BET:,}원 이상 베팅할 수 없습니다"
                    )
                )
                return

            lock = await self.gambling_service._get_lock(user_id)
            async with lock:
                current_balance = await self.gambling_service.get_balance(
                    user_id, server_id
                )
                min_bet = current_balance // 100

                if bet_amount > current_balance:
                    await ctx.reply(
                        embed=GamblingEmbed.create_error_embed("돈이 부족해...")
                    )
                    return

                if bet_amount < min_bet:
                    await ctx.reply(
                        embed=GamblingEmbed.create_error_embed(
                            f"현재 재산의 1% 이상 베팅하세요. (최소 {min_bet:,}원)"
                        )
                    )
                    return

                await self.gambling_service.subtract_balance(
                    user_id, server_id, bet_amount
                )
                await self.gambling_service.add_jackpot(server_id, bet_amount)

                if secrets.randbelow(100) <= 0:
                    jackpot = await self.gambling_service.get_jackpot(server_id)
                    winnings = jackpot // 10
                    tax = self.gambling_service.calculate_tax(winnings, "jackpot")
                    winnings_after_tax = winnings - tax

                    await self.gambling_service.add_balance(
                        user_id, server_id, winnings_after_tax
                    )
                    await self.gambling_service.subtract_jackpot(server_id, winnings)

                    await self.gambling_service.set_cooldown(user_id, "jackpot_win")

                    current_jackpot = await self.gambling_service.get_jackpot(server_id)
                    balance = await self.gambling_service.get_balance(
                        user_id, server_id
                    )

                    embed = GamblingEmbed.create_jackpot_embed(
                        f"🎉 {ctx.author.name} 당첨",
                        (
                            f"- 현재 잭팟: {current_jackpot:,}원(-{winnings:,})\n"
                            f"## 수익: {winnings_after_tax:,}원(세금: {tax:,}원)\n"
                            f"- 재산: {balance:,}원(+{winnings_after_tax:,})"
                        ),
                        discord.Color.gold(),
                    )
                else:
                    current_jackpot = await self.gambling_service.get_jackpot(server_id)
                    balance = await self.gambling_service.get_balance(
                        user_id, server_id
                    )

                    embed = GamblingEmbed.create_jackpot_embed(
                        f"🎰 {ctx.author.name} 잭팟 실패ㅋ",
                        (
                            f"- 현재 잭팟: {current_jackpot:,}원\n"
                            f"## 수익: -{bet_amount:,}원\n"
                            f"- 재산: {balance:,}원"
                        ),
                        discord.Color.red(),
                    )

                await self.gambling_service.set_cooldown(user_id, "jackpot")

                await ctx.reply(embed=embed)

        finally:
            await self.game_manager.end_game(user_id)

    async def cog_check(self, ctx):
        user_id = ctx.author.id

        if (
            user_id in self.blackjack_players
            or user_id in self.baccarat_players
            or user_id in self.indian_poker_players
            or user_id in self.coin_players
            or user_id in self.dice_players
        ):

            current_game = None
            if user_id in self.blackjack_players:
                current_game = "블랙잭"
            elif user_id in self.baccarat_players:
                current_game = "바카라"
            elif user_id in self.indian_poker_players:
                current_game = "인디언 포커"
            elif user_id in self.coin_players:
                current_game = "동전"
            elif user_id in self.dice_players:
                current_game = "주사위"

            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(
                    f"이미 {current_game} 게임이 진행 중입니다."
                )
            )
            return False

        return True
