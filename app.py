import discord
from discord.ext import commands
from discord_token import TOKEN
import random

TOKEN = TOKEN

intents = discord.Intents.default()
intents.message_content = True
intents.members = False
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command(name="안녕", description="안녕")
async def hello(ctx):
    if ctx.author.name == "aiden300." or "aiden300_":
      embed = discord.Embed(
            title="야 이주언 싸려",
            color=discord.Color.red()
        )
    elif random.random() <= 0.01: 
        embed = discord.Embed(
            title="야 싸려",
            color=discord.Color.red()
        )
    else:
        embed = discord.Embed(
            title="안녕!",
            color=discord.Color.blue()
        )
    await ctx.send(embed=embed)

@bot.command(name="도박.동전", description="동전 던지기")
async def flip_coin(ctx, guess: str = None, bet: int = None):
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
        embed = discord.Embed(
            title=f"{ctx.author.name} {'맞음 ㄹㅈㄷ' if is_correct else '틀림ㅋ'}",
            description=f"- 예측: {guess}\n- 결과: {result}\n## 돈: {bet} → {winnings}", 
            color=discord.Color.green() if is_correct else discord.Color.red()
        )
    await ctx.send(embed=embed)

@bot.command(name="도박.주사위", description="주사위")
async def dice(ctx, guess: str = None):
    if guess not in ["1", "2", "3", "4", "5", "6"]:
        embed = discord.Embed(
            title="오류",
            description="**1부터 6까지 숫자**만 입력해라...",
            color=discord.Color.red()
        )
    else:
        result = random.choice(["1", "2", "3", "4", "5", "6"])
        is_correct = guess == result
        embed = discord.Embed(
            title=f"{ctx.author.name} {'맞음 ㄹㅈㄷ' if is_correct else '틀림ㅋ'}",
            description=f"## 예측: {guess}\n## 결과: {result}",
            color=discord.Color.green() if is_correct else discord.Color.red()
        )
    await ctx.send(embed=embed)

bot.run(TOKEN)
