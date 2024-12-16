import discord
from discord.ext import commands
import random
from datetime import datetime
class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        self.balances = {}

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

    def _play_game(self, author_id, author_name, guess, result, bet, multiplier):
        is_correct = guess == result
        winnings = bet * multiplier if is_correct else 0
        
        current_balance = self.balances.get(author_id, 0)
        if is_correct:
            self.balances[author_id] = current_balance + winnings
        else:
            self.balances[author_id] = current_balance - bet
            
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
        elif bet > self.balances.get(ctx.author.id, 0):
            embed = discord.Embed(
                title="오류",
                description="돈이 부족해...",
                color=discord.Color.red()
            )
        else:
            result = random.choice(["앞", "뒤"])
            embed = self._play_game(ctx.author.id, ctx.author.name, guess, result, bet, random.uniform(1.5, 3.0))
        await ctx.reply(embed=embed)

    @commands.command(name="도박.주사위", description="주사위")
    async def dice(self, ctx, guess: str = None, bet: int = None):
        if error_embed := self._validate_dice_guess(guess):
            embed = error_embed
        elif error_embed := self._validate_bet(bet):
            embed = error_embed
        elif bet > self.balances.get(ctx.author.id, 0):
            embed = discord.Embed(
                title="오류",
                description="돈이 부족해...",
                color=discord.Color.red()
            )
        else:
            result = random.choice([str(i) for i in range(1, 7)])
            embed = self._play_game(ctx.author.id, ctx.author.name, guess, result, bet, random.uniform(5, 10))
        await ctx.reply(embed=embed)

    @commands.command(name="도박.노동", description="도박.노동")
    async def get_money(self, ctx):
        current_time = datetime.now()
        last_used = self.cooldowns.get(ctx.author.id)
        
        if last_used and (current_time - last_used).total_seconds() < 60:
            remaining = 60 - int((current_time - last_used).total_seconds())
            embed = discord.Embed(
                title="힘들어서 쉬는 중 ㅋ",
                description=f"{remaining}초 후에 다시 시도해주세요.",
                color=discord.Color.red()
            )
        else:
            amount = random.randint(50, 1000)
            self.balances[ctx.author.id] = self.balances.get(ctx.author.id, 0) + amount
            embed = discord.Embed(
                title=f"{ctx.author.name}",
                description=f"정당한 노동을 통해 {amount}원을 벌었다. \n- 재산: {self.balances.get(ctx.author.id, 0)}원(+{amount})",
                color=discord.Color.green()
            )
            self.cooldowns[ctx.author.id] = current_time
            
        await ctx.reply(embed=embed)

    @commands.command(name="도박.지갑", description="잔액 확인")
    async def check_balance(self, ctx):
        balance = self.balances.get(ctx.author.id, 0)
        embed = discord.Embed(
            title=f"{ctx.author.name}의 지갑",
            description=f"현재 잔액: {balance}원",
            color=discord.Color.blue()
        )
        await ctx.reply(embed=embed)

    def _create_game_embed(self, author_name, is_correct, guess, result, bet=None, winnings=None):
        description = f"- 예측: {guess}\n- 결과: {result}"
        if bet is not None:
            diff = winnings - bet
            sign = "+" if diff > 0 else ""
            description = f"- 예측: {guess}\n- 결과: {result}\n- 재산: {winnings}원({sign}{diff})"
            
        return discord.Embed(
            title=f"{author_name} {'맞음 ㄹㅈㄷ' if is_correct else '틀림ㅋ'}",
            description=description,
            color=discord.Color.green() if is_correct else discord.Color.red()
        )
