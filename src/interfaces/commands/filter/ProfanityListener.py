import logging
import aiohttp
from discord.ext import commands
from src.interfaces.commands.Base import BaseCommand
from src.config.settings.Base import BaseConfig
from src.infrastructure.database.Session import get_db_session
from src.repositories.ChannelFilterRepository import ChannelFilterRepository
from src.domain.models.ChannelFilter import ChannelFilter

logger = logging.getLogger(__name__)

PROFANITY_EMOJI = "\U0001F92C"


class ProfanityListener(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.filter_url = BaseConfig.FILTER_API_URL
        self._timeout = aiohttp.ClientTimeout(total=5)
        self._enabled_channels: set[int] = set()
        self._cache_loaded = False

    def _load_enabled_channels(self):
        if self._cache_loaded:
            return
        try:
            with get_db_session() as db:
                repo = ChannelFilterRepository(model=ChannelFilter, db=db)
                self._enabled_channels = repo.get_all_enabled_channel_ids()
            self._cache_loaded = True
            logger.info(f"욕설 필터 활성 채널 {len(self._enabled_channels)}개 로드")
        except Exception as e:
            logger.error(f"욕설 필터 채널 로드 실패: {e}")

    @commands.command(
        name="filter",
        aliases=["필터", "욕필터"],
        description="이 채널의 욕설 감지 기능을 켜거나 끕니다",
    )
    async def toggle_filter(self, ctx):
        self._load_enabled_channels()
        try:
            with get_db_session() as db:
                repo = ChannelFilterRepository(model=ChannelFilter, db=db)
                now_enabled = repo.toggle(ctx.guild.id, ctx.channel.id)

            if now_enabled:
                self._enabled_channels.add(ctx.channel.id)
                await ctx.reply("욕설 필터가 **활성화**되었습니다.")
            else:
                self._enabled_channels.discard(ctx.channel.id)
                await ctx.reply("욕설 필터가 **비활성화**되었습니다.")
        except Exception as e:
            logger.error(f"Filter toggle error: {e}")
            await ctx.reply("욕설 필터 설정 중 오류가 발생했습니다.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if not message.content or message.content.startswith(BaseConfig.PREFIX):
            return

        self._load_enabled_channels()
        if message.channel.id not in self._enabled_channels:
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
