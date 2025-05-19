from discord.ext import commands
from src.interfaces.commands.base import BaseCommand
from src.utils.embeds.time_embed import TimeEmbed

class TimeCommands(BaseCommand):
    @commands.command(
        name='시간',
        aliases=['시계', '타임', 'time'],
        description="현재 시간을 확인합니다."
    )
    async def get_time(self, ctx):
        time_service = self.container.time_service()
        current_time = time_service.get_current_datetime()
        embed = TimeEmbed.create_time_embed(current_time)
        await ctx.reply(embed=embed)
