from discord.ext import commands
from src.infrastructure.di.container import Container

class BaseCommand(commands.Cog):
    def __init__(self, bot, container: Container):
        self.bot = bot
        self.container = container 