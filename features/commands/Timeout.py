import discord
from discord.ext import commands
from datetime import datetime, timedelta

class Timeout(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='타임아웃', description="특정 유저를 타임아웃합니다.")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: int, *, reason: str = None):

        try:
            until = datetime.utcnow() + timedelta(minutes=duration)
            await member.timeout(until=until, reason=reason)
            await ctx.reply(embed=discord.Embed(
                title="타임아웃",
                description=f"{member.mention}가 {duration}분 동안 타임아웃됨",
                color=discord.Color.red()
            ))
        except discord.Forbidden:
            await ctx.reply(embed=discord.Embed(
                title="오류",
                description="권한 없음",
                color=discord.Color.red()
            ))
        except Exception as e:
            await ctx.reply(embed=discord.Embed(
                title="오류",
                description=f"{str(e)}",
                color=discord.Color.red()
            ))

def setup(bot):
    bot.add_cog(Timeout(bot))
