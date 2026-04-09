import logging
import aiohttp
from discord.ext import commands
from src.interfaces.commands.Base import BaseCommand
from src.config.settings.Base import BaseConfig
from src.infrastructure.database.Session import get_db_session
from src.repositories.ChannelFilterRepository import ChannelFilterRepository
from src.domain.models.ChannelFilter import ChannelFilter

logger = logging.getLogger(__name__)

PROFANITY_EMOJI = "\U0001F92C"  # 🤬
FALSE_POSITIVE_EMOJI = "\u274C"  # ❌
ADMIN_NAME = "nwoxsterziah"


class ProfanityListener(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.filter_url = BaseConfig.FILTER_API_URL
        self._timeout = aiohttp.ClientTimeout(total=5)
        self._enabled_channels: set[int] = set()
        self._cache_loaded = False
        # message_id -> original text (for feedback tracking)
        self._flagged_messages: dict[int, str] = {}

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
        if ctx.author.name != ADMIN_NAME:
            return
        self._load_enabled_channels()
        try:
            with get_db_session() as db:
                repo = ChannelFilterRepository(model=ChannelFilter, db=db)
                now_enabled = repo.toggle(ctx.guild.id, ctx.channel.id)

            if now_enabled:
                self._enabled_channels.add(ctx.channel.id)
                await ctx.reply("욕설 필터가 **활성화**되었습니다.\n"
                                f"오탐: 봇의 {PROFANITY_EMOJI}에 {FALSE_POSITIVE_EMOJI} 리액션\n"
                                f"미탐: 메시지에 {PROFANITY_EMOJI} 리액션")
            else:
                self._enabled_channels.discard(ctx.channel.id)
                await ctx.reply("욕설 필터가 **비활성화**되었습니다.")
        except Exception as e:
            logger.error(f"Filter toggle error: {e}")
            await ctx.reply("욕설 필터 설정 중 오류가 발생했습니다.")

    @commands.command(
        name="filter.train",
        aliases=["필터.학습"],
        description="축적된 피드백으로 모델을 학습시킵니다",
    )
    async def train_model(self, ctx):
        if ctx.author.name != ADMIN_NAME:
            return
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(f"{self.filter_url}/status") as resp:
                    status = await resp.json()

                count = status.get("feedback_count", 0)
                if count < 5:
                    await ctx.reply(f"피드백 {count}개 — 최소 5개 필요합니다.")
                    return

                msg = await ctx.reply(f"학습 시작 (피드백 {count}개)...")

                async with session.post(f"{self.filter_url}/train") as resp:
                    result = await resp.json()

                if result.get("status") == "training":
                    await msg.edit(content=f"학습 중... (피드백 {count}개, 백그라운드 처리)")
                else:
                    await msg.edit(content=f"학습 결과: {result}")
        except Exception as e:
            logger.error(f"Train error: {e}")
            await ctx.reply("학습 요청 중 오류가 발생했습니다.")

    @commands.command(
        name="filter.status",
        aliases=["필터.상태"],
        description="필터 모델 상태를 확인합니다",
    )
    async def filter_status(self, ctx):
        if ctx.author.name != ADMIN_NAME:
            return
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(f"{self.filter_url}/status") as resp:
                    status = await resp.json()
            fine_tuned = "사용 중" if status.get("fine_tuned") else "미적용"
            count = status.get("feedback_count", 0)
            await ctx.reply(f"Fine-tuned 모델: **{fine_tuned}**\n축적 피드백: **{count}개**")
        except Exception as e:
            logger.error(f"Status error: {e}")
            await ctx.reply("상태 조회 중 오류가 발생했습니다.")

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
                self._flagged_messages[message.id] = message.content
                # Prevent memory leak
                if len(self._flagged_messages) > 1000:
                    oldest = list(self._flagged_messages.keys())[:500]
                    for k in oldest:
                        del self._flagged_messages[k]
        except Exception as e:
            logger.error(f"Profanity filter error: {e}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if user.name != ADMIN_NAME:
            return

        message = reaction.message
        emoji = str(reaction.emoji)

        # Case 1: ❌ on a message the bot flagged → false positive
        if emoji == FALSE_POSITIVE_EMOJI and message.id in self._flagged_messages:
            text = self._flagged_messages.pop(message.id)
            await self._send_feedback(text, label=0)  # 0 = clean
            logger.info(f"피드백(오탐): {text[:30]}...")

        # Case 2: 🤬 on a message the bot didn't flag → false negative
        elif emoji == PROFANITY_EMOJI and message.id not in self._flagged_messages:
            if not message.content:
                return
            # Check the bot didn't already react
            for r in message.reactions:
                if str(r.emoji) == PROFANITY_EMOJI and r.me:
                    return
            await self._send_feedback(message.content, label=1)  # 1 = profanity
            logger.info(f"피드백(미탐): {message.content[:30]}...")

    async def _check_profanity(self, text: str) -> bool:
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(
                f"{self.filter_url}/predict",
                json={"text": text},
            ) as resp:
                data = await resp.json()
                return data.get("is_profanity", False)

    async def _send_feedback(self, text: str, label: int):
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                await session.post(
                    f"{self.filter_url}/feedback",
                    json={"text": text, "label": label},
                )
        except Exception as e:
            logger.error(f"Feedback send error: {e}")
