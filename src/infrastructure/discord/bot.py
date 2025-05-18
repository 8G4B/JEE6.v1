import discord
from discord.ext import commands
from src.infrastructure.di.container import Container
from src.interfaces.commands.time_command import TimeCommands

class Bot(commands.Bot):
    def __init__(self, container: Container):
        super().__init__(command_prefix='!')
        self.container = container
        self.remove_command('help')  
    
    async def setup_hook(self):
        await self.add_cog(TimeCommands(self, self.container))
    
    async def on_ready(self):
        print(f'Logged in as {self.user.name}') 