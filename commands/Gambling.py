import discord
from discord.ext import commands
import random

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _validate_bet(self, bet):
        if bet is None or bet <= 0:
            return discord.Embed(
                title="오류",
                description="돈 제대로 입력해라...",
                color=discord.Color.red()
            )
        return None

    def _validate_coin_guess(self, guess):
        if guess not in ["앞", "뒤"]:
            return discord.Embed(
                title="오류", 
                description="**'앞'**이랑 **'뒤'**만 입력해라...",
                color=discord.Color.red()
            )
        return None

    def _validate_dice_guess(self, guess):
        if guess not in [str(i) for i in range(1, 7)]:
            return discord.Embed(
                title="오류",
                description="**1부터 6까지 숫자**만 입력해라...",
                color=discord.Color.red()
            )
        return None

    def _play_game(self, author_name, guess, result, bet, multiplier):
        is_correct = guess == result
        winnings = bet * multiplier if is_correct else 0
        return self._create_game_embed(
            author_name,
            is_correct,
            guess,
            result,
            bet,
            winnings
        )

    @commands.command(name="도박.동전", description="동전 던지기")
    async def coin(self, ctx, guess: str = None, bet: int = None):
        if error_embed := self._validate_coin_guess(guess):
            embed = error_embed
        elif error_embed := self._validate_bet(bet):
            embed = error_embed
        else:
            result = random.choice(["앞", "뒤"])
            embed = self._play_game(ctx.author.name, guess, result, bet, 2)
        await ctx.message.delete()
        await ctx.reply(f"{ctx.author.mention}", embed=embed)

    @commands.command(name="도박.주사위", description="주사위")
    async def dice(self, ctx, guess: str = None, bet: int = None):
        if error_embed := self._validate_dice_guess(guess):
            embed = error_embed
        elif error_embed := self._validate_bet(bet):
            embed = error_embed
        else:
            result = random.choice([str(i) for i in range(1, 7)])
            embed = self._play_game(ctx.author.name, guess, result, bet, 6)
        await ctx.message.delete()
        await ctx.reply(f"{ctx.author.mention}", embed=embed)

    def _create_game_embed(self, author_name, is_correct, guess, result, bet=None, winnings=None):
        description = f"- 예측: {guess}\n- 결과: {result}"
        if bet is not None:
            description = f"- 예측: {guess}\n- 결과: {result}\n## 돈: {bet} → {winnings}"
            
        return discord.Embed(
            title=f"{author_name} {'맞음 ㄹㅈㄷ' if is_correct else '틀림ㅋ'}",
            description=description,
            color=discord.Color.green() if is_correct else discord.Color.red()
        )
