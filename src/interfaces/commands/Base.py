from discord.ext import commands
from typing import Any

# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
#     from src.infrastructure.di.container import Container


class BaseCommand(commands.Cog):
    def __init__(self, bot, container: Any):
        self.bot = bot
        self.container = container
