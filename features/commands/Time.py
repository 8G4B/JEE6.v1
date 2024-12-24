import discord
from discord.ext import commands
from datetime import datetime

class TimeService:
    @staticmethod
    def get_current_time() -> datetime:
        return datetime.now()

class TimeEmbed:
    @staticmethod
    def create_time_embed(time: datetime) -> discord.Embed:
        return discord.Embed(
            title=f"🗓️ {time.strftime('%Y년 %m월 %d일')}\n⌚️ {time.strftime('%H시 %M분 %S초')}",
            color=discord.Color.pink()
        )

class Time(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.time_service = TimeService()

    @commands.command(name='시간', aliases=['시계', '타임'], description="시간")
    async def time(self, ctx):
        current_time = TimeService.get_current_time()
        embed = TimeEmbed.create_time_embed(current_time)
        await ctx.reply(embed=embed)
