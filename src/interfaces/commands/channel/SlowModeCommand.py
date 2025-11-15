from discord.ext import commands
import asyncio
import shlex
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.ChannelEmbed import ChannelEmbed
from src.infrastructure.database.Session import get_db_session
from src.services.SlowModeService import SlowModeService

logger = logging.getLogger(__name__)


class SlowModeCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.slow_mode_service = SlowModeService()
        self.slow_mode_tasks = {}
        self._initialized = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._initialized:
            return
        self._initialized = True
        await self._init_slow_mode_tasks()

    async def _init_slow_mode_tasks(self):
        try:
            with get_db_session() as db:
                repo = self.container.slow_mode_repository(db=db)
                schedules = repo.get_all_enabled()

                for sched in schedules:
                    guild = self.bot.get_guild(sched.guild_id)
                    if not guild:
                        continue
                    channel = guild.get_channel(sched.channel_id)
                    if not channel:
                        continue
                    self._start_slow_mode_task(guild, channel)
                    logger.info(f"슬로우 모드 태스크 시작: {guild.name} - {channel.name}")

                    await self._apply_initial_slow_mode(channel)
        except Exception as e:
            logger.error(f"슬로우 모드 태스크 초기화 중 오류: {e}")

    async def _apply_initial_slow_mode(self, channel):
        try:
            now = datetime.now(ZoneInfo("Asia/Seoul"))

            if self.slow_mode_service.is_slow_mode_active_time(now):
                period = self.slow_mode_service.get_current_slow_period(now)

                if period:
                    delay = 3000
                    success, message = await self.slow_mode_service.apply_slow_mode(
                        channel, delay
                    )
                    if success:
                        logger.info(f"슬로우 모드 적용: {channel.name} - {period} ({delay}초)")
                else:
                    await self.slow_mode_service.remove_slow_mode(channel)
            else:
                await self.slow_mode_service.remove_slow_mode(channel)
        except Exception as e:
            logger.error(f"슬로우 모드 적용 중 오류: {e}")

    def _start_slow_mode_task(self, guild, channel):
        key = (guild.id, channel.id)
        if key in self.slow_mode_tasks:
            logger.info(f"이미 등록된 슬로우 모드 태스크: {key}")
            return

        async def slow_mode_monitor():
            current_channel = channel

            while True:
                try:
                    now = datetime.now(ZoneInfo("Asia/Seoul"))

                    if self.slow_mode_service.is_slow_mode_active_time(now):
                        period = self.slow_mode_service.get_current_slow_period(now)

                        if period:
                            delay = 3000
                            success, message = await self.slow_mode_service.apply_slow_mode(
                                current_channel, delay
                            )
                            if success:
                                logger.debug(
                                    f"슬로우 모드 적용: {current_channel.name} - {period} ({delay}초)"
                                )
                        else:
                            await self.slow_mode_service.remove_slow_mode(current_channel)
                            logger.debug(f"쉬는 시간 - 슬로우 모드 해제: {current_channel.name}")
                    else:
                        await self.slow_mode_service.remove_slow_mode(current_channel)
                        logger.debug(f"비활성 시간 - 슬로우 모드 해제: {current_channel.name}")

                except Exception as e:
                    logger.error(f"슬로우 모드 모니터링 에러: {e}")

                await asyncio.sleep(20)

        task = asyncio.create_task(slow_mode_monitor())
        self.slow_mode_tasks[key] = task

    @commands.command(
        name="슬로우",
        aliases=["slow", "슬로우모드", "slowmode"],
        description="슬로우 [채널명] - 슬로우 모드 활성화",
    )
    @commands.has_permissions(manage_channels=True)
    async def slow_mode(self, ctx, *, arg: str = None):
        channel_name = self._parse_channel_arg(arg)
        channel = ctx.channel

        if channel_name:
            found = None
            for ch in ctx.guild.text_channels:
                if ch.name == channel_name:
                    found = ch
                    break
            if not found:
                await ctx.send(
                    embed=ChannelEmbed.create_error_embed(
                        f"'{channel_name}' 채널을 찾을 수 없습니다."
                    )
                )
                return
            channel = found

        try:
            with get_db_session() as db:
                repo = self.container.slow_mode_repository(db=db)
                repo.enable(ctx.guild.id, channel.id, channel.name)
        except Exception as e:
            await ctx.send(
                embed=ChannelEmbed.create_error_embed(
                    f"슬로우 모드 등록 중 오류가 발생했습니다: {e}"
                )
            )
            return

        self._start_slow_mode_task(ctx.guild, channel)

        now = datetime.now(ZoneInfo("Asia/Seoul"))
        period = None

        if self.slow_mode_service.is_slow_mode_active_time(now):
            period = self.slow_mode_service.get_current_slow_period(now)
            if period:
                delay = 3000
                await self.slow_mode_service.apply_slow_mode(channel, delay)
                period_name = self.slow_mode_service.get_period_name(period)
            else:
                period_name = None
        else:
            period_name = None

        embed = ChannelEmbed.create_slow_mode_enabled_embed(channel.name, period_name)
        await ctx.send(embed=embed)

    @commands.command(
        name="슬로우.비활성화",
        aliases=["slow.disable", "슬로우끄기", "슬로우제거"],
        description="슬로우.비활성화 [채널명] - 슬로우 모드 비활성화",
    )
    @commands.has_permissions(manage_channels=True)
    async def slow_mode_disable(self, ctx, *, arg: str = None):
        channel_name = self._parse_channel_arg(arg)
        channel = ctx.channel
        channel_name_to_search = channel.name

        if channel_name:
            channel_name_to_search = channel_name.lower().strip()
            found = None
            for ch in ctx.guild.text_channels:
                if ch.name.lower() == channel_name_to_search:
                    found = ch
                    break
            if found:
                channel = found

        try:
            with get_db_session() as db:
                repo = self.container.slow_mode_repository(db=db)
                records = repo.find_by_channel_name(ctx.guild.id, channel_name_to_search)

                if not records:
                    await ctx.send(
                        embed=ChannelEmbed.create_error_embed(
                            f"'{channel_name_to_search}' 채널에 활성화된 슬로우 모드가 없습니다."
                        )
                    )
                    return

                for record in records:
                    task_key = (ctx.guild.id, record.channel_id)
                    task = self.slow_mode_tasks.get(task_key)
                    if task:
                        task.cancel()
                        del self.slow_mode_tasks[task_key]

                repo.disable_by_name(ctx.guild.id, channel_name_to_search)

                await self.slow_mode_service.remove_slow_mode(channel)

                embed = ChannelEmbed.create_slow_mode_disabled_embed(channel.name)
                await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(
                embed=ChannelEmbed.create_error_embed(
                    f"슬로우 모드 비활성화 중 오류가 발생했습니다: {e}"
                )
            )

    def _parse_channel_arg(self, arg):
        if not arg:
            return None

        channel_name = None
        tokens = shlex.split(arg)
        i = 0
        while i < len(tokens):
            if (tokens[i] in ("-n", "--name")) and i + 1 < len(tokens):
                channel_name = tokens[i + 1]
                i += 2
            else:
                channel_name = arg
                break

        return channel_name
