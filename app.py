import discord
from discord.ext import commands
from discord_token import TOKEN
import random

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

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="도박.동전", description="동전 던지기")
    async def coin(self, ctx, guess: str = None, bet: int = None):
        if guess not in ["앞", "뒤"]:
            embed = discord.Embed(
                title="오류",
                description="**'앞'**이랑 **'뒤'**만 입력해라...",
                color=discord.Color.red()
            )
        elif bet is None or bet <= 0:
            embed = discord.Embed(
                title="오류",
                description="돈 제대로 입력해라...", 
                color=discord.Color.red()
            )
        else:
            result = random.choice(["앞", "뒤"])
            is_correct = guess == result
            winnings = bet * 2 if is_correct else 0
            embed = self._create_game_embed(
                ctx.author.name,
                is_correct,
                guess,
                result,
                bet,
                winnings
            )
        await ctx.send(embed=embed)

    @commands.command(name="도박.주사위", description="주사위")
    async def dice(self, ctx, guess: str = None):
        valid_guesses = [str(i) for i in range(1, 7)]
        if guess not in valid_guesses:
            embed = discord.Embed(
                title="오류",
                description="**1부터 6까지 숫자**만 입력해라...",
                color=discord.Color.red()
            )
        else:
            result = random.choice(valid_guesses)
            is_correct = guess == result
            embed = self._create_game_embed(
                ctx.author.name,
                is_correct,
                guess,
                result
            )
        await ctx.send(embed=embed)

    def _create_game_embed(self, author_name, is_correct, guess, result, bet=None, winnings=None):
        description = f"## 예측: {guess}\n## 결과: {result}"
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

bot.run(TOKEN)
