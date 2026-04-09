import logging
import aiohttp
from discord.ext import commands
from src.interfaces.commands.Base import BaseCommand
from src.config.settings.Base import BaseConfig

logger = logging.getLogger(__name__)

PROFANITY_EMOJI = "\U0001F92C"


class ProfanityListener(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.filter_url = BaseConfig.FILTER_API_URL
        self._timeout = aiohttp.ClientTimeout(total=5)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if not message.content or message.content.startswith(BaseConfig.PREFIX):
            return

        try:
            is_profanity = await self._check_profanity(message.content)
            if is_profanity:
                await message.add_reaction(PROFANITY_EMOJI)
        except Exception as e:
            logger.error(f"Profanity filter error: {e}")

    async def _check_profanity(self, text: str) -> bool:
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(
                f"{self.filter_url}/predict",
                json={"text": text},
            ) as resp:
                data = await resp.json()
                return data.get("is_profanity", False)
