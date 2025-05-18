from discord.ext import commands
from src.services.time_service import TimeService

class TimeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.time_service = TimeService()
