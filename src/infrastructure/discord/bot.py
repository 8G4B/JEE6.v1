import asyncio
import logging
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from src.infrastructure.di.Container import Container
from src.interfaces.commands.information.TimeCommand import TimeCommands
from src.interfaces.commands.channel import ChannelCommands
from src.interfaces.commands.channel import CleanCommand
from src.interfaces.commands.channel import PeriodicCleanCommand
from src.interfaces.commands.channel.SlowModeCommand import SlowModeCommand
from src.interfaces.commands.justice.JusticeCommand import JusticeCommands
from src.interfaces.commands.justice.ReleaseCommand import ReleaseCommand
from src.interfaces.commands.information.InformationCommand import InformationCommands
from src.interfaces.commands.meal.MealCommand import MealCommands
from src.interfaces.commands.riot.LolCommand import LolCommands
from src.interfaces.commands.riot.ValoCommand import ValoCommands
from src.config.settings.Base import BaseConfig
from src.services.MealService import MealService

logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    def __init__(self, container: Container):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=BaseConfig.PREFIX, intents=intents, help_command=None
        )

        self.container = container
        self.container.bot.override(self)
        self.remove_command("help")

    async def setup_hook(self) -> None:
        if BaseConfig.ENABLE_MANAGEMENT_COMMANDS:
            await self.add_cog(ChannelCommands(self, self.container))
            await self.add_cog(CleanCommand(self, self.container))
            await self.add_cog(PeriodicCleanCommand(self, self.container))
            await self.add_cog(SlowModeCommand(self, self.container))

        if BaseConfig.ENABLE_GAMBLING_COMMANDS:
            await self.add_cog(self.container.gambling_command())
            await self.add_cog(self.container.gambling_games())
            await self.add_cog(self.container.gambling_card_games())

        await self.add_cog(InformationCommands(self, self.container))
        await self.add_cog(MealCommands(self, self.container))
        await self.add_cog(LolCommands(self, self.container))
        await self.add_cog(ValoCommands(self, self.container))
        await self.add_cog(TimeCommands(self, self.container))
        await self.add_cog(JusticeCommands(self, self.container))
        await self.add_cog(ReleaseCommand(self, self.container))

    async def on_ready(self):
        print(f"Logged in as {self.user.name} (ID: {self.user.id})")
        print(f"Connected to {len(self.guilds)} guilds")
        print(f"Management commands enabled: {BaseConfig.ENABLE_MANAGEMENT_COMMANDS}")

    async def _preload_meal_cache(self):
        try:
            logger.info("급식 정보 캐시 사전 로딩 시작...")
            meal_service = MealService()
            now = datetime.now()
            today = now.strftime("%Y%m%d")
            tomorrow = (now + timedelta(days=1)).strftime("%Y%m%d")

            await asyncio.gather(
                meal_service.get_meal_info(today),
                meal_service.get_meal_info(tomorrow),
                return_exceptions=True
            )

            logger.info(f"급식 정보 캐시 사전 로딩 완료 ({today}, {tomorrow})")
        except Exception as e:
            logger.warning(f"급식 정보 캐시 사전 로딩 실패 (무시 가능): {e}")
