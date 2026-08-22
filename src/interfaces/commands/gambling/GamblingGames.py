import discord
from discord.ext import commands
import logging
import random
import secrets
import asyncio

from src.interfaces.commands.Base import BaseCommand
from src.services.GamblingService import GamblingService, GamblingManager
from src.utils.embeds.GamblingEmbed import GamblingEmbed
from src.config.settings.gamblingSettings import (
    MIN_BET,
    MAX_BET,
    GAME_COOLDOWN,
    GAME_MULTIPLIER_RANGES,
)

logger = logging.getLogger(__name__)


class GamblingGames(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.gambling_service = GamblingService()
        self.game_manager = GamblingManager()
        self.blackjack_players = set()
        self.baccarat_players = set()
        self.indian_poker_players = set()
        self.coin_players = set()
        self.dice_players = set()

    async def _parse_bet_amount(
        self, bet_str: str, user_id: int, server_id: int
    ) -> int:
        if bet_str == "올인":
            return await self.gambling_service.get_balance(user_id, server_id)
        try:
            return int(bet_str)
        except (ValueError, TypeError):
            return None

    async def _play_game(
        self,
        ctx,
        user_id: int,
        server_id: int,
        guess: str,
        result: str,
        bet: int,
        game_type: str,
    ) -> discord.Embed:
        lock = await self.gambling_service._get_lock(user_id)
        try:
            async with lock:
                is_correct = guess == result
                if is_correct:
                    multiplier = random.uniform(*GAME_MULTIPLIER_RANGES[game_type])
                    winnings = int(bet * multiplier)
                    tax = self.gambling_service.calculate_tax(winnings, game_type)
                    winnings_after_tax = winnings - tax
                    balance = await self.gambling_service.add_balance(
                        user_id, server_id, winnings_after_tax
                    )
                    return GamblingEmbed.create_game_embed(
                        author_name=ctx.author.name,
                        is_correct=True,
                        guess=guess,
                        result=result,
                        bet=bet,
                        winnings=winnings_after_tax,
                        balance=balance,
                        game_type=game_type,
                        tax=tax,
                    )
                else:
                    balance = await self.gambling_service.subtract_balance(
                        user_id, server_id, bet
                    )
                    return GamblingEmbed.create_game_embed(
                        author_name=ctx.author.name,
                        is_correct=False,
                        guess=guess,
                        result=result,
                        bet=bet,
                        winnings=-bet,
                        balance=balance,
                        game_type=game_type,
                    )
        except Exception as e:
            logger.error(f"게임 진행 중 오류: {e}")
            return GamblingEmbed.create_error_embed("게임 진행 중 오류가 발생했습니다.")

    @commands.command(name="도박.동전", description="동전 던지기")
    async def coin(self, ctx, bet: str = None):
        user_id = ctx.author.id
        server_id = ctx.guild.id
        if not await self.game_manager.start_game(user_id, "coin"):
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(
                    "이미 다른 게임이 진행 중입니다."
                )
            )
            return
        self.coin_players.add(user_id)
        try:
            remaining = await self.gambling_service.check_cooldown(
                user_id, "coin", GAME_COOLDOWN
            )
            if remaining:
                await ctx.reply(embed=GamblingEmbed.create_cooldown_embed(remaining))
                return
            bet_amount = await self._parse_bet_amount(bet, user_id, server_id)
            if error_msg := self.gambling_service.validate_bet(
                bet_amount, MIN_BET, MAX_BET
            ):
                await ctx.reply(embed=GamblingEmbed.create_error_embed(error_msg))
                return
            balance = await self.gambling_service.get_balance(user_id, server_id)
            if bet_amount > balance:
                await ctx.reply(
                    embed=GamblingEmbed.create_error_embed("돈이 부족해...")
                )
                return
            embed = discord.Embed(
                title=f"🪙 {ctx.author.name}의 동전 게임",
                description="앞면 또는 뒷면을 선택하세요",
                color=discord.Color.blue(),
            )
            embed.add_field(name="선택", value="⭕ 앞면 / ❌ 뒷면", inline=False)
            game_message = await ctx.reply(embed=embed)
            await game_message.add_reaction("⭕")
            await game_message.add_reaction("❌")
            await self.gambling_service.set_cooldown(user_id, "coin")

            def check(reaction, user):
                return (
                    user.id == user_id
                    and str(reaction.emoji) in ["⭕", "❌"]
                    and reaction.message.id == game_message.id
                )

            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=30.0, check=check
                )
                guess = "앞" if str(reaction.emoji) == "⭕" else "뒤"
                result = secrets.choice(["앞", "뒤"])
                embed = await self._play_game(
                    ctx, user_id, server_id, guess, result, bet_amount, "coin"
                )
                await game_message.edit(embed=embed)
            except asyncio.TimeoutError:
                embed = GamblingEmbed.create_error_embed(
                    "30초 동안 응답이 없어 취소됐어요"
                )
                await game_message.edit(embed=embed)
        except Exception as e:
            logger.error(f"동전 게임 처리 중 오류: {e}")
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )
        finally:
            self.coin_players.remove(user_id)
            await self.game_manager.end_game(user_id)

    @commands.command(name="도박.주사위", description="주사위 게임")
    async def dice(self, ctx, bet: str = None):
        user_id = ctx.author.id
        server_id = ctx.guild.id
        if not await self.game_manager.start_game(user_id, "dice"):
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(
                    "이미 다른 게임이 진행 중입니다."
                )
            )
            return
        self.dice_players.add(user_id)
        try:
            remaining = await self.gambling_service.check_cooldown(
                user_id, "dice", GAME_COOLDOWN
            )
            if remaining:
                await ctx.reply(embed=GamblingEmbed.create_cooldown_embed(remaining))
                return
            bet_amount = await self._parse_bet_amount(bet, user_id, server_id)
            if error_msg := self.gambling_service.validate_bet(
                bet_amount, MIN_BET, MAX_BET
            ):
                await ctx.reply(embed=GamblingEmbed.create_error_embed(error_msg))
                return
            balance = await self.gambling_service.get_balance(user_id, server_id)
            if bet_amount > balance:
                await ctx.reply(
                    embed=GamblingEmbed.create_error_embed("돈이 부족해...")
                )
                return
            embed = discord.Embed(
                title=f"🎲 {ctx.author.name}의 주사위 게임",
                description="1부터 6까지 숫자를 선택하세요",
                color=discord.Color.blue(),
            )
            embed.add_field(name="선택", value="1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣", inline=False)
            game_message = await ctx.reply(embed=embed)
            reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
            for reaction in reactions:
                await game_message.add_reaction(reaction)
            await self.gambling_service.set_cooldown(user_id, "dice")

            def check(reaction, user):
                return (
                    user.id == user_id
                    and str(reaction.emoji) in reactions
                    and reaction.message.id == game_message.id
                )

            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=30.0, check=check
                )
                guess = str(reactions.index(str(reaction.emoji)) + 1)
                result = str(secrets.randbelow(6) + 1)
                embed = await self._play_game(
                    ctx, user_id, server_id, guess, result, bet_amount, "dice"
                )
                await game_message.edit(embed=embed)
            except asyncio.TimeoutError:
                embed = GamblingEmbed.create_error_embed(
                    "30초 동안 응답이 없어 취소됐어요"
                )
                await game_message.edit(embed=embed)
        except Exception as e:
            logger.error(f"주사위 게임 처리 중 오류: {e}")
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )
        finally:
            self.dice_players.remove(user_id)
            await self.game_manager.end_game(user_id)
