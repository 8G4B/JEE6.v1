import discord
from discord.ext import commands
import logging
import random
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

    async def _handle_timeout(self, user_id, server_id, bet_amount, game_message):
        lock = await self.gambling_service._get_lock(user_id)
        async with lock:
            balance = await self.gambling_service.subtract_balance(
                user_id, server_id, bet_amount
            )

        embed = discord.Embed(
            title="⏳️ 시간 초과",
            description=f"30초 동안 응답이 없어 베팅금 {bet_amount:,}원을 잃었습니다.\n- 재산: {balance:,}원",
            color=discord.Color.red(),
        )
        await game_message.edit(embed=embed)

    async def _validate_bet(self, bet, user_id, server_id, ctx, game_type):
        remaining = await self.gambling_service.check_cooldown(
            user_id, game_type, GAME_COOLDOWN
        )
        if remaining:
            await ctx.reply(embed=GamblingEmbed.create_cooldown_embed(remaining))
            return False, None

        bet_amount = await self._parse_bet_amount(bet, user_id, server_id)

        if error_msg := self.gambling_service.validate_bet(
            bet_amount, MIN_BET, MAX_BET
        ):
            await ctx.reply(embed=GamblingEmbed.create_error_embed(error_msg))
            return False, None

        balance = await self.gambling_service.get_balance(user_id, server_id)
        if bet_amount > balance:
            await ctx.reply(embed=GamblingEmbed.create_error_embed("돈이 부족해..."))
            return False, None

        return True, bet_amount

    @commands.command(name="도박.블랙잭", description="도박.블랙잭 [베팅금]")
    async def blackjack(self, ctx, bet: str = None):
        user_id = ctx.author.id
        server_id = ctx.guild.id

        valid, bet_amount = await self._validate_bet(
            bet, user_id, server_id, ctx, "blackjack"
        )
        if not valid:
            return

        self.blackjack_players.add(user_id)

        try:
            await self.gambling_service.set_cooldown(user_id, "blackjack")

            (
                game_message,
                cards,
                player_hand,
                dealer_hand,
                player_value,
                dealer_value,
            ) = await self._setup_blackjack_game(ctx)

            await self._run_blackjack_game(
                user_id,
                ctx,
                game_message,
                cards,
                player_hand,
                dealer_hand,
                player_value,
                dealer_value,
                bet_amount,
                server_id,
            )

        except Exception as e:
            logger.error(f"블랙잭 게임 처리 중 오류: {e}")
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )

        finally:
            self.blackjack_players.remove(user_id)

    async def _setup_blackjack_game(self, ctx):
        cards = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"] * 4
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

        return game_message, cards, player_hand, dealer_hand, player_value, dealer_value

    async def _run_blackjack_game(
        self,
        user_id,
        ctx,
        game_message,
        cards,
        player_hand,
        dealer_hand,
        player_value,
        dealer_value,
        bet_amount,
        server_id,
    ):
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
                    game_over, player_value = await self._handle_blackjack_hit(
                        cards,
                        player_hand,
                        dealer_hand,
                        player_value,
                        dealer_value,
                        user_id,
                        server_id,
                        bet_amount,
                        ctx,
                        game_message,
                    )
                    if game_over:
                        break
                elif str(reaction.emoji) == "🛑":
                    await self._handle_blackjack_stand(
                        cards,
                        player_hand,
                        dealer_hand,
                        player_value,
                        dealer_value,
                        user_id,
                        server_id,
                        bet_amount,
                        ctx,
                        game_message,
                    )
                    break

            except asyncio.TimeoutError:
                await self._handle_timeout(user_id, server_id, bet_amount, game_message)
                break

    async def _handle_blackjack_hit(
        self,
        cards,
        player_hand,
        dealer_hand,
        player_value,
        dealer_value,
        user_id,
        server_id,
        bet_amount,
        ctx,
        game_message,
    ):
        player_hand.append(cards.pop())
        player_value = self.gambling_service.calculate_hand_value(player_hand)

        if player_value > 21:
            lock = await self.gambling_service._get_lock(user_id)
            async with lock:
                balance = await self.gambling_service.subtract_balance(
                    user_id, server_id, bet_amount
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
            return True, player_value

        embed = GamblingEmbed.create_blackjack_embed(
            title=f"🃏 {ctx.author.name}의 블랙잭",
            description=(
                f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\n"
                f"JEE6의 패: {dealer_hand[0]} ?"
            ),
            color=discord.Color.blue(),
        )
        await game_message.edit(embed=embed)
        return False, player_value

    async def _handle_blackjack_stand(
        self,
        cards,
        player_hand,
        dealer_hand,
        player_value,
        dealer_value,
        user_id,
        server_id,
        bet_amount,
        ctx,
        game_message,
    ):
        while dealer_value < 17:
            dealer_hand.append(cards.pop())
            dealer_value = self.gambling_service.calculate_hand_value(dealer_hand)

        lock = await self.gambling_service._get_lock(user_id)
        async with lock:
            if dealer_value > 21 or player_value > dealer_value:
                multiplier = (
                    2.0
                    if player_value == 21
                    else random.uniform(*GAME_MULTIPLIER_RANGES["blackjack"])
                )
                winnings = int(bet_amount * multiplier)
                tax = self.gambling_service.calculate_tax(winnings, "blackjack")
                winnings_after_tax = winnings - tax

                balance = await self.gambling_service.add_balance(
                    user_id, server_id, winnings_after_tax
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
                balance = await self.gambling_service.subtract_balance(
                    user_id, server_id, bet_amount
                )

                result = "패배" if player_value < dealer_value else "무승부"
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

    @commands.command(name="도박.바카라", description="도박.바카라 [베팅금]")
    async def baccarat(self, ctx, bet: str = None):
        user_id = ctx.author.id
        server_id = ctx.guild.id

        valid, bet_amount = await self._validate_bet(
            bet, user_id, server_id, ctx, "baccarat"
        )
        if not valid:
            return

        self.baccarat_players.add(user_id)

        try:
            await self.gambling_service.set_cooldown(user_id, "baccarat")
            game_message = await self._setup_baccarat_game(ctx)

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

                (
                    is_win,
                    result,
                    player_hand,
                    banker_hand,
                    player_value,
                    banker_value,
                ) = await self._get_baccarat_result(guess)

                await self._handle_baccarat_result(
                    is_win,
                    player_hand,
                    banker_hand,
                    player_value,
                    banker_value,
                    user_id,
                    server_id,
                    bet_amount,
                    ctx,
                    game_message,
                    result,
                )

            except asyncio.TimeoutError:
                await self._handle_timeout(user_id, server_id, bet_amount, game_message)

        except Exception as e:
            logger.error(f"바카라 게임 처리 중 오류: {e}")
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )

        finally:
            self.baccarat_players.remove(user_id)

    async def _setup_baccarat_game(self, ctx):
        embed = GamblingEmbed.create_baccarat_embed(
            title=f"🃏 {ctx.author.name}의 바카라",
            description="베팅할 곳을 선택하세요",
            color=discord.Color.blue(),
        )

        game_message = await ctx.reply(embed=embed)
        await game_message.add_reaction("👤")
        await game_message.add_reaction("🏦")
        await game_message.add_reaction("🤝")
        return game_message

    async def _get_baccarat_result(self, user_guess):
        cards = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"] * 4
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

        is_win = user_guess == result
        return is_win, result, player_hand, banker_hand, player_value, banker_value

    async def _handle_baccarat_result(
        self,
        is_win,
        player_hand,
        banker_hand,
        player_value,
        banker_value,
        user_id,
        server_id,
        bet_amount,
        ctx,
        game_message,
        result,
    ):
        lock = await self.gambling_service._get_lock(user_id)
        async with lock:
            if is_win:
                multiplier = (
                    8
                    if result == "Tie"
                    else random.uniform(*GAME_MULTIPLIER_RANGES["baccarat"])
                )
                winnings = int(bet_amount * multiplier)
                tax = self.gambling_service.calculate_tax(winnings, "baccarat")
                winnings_after_tax = winnings - tax

                balance = await self.gambling_service.add_balance(
                    user_id, server_id, winnings_after_tax
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
                balance = await self.gambling_service.subtract_balance(
                    user_id, server_id, bet_amount
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

    @commands.command(
        name="도박.인디언",
        aliases=["도박.인디언포커"],
        description="도박.인디언포커 [베팅금]",
    )
    async def indian_poker(self, ctx, bet: str = None):
        user_id = ctx.author.id
        server_id = ctx.guild.id

        valid, bet_amount = await self._validate_bet(
            bet, user_id, server_id, ctx, "indian_poker"
        )
        if not valid:
            return

        self.indian_poker_players.add(user_id)

        try:
            await self.gambling_service.set_cooldown(user_id, "indian_poker")

            game_message, player_card, banker_card = await self._setup_indian_poker(ctx)

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

                if str(reaction.emoji) == "💀":
                    await self._handle_indian_die(
                        player_card,
                        banker_card,
                        user_id,
                        server_id,
                        bet_amount,
                        ctx,
                        game_message,
                    )
                else:
                    await self._handle_indian_call(
                        player_card,
                        banker_card,
                        user_id,
                        server_id,
                        bet_amount,
                        ctx,
                        game_message,
                    )

            except asyncio.TimeoutError:
                await self._handle_timeout(user_id, server_id, bet_amount, game_message)

        except Exception as e:
            logger.error(f"인디언 포커 게임 처리 중 오류: {e}")
            await ctx.reply(
                embed=GamblingEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )

        finally:
            self.indian_poker_players.remove(user_id)

    async def _setup_indian_poker(self, ctx):
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

        return game_message, player_card, banker_card

    async def _handle_indian_die(
        self,
        player_card,
        banker_card,
        user_id,
        server_id,
        bet_amount,
        ctx,
        game_message,
    ):
        lock = await self.gambling_service._get_lock(user_id)
        async with lock:
            loss = bet_amount // 2
            balance = await self.gambling_service.subtract_balance(
                user_id, server_id, loss
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
        await game_message.edit(embed=embed)

    async def _handle_indian_call(
        self,
        player_card,
        banker_card,
        user_id,
        server_id,
        bet_amount,
        ctx,
        game_message,
    ):
        lock = await self.gambling_service._get_lock(user_id)
        async with lock:
            if player_card > banker_card:
                multiplier = random.uniform(*GAME_MULTIPLIER_RANGES["indian_poker"])
                winnings = int(bet_amount * multiplier)
                tax = self.gambling_service.calculate_tax(winnings, "indian_poker")
                winnings_after_tax = winnings - tax

                balance = await self.gambling_service.add_balance(
                    user_id, server_id, winnings_after_tax
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
                balance = await self.gambling_service.subtract_balance(
                    user_id, server_id, bet_amount
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
