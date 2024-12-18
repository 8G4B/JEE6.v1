import discord
from discord.ext import commands
from datetime import datetime
        
class Time(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='시간', aliases=['시계', '타임'], description="시간")
    async def time(self, ctx):
        now = datetime.now()
        embed = discord.Embed(
            title=f"🗓️ {now.strftime('%Y년 %m월 %d일')}\n⌚️ {now.strftime('%H시 %M분 %S초')}",
            color=discord.Color.pink()
        )
        await ctx.reply(embed=embed)        
