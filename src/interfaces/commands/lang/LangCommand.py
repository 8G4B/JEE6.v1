import logging
import discord
from discord.ext import commands
from src.interfaces.commands.Base import BaseCommand
from src.services.LangService import LangService
from src.infrastructure.database.Session import get_db_session
from src.config.settings.base import BaseConfig

logger = logging.getLogger(__name__)


class LangCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.lang_service = LangService()
        self._enabled_channels: set[int] = set()
        self._cache_loaded = False

    def _load_enabled_channels(self):
        if self._cache_loaded:
            return
        try:
            with get_db_session() as db:
                repo = self.container.channel_lang_repository(db=db)
                self._enabled_channels = repo.get_all_enabled_channel_ids()
            self._cache_loaded = True
            logger.info(f"자연어 모드 활성 채널 {len(self._enabled_channels)}개 로드")
        except Exception as e:
            logger.error(f"자연어 모드 채널 로드 실패: {e}")

    @commands.command(
        name="lang",
        aliases=["자연어", "ㅈㅇㅇ"],
        description="현재 채널의 자연어 명령 모드를 토글합니다. (관리자 전용)",
    )
    @commands.has_permissions(manage_channels=True)
    async def toggle_lang(self, ctx):
        logger.info(f"lang_toggle({ctx.guild.name}, {ctx.channel.name}, {ctx.author.name})")

        try:
            with get_db_session() as db:
                repo = self.container.channel_lang_repository(db=db)
                enabled = repo.toggle(ctx.guild.id, ctx.channel.id)

            if enabled:
                self._enabled_channels.add(ctx.channel.id)
            else:
                self._enabled_channels.discard(ctx.channel.id)

            status = "활성화" if enabled else "비활성화"
            color = discord.Color.green() if enabled else discord.Color.red()

            embed = discord.Embed(
                title="🧠 자연어 명령 모드",
                description=f"이 채널에서 자연어 명령 모드가 **{status}** 되었습니다.",
                color=color,
            )
            if enabled:
                embed.add_field(
                    name="사용법",
                    value="이제 `!` 없이 자연스럽게 말하면 됩니다.\n"
                          "예: \"오늘 급식 뭐야?\", \"한강 수온 알려줘\"",
                    inline=False,
                )
            await ctx.reply(embed=embed)

        except Exception as e:
            logger.error(f"lang 토글 오류: {e}")
            await ctx.reply(f"오류가 발생했습니다: {e}")

    @commands.command(
        name="질문",
        aliases=["ask", "ㅈㅁ"],
        description="AI에게 질문합니다.",
    )
    async def ask(self, ctx, *, question: str = None):
        if not question:
            await ctx.reply("질문 내용을 입력해주세요. 예: `!질문 파이썬이 뭐야?`")
            return

        logger.info(f"ask({ctx.guild.name}, {ctx.author.name}, {question[:50]})")

        async with ctx.typing():
            answer = await self.lang_service.ask_question(question)

        if len(answer) > 2000:
            answer = answer[:1997] + "..."

        embed = discord.Embed(
            title="🤖 AI 답변",
            description=answer,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"질문: {question[:100]}")
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if not message.guild:
            return

        if message.content.startswith(BaseConfig.PREFIX):
            return

        self._load_enabled_channels()

        if message.channel.id not in self._enabled_channels:
            return

        content = message.content.strip()
        if not content or len(content) < 2:
            return

        logger.info(f"lang_process({message.guild.name}, {message.channel.name}, {message.author.name}, {content[:50]})")

        async with message.channel.typing():
            response = await self.lang_service.process_message(content)

        if not response:
            return

        if len(response) > 2000:
            response = response[:1997] + "..."

        await message.reply(response, mention_author=False)
