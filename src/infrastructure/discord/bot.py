import discord
from discord.ext import commands
from src.infrastructure.di.container import Container
from src.interfaces.commands.time_command import TimeCommands
from src.interfaces.commands.channel_command import ChannelCommands
from src.interfaces.commands.justice_command import JusticeCommands
from src.interfaces.commands.information_command import InformationCommands
from src.interfaces.commands.meal_command import MealCommands
from src.interfaces.commands.lol_command import LolCommands
from src.interfaces.commands.valo_command import ValoCommands
from src.interfaces.commands.gambling_command import GamblingCommands
from src.interfaces.commands.gambling_games import GamblingGames
from src.interfaces.commands.gambling_card_games import GamblingCardGames

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
        self.container.bot.override(self)
        self.remove_command('help')  

    async def setup_hook(self) -> None:
        await self.add_cog(TimeCommands(self, self.container))
        await self.add_cog(ChannelCommands(self, self.container))
        await self.add_cog(JusticeCommands(self, self.container))
        await self.add_cog(InformationCommands(self, self.container))
        await self.add_cog(MealCommands(self, self.container))
        await self.add_cog(LolCommands(self, self.container))
        await self.add_cog(ValoCommands(self, self.container))
        
        await self.add_cog(self.container.gambling_command())
        await self.add_cog(self.container.gambling_games())
        await self.add_cog(self.container.gambling_card_games())

    async def on_ready(self):
        print(f'Logged in as {self.user.name} (ID: {self.user.id})')
        print(f'Connected to {len(self.guilds)} guilds')