import discord
from discord.ext import commands
from discord_token import TOKEN
import random
import asyncio
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = False
bot = commands.Bot(command_prefix="!", intents=intents)

class Greeting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="안녕", description="안녕")
    async def greet(self, ctx):
        if ctx.author.name in ["aiden300.", "aiden300_"]:
            title = "야 이주언 싸려"
        elif random.random() <= 0.01:
            title = "야 싸려" 
        else:
            title = "안녕!"
            
        embed = discord.Embed(
            title=title,
            color=discord.Color.red() if title != "안녕!" else discord.Color.blue()
        )
        await ctx.send(embed=embed)
        
class Time(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='시간', aliases=['시계', '타임'], description="시간")
    async def time(self, ctx):
        now = datetime.now()
        embed = discord.Embed(
            title=f"{now.strftime('%Y년 %m월 %d일')}\n{now.strftime('%H시 %M분 %S초')}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
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
        await ctx.send(embed=embed)

    @commands.command(name="도박.주사위", description="주사위")
    async def dice(self, ctx, guess: str = None, bet: int = None):
        if error_embed := self._validate_dice_guess(guess):
            embed = error_embed
        elif error_embed := self._validate_bet(bet):
            embed = error_embed
        else:
            result = random.choice([str(i) for i in range(1, 7)])
            embed = self._play_game(ctx.author.name, guess, result, bet, 6)
        await ctx.send(embed=embed)

    def _create_game_embed(self, author_name, is_correct, guess, result, bet=None, winnings=None):
        description = f"- 예측: {guess}\n- 결과: {result}"
        if bet is not None:
            description = f"- 예측: {guess}\n- 결과: {result}\n## 돈: {bet} → {winnings}"
            
        return discord.Embed(
            title=f"{author_name} {'맞음 ㄹㅈㄷ' if is_correct else '틀림ㅋ'}",
            description=description,
            color=discord.Color.green() if is_correct else discord.Color.red()
        )

async def setup(bot):
    await bot.add_cog(Greeting(bot))
    await bot.add_cog(Gambling(bot))
    await bot.add_cog(Time(bot))

async def main():
    async with bot:
        await setup(bot)
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
