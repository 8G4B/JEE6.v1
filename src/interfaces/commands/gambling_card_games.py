import discord
from discord.ext import commands
import logging
import random
import asyncio

from src.interfaces.commands.base import BaseCommand
from src.services.gambling_service import GamblingService, GamblingManager
from src.utils.embeds.gambling_embed import GamblingEmbed
from src.config.settings.gambling_settings import (
    MIN_BET,
    MAX_BET,
    GAME_COOLDOWN,
    GAME_MULTIPLIER_RANGES,
)

logger = logging.getLogger(__name__)


class GamblingCardGames(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.gambling_service = GamblingService()
        self.game_manager = GamblingManager()
        self.blackjack_players = set()
        self.baccarat_players = set()
        self.indian_poker_players = set()

    async def _parse_bet_amount(
        self, bet_str: str, user_id: int, server_id: int
    ) -> int:
        if bet_str == "올인":
            return await self.gambling_service.get_balance(user_id, server_id)
        try:
            return int(bet_str)
        except (ValueError, TypeError):
            return None

    @commands.command(name="도박.블랙잭", description="블랙잭 게임")
    async def blackjack(self, ctx, bet: str = None):
        user_id = ctx.author.id
        server_id = ctx.guild.id

        remaining = await self.gambling_service.check_cooldown(
            user_id, "blackjack", GAME_COOLDOWN
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
            await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
            return

        self.blackjack_players.add(user_id)

        try:
            await self.gambling_service.set_cooldown(user_id, "blackjack")

            cards = [
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
                "9",
                "10",
                "J",
                "Q",
                "K",
                "A",
            ] * 4
            random.shuffle(cards)

            player_hand = [cards.pop(), cards.pop()]
            dealer_hand = [cards.pop(), cards.pop()]

            player_value = self.gambling_service.calculate_hand_value(player_hand)
            dealer_value = self.gambling_service.calculate_hand_value(dealer_hand)

            embed = GamblingEmbed.create_blackjack_embed(
                title=f"🃏 {ctx.author.name}의 블랙잭",
                description=(
                    f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                    f"JEE6의 패: {dealer_hand[0]} ?"
                ),
                color=discord.Color.blue(),
            )

            game_message = await ctx.reply(embed=embed)
            await game_message.add_reaction("👊")
            await game_message.add_reaction("🛑")

            def check(reaction, user):
                return (
                    user.id == user_id
                    and str(reaction.emoji) in ["👊", "🛑"]
                    and reaction.message.id == game_message.id
                )

            while True:
                try:
                    reaction, _ = await self.bot.wait_for(
                        "reaction_add", timeout=30.0, check=check
                    )
                    await reaction.remove(ctx.author)

                    if str(reaction.emoji) == "👊":
                        player_hand.append(cards.pop())
                        player_value = self.gambling_service.calculate_hand_value(
                            player_hand
                        )

                        if player_value > 21:
                            lock = await self.gambling_service._get_lock(user_id)
                            async with lock:
                                await self.gambling_service.subtract_balance(
                                    user_id, server_id, bet_amount
                                )
                                balance = await self.gambling_service.get_balance(
                                    user_id, server_id
                                )

                            embed = discord.Embed(
                                title=f"🃏 {ctx.author.name} 버스트!",
                                description=(
                                    f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                                    f"JEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n"
                                    f"## 수익: {bet_amount:,}원 × -1 = -{bet_amount:,}원\n"
                                    f"- 재산: {balance:,}원"
                                ),
                                color=discord.Color.red(),
                            )
                            await game_message.edit(embed=embed)
                            break

                        embed = GamblingEmbed.create_blackjack_embed(
                            title=f"🃏 {ctx.author.name}의 블랙잭",
                            description=(
                                f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                                f"JEE6의 패: {dealer_hand[0]} ?"
                            ),
                            color=discord.Color.blue(),
                        )
                        await game_message.edit(embed=embed)

                    elif str(reaction.emoji) == "🛑":
                        while dealer_value < 17:
                            dealer_hand.append(cards.pop())
                            dealer_value = self.gambling_service.calculate_hand_value(
                                dealer_hand
                            )

                        lock = await self.gambling_service._get_lock(user_id)
                        async with lock:
                            if dealer_value > 21 or player_value > dealer_value:
                                multiplier = (
                                    2.0
                                    if player_value == 21
                                    else random.uniform(
                                        *GAME_MULTIPLIER_RANGES["blackjack"]
                                    )
                                )
                                winnings = int(bet_amount * multiplier)
                                tax = self.gambling_service.calculate_tax(
                                    winnings, "blackjack"
                                )
                                winnings_after_tax = winnings - tax

                                await self.gambling_service.add_balance(
                                    user_id, server_id, winnings_after_tax
                                )
                                balance = await self.gambling_service.get_balance(
                                    user_id, server_id
                                )

                                embed = discord.Embed(
                                    title=f"🃏 {ctx.author.name} 승리",
                                    description=(
                                        f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                                        f"JEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n"
                                        f"## 수익: {bet_amount:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)\n"
                                        f"- 재산: {balance:,}원"
                                    ),
                                    color=discord.Color.green(),
                                )
                            else:
                                await self.gambling_service.subtract_balance(
                                    user_id, server_id, bet_amount
                                )
                                balance = await self.gambling_service.get_balance(
                                    user_id, server_id
                                )

                                result = (
                                    "패배" if player_value < dealer_value else "무승부"
                                )
                                embed = discord.Embed(
                                    title=f"🃏 {ctx.author.name} {result}",
                                    description=(
                                        f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                                        f"JEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n"
                                        f"## 수익: {bet_amount:,}원 × -1 = -{bet_amount:,}원\n"
                                        f"- 재산: {balance:,}원"
                                    ),
                                    color=discord.Color.red(),
                                )

                            await game_message.edit(embed=embed)
                            break

                except asyncio.TimeoutError:
                    lock = await self.gambling_service._get_lock(user_id)
                    async with lock:
                        await self.gambling_service.subtract_balance(
                            user_id, server_id, bet_amount
                        )
                        balance = await self.gambling_service.get_balance(
                            user_id, server_id
                        )

                    embed = discord.Embed(
                        title="⏳️ 시간 초과",
                        description=f"30초 동안 응답이 없어 베팅금 {bet_amount:,}원을 잃었습니다.\n- 재산: {balance:,}원",
                        color=discord.Color.red(),
                    )
                    await game_message.edit(embed=embed)
                    break

        except Exception as e:
            logger.error(f"블랙잭 게임 처리 중 오류: {e}")
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )

        finally:
            self.blackjack_players.remove(user_id)

    @commands.command(name="도박.바카라", description="바카라 게임")
    async def baccarat(self, ctx, bet: str = None):
        user_id = ctx.author.id
        server_id = ctx.guild.id

        remaining = await self.gambling_service.check_cooldown(
            user_id, "baccarat", GAME_COOLDOWN
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
            await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
            return

        self.baccarat_players.add(user_id)

        try:
            await self.gambling_service.set_cooldown(user_id, "baccarat")

            embed = GamblingEmbed.create_baccarat_embed(
                title=f"🃏 {ctx.author.name}의 바카라",
                description="베팅할 곳을 선택하세요",
                color=discord.Color.blue(),
            )

            game_message = await ctx.reply(embed=embed)
            await game_message.add_reaction("👤")
            await game_message.add_reaction("🏦")
            await game_message.add_reaction("🤝")

            def check(reaction, user):
                return (
                    user.id == user_id
                    and str(reaction.emoji) in ["👤", "🏦", "🤝"]
                    and reaction.message.id == game_message.id
                )

            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=30.0, check=check
                )

                guess = {"👤": "Player", "🏦": "Banker", "🤝": "Tie"}[
                    str(reaction.emoji)
                ]

                cards = [
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                    "10",
                    "J",
                    "Q",
                    "K",
                    "A",
                ] * 4
                random.shuffle(cards)

                player_hand = [cards.pop(), cards.pop()]
                banker_hand = [cards.pop(), cards.pop()]

                player_value = self.gambling_service.calculate_baccarat_value(
                    player_hand
                )
                banker_value = self.gambling_service.calculate_baccarat_value(
                    banker_hand
                )

                if player_value <= 5:
                    player_hand.append(cards.pop())
                    player_value = self.gambling_service.calculate_baccarat_value(
                        player_hand
                    )

                if banker_value <= 5:
                    banker_hand.append(cards.pop())
                    banker_value = self.gambling_service.calculate_baccarat_value(
                        banker_hand
                    )

                if player_value > banker_value:
                    result = "Player"
                elif banker_value > player_value:
                    result = "Banker"
                else:
                    result = "Tie"

                lock = await self.gambling_service._get_lock(user_id)
                async with lock:
                    if guess == result:
                        multiplier = (
                            8
                            if result == "Tie"
                            else random.uniform(*GAME_MULTIPLIER_RANGES["baccarat"])
                        )
                        winnings = int(bet_amount * multiplier)
                        tax = self.gambling_service.calculate_tax(winnings, "baccarat")
                        winnings_after_tax = winnings - tax

                        await self.gambling_service.add_balance(
                            user_id, server_id, winnings_after_tax
                        )
                        balance = await self.gambling_service.get_balance(
                            user_id, server_id
                        )

                        embed = discord.Embed(
                            title=f"🃏 {ctx.author.name} 맞음 ㄹㅈㄷ",
                            description=(
                                f"{ctx.author.name}: {' '.join(player_hand)} (합계: {player_value})\n"
                                f"JEE6: {' '.join(banker_hand)} (합계: {banker_value})\n"
                                f"## 수익: {bet_amount:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)\n"
                                f"- 재산: {balance:,}원"
                            ),
                            color=discord.Color.green(),
                        )
                    else:
                        await self.gambling_service.subtract_balance(
                            user_id, server_id, bet_amount
                        )
                        balance = await self.gambling_service.get_balance(
                            user_id, server_id
                        )

                        embed = discord.Embed(
                            title=f"🃏 {ctx.author.name} 틀림ㅋ",
                            description=(
                                f"{ctx.author.name}: {' '.join(player_hand)} (합계: {player_value})\n"
                                f"JEE6: {' '.join(banker_hand)} (합계: {banker_value})\n"
                                f"## 수익: {bet_amount:,}원 × -1 = -{bet_amount:,}원\n"
                                f"- 재산: {balance:,}원"
                            ),
                            color=discord.Color.red(),
                        )

                await game_message.edit(embed=embed)

            except asyncio.TimeoutError:
                lock = await self.gambling_service._get_lock(user_id)
                async with lock:
                    await self.gambling_service.subtract_balance(
                        user_id, server_id, bet_amount
                    )
                    balance = await self.gambling_service.get_balance(
                        user_id, server_id
                    )

                embed = discord.Embed(
                    title="⏳️ 시간 초과",
                    description=f"30초 동안 응답이 없어 베팅금 {bet_amount:,}원을 잃었습니다.\n- 재산: {balance:,}원",
                    color=discord.Color.red(),
                )
                await game_message.edit(embed=embed)

        except Exception as e:
            logger.error(f"바카라 게임 처리 중 오류: {e}")
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )

        finally:
            self.baccarat_players.remove(user_id)

    @commands.command(
        name="도박.인디언", aliases=["도박.인디언포커"], description="인디언 포커"
    )
    async def indian_poker(self, ctx, bet: str = None):
        user_id = ctx.author.id
        server_id = ctx.guild.id

        remaining = await self.gambling_service.check_cooldown(
            user_id, "indian_poker", GAME_COOLDOWN
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
            await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
            return

        self.indian_poker_players.add(user_id)

        try:
            await self.gambling_service.set_cooldown(user_id, "indian_poker")

            player_card = random.randint(1, 10)
            banker_card = random.randint(1, 10)

            embed = GamblingEmbed.create_indian_poker_embed(
                title=f"🃏 {ctx.author.name}의 인디언 포커",
                description=f"{ctx.author.name}의 카드: ?\nJEE6의 카드: {banker_card}",
                color=discord.Color.blue(),
            )

            game_message = await ctx.reply(embed=embed)
            await game_message.add_reaction("💀")
            await game_message.add_reaction("✅")

            def check(reaction, user):
                return (
                    user.id == user_id
                    and str(reaction.emoji) in ["💀", "✅"]
                    and reaction.message.id == game_message.id
                )

            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=30.0, check=check
                )

                lock = await self.gambling_service._get_lock(user_id)
                async with lock:
                    if str(reaction.emoji) == "💀":
                        loss = bet_amount // 2
                        await self.gambling_service.subtract_balance(
                            user_id, server_id, loss
                        )
                        balance = await self.gambling_service.get_balance(
                            user_id, server_id
                        )

                        embed = discord.Embed(
                            title=f"🃏 {ctx.author.name} Die",
                            description=(
                                f"{ctx.author.name}의 카드: {player_card}\n"
                                f"JEE6의 카드: {banker_card}\n"
                                f"## 수익: {bet_amount:,}원 × -0.5 = -{loss:,}원\n"
                                f"- 재산: {balance:,}원"
                            ),
                            color=discord.Color.red(),
                        )
                    else:
                        if player_card > banker_card:
                            multiplier = random.uniform(
                                *GAME_MULTIPLIER_RANGES["indian_poker"]
                            )
                            winnings = int(bet_amount * multiplier)
                            tax = self.gambling_service.calculate_tax(
                                winnings, "indian_poker"
                            )
                            winnings_after_tax = winnings - tax

                            await self.gambling_service.add_balance(
                                user_id, server_id, winnings_after_tax
                            )
                            balance = await self.gambling_service.get_balance(
                                user_id, server_id
                            )

                            embed = discord.Embed(
                                title=f"🃏 {ctx.author.name} 승리",
                                description=(
                                    f"{ctx.author.name}의 카드: {player_card}\n"
                                    f"JEE6의 카드: {banker_card}\n"
                                    f"## 수익: {bet_amount:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)\n"
                                    f"- 재산: {balance:,}원"
                                ),
                                color=discord.Color.green(),
                            )
                        else:
                            await self.gambling_service.subtract_balance(
                                user_id, server_id, bet_amount
                            )
                            balance = await self.gambling_service.get_balance(
                                user_id, server_id
                            )

                            embed = discord.Embed(
                                title=f"🃏 {ctx.author.name} 패배",
                                description=(
                                    f"{ctx.author.name}의 카드: {player_card}\n"
                                    f"JEE6의 카드: {banker_card}\n"
                                    f"## 수익: {bet_amount:,}원 × -1 = -{bet_amount:,}원\n"
                                    f"- 재산: {balance:,}원"
                                ),
                                color=discord.Color.red(),
                            )

                await game_message.edit(embed=embed)

            except asyncio.TimeoutError:
                lock = await self.gambling_service._get_lock(user_id)
                async with lock:
                    await self.gambling_service.subtract_balance(
                        user_id, server_id, bet_amount
                    )
                    balance = await self.gambling_service.get_balance(
                        user_id, server_id
                    )

                embed = discord.Embed(
                    title="⏳️ 시간 초과",
                    description=f"30초 동안 응답이 없어 베팅금 {bet_amount:,}원을 잃었습니다.\n- 재산: {balance:,}원",
                    color=discord.Color.red(),
                )
                await game_message.edit(embed=embed)

        except Exception as e:
            logger.error(f"인디언 포커 게임 처리 중 오류: {e}")
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )

        finally:
            self.indian_poker_players.remove(user_id)
