from discord.ext import commands
from typing import Any


class BaseCommand(commands.Cog):
    def __init__(self, bot, container: Any):
        self.bot = bot
        self.container = container
