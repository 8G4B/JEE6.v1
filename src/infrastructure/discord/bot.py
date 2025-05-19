import discord
from discord.ext import commands
from src.infrastructure.di.container import Container
from src.interfaces.commands.time_command import TimeCommands

class Bot(commands.Bot):
    def __init__(self, container: Container):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None 
        )
        
        self.container = container

    async def setup_hook(self) -> None:
        await self.add_cog(TimeCommands(self, self.container))

    async def on_ready(self):
        print(f'Logged in as {self.user.name} (ID: {self.user.id})')
        print(f'Connected to {len(self.guilds)} guilds')