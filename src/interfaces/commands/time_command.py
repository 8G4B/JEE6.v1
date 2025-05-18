from discord.ext import commands
from src.interfaces.commands.base_command import BaseCommand

class TimeCommands(BaseCommand):
    @commands.command(name='time')
    async def get_time(self, ctx):
        current_time = self.container.time_service().get_current_time()
        await ctx.send(f"현재 시간: {current_time}")
