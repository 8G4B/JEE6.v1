from discord.ext import commands
import asyncio
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.ChannelEmbed import ChannelEmbed
from src.infrastructure.database.Session import get_db_session
from sqlalchemy import text
from src.utils.time.timeParser import parse_time_string
from src.utils.time.formatSeconds import format_seconds
import logging
import shlex

logger = logging.getLogger(__name__)


class ChannelCommands(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.periodic_tasks = {}
        self._init_periodic_tasks()

    def _get_db(self):
        return self.container.db() if hasattr(self.container, "db") else None

    def _init_periodic_tasks(self):
        try:
            with get_db_session() as db:
                repo = self.container.periodic_clean_repository(db=db)
                try:
                    self._update_channel_names(db, repo)

                    schedules = repo.get_all_enabled()
                    for sched in schedules:
                        guild = self.bot.get_guild(sched.guild_id)
                        if not guild:
                            continue
                        channel = guild.get_channel(sched.channel_id)
                        if not channel:
                            continue
                        self._start_periodic_clean_task(
                            guild, channel, sched.interval_seconds
                        )
                except Exception as e:
                    if "Table" in str(e) and "doesn't exist" in str(e):
                        logger.warning(
                            f"주기적 청소 테이블이 아직 생성되지 않았습니다: {e}"
                        )
                    elif "Unknown column" in str(e) and "channel_name" in str(e):
                        logger.warning(
                            f"channel_name 컬럼이 아직 추가되지 않았습니다. 앱을 재시작하면 자동으로 추가됩니다: {e}"
                        )
                    else:
                        logger.error(f"주기적 청소 작업 초기화 중 오류: {e}")
        except Exception as e:
            logger.error(f"세션 관리 중 오류 발생: {e}")

    def _update_channel_names(self, db, repo):
        try:
            result = db.execute(
                text(
                    "SELECT guild_id, channel_id FROM periodic_clean WHERE channel_name = '' OR channel_name IS NULL"
                )
            )
            records = result.fetchall()

            updated = 0
            for record in records:
                guild_id, channel_id = record
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue

                channel = guild.get_channel(channel_id)
                if not channel:
                    continue

                db.execute(
                    text(
                        "UPDATE periodic_clean SET channel_name = :name WHERE guild_id = :guild_id AND channel_id = :channel_id"
                    ),
                    {
                        "name": channel.name,
                        "guild_id": guild_id,
                        "channel_id": channel_id,
                    },
                )
                updated += 1

            if updated > 0:
                db.commit()
        except Exception as e:
            logger.error(f"channel_name 업데이트 중 오류: {e}")

    def _start_periodic_clean_task(self, guild, channel, seconds):
        key = (guild.id, channel.id)
        if key in self.periodic_tasks:
            logger.info(f"이미 메모리에 등록된 태스크 존재: {key}")
            return
        channel_service = self.container.channel_service()

        async def periodic_clean():
            current_channel = channel
            old_key = (guild.id, current_channel.id)
            while True:
                try:
                    start_embed = ChannelEmbed.create_clean_start_embed(
                        current_channel.name
                    )
                    await current_channel.send(embed=start_embed)
                    success, message, new_channel = await channel_service.clean_channel(
                        guild, current_channel, None
                    )
                    if success and new_channel:
                        success_embed = ChannelEmbed.create_clean_success_embed()
                        await new_channel.send(embed=success_embed)
                        current_channel = new_channel

                        new_key = (guild.id, current_channel.id)
                        if old_key != new_key and old_key in self.periodic_tasks:
                            task = self.periodic_tasks.pop(old_key)
                            self.periodic_tasks[new_key] = task
                            old_key = new_key
                    else:
                        error_embed = ChannelEmbed.create_error_embed(message)
                        await current_channel.send(embed=error_embed)
                        break
                except Exception as e:
                    logger.error(f"주기적 청소 에러: {e}")
                    break
                await asyncio.sleep(seconds)

        task = asyncio.create_task(periodic_clean())
        self.periodic_tasks[key] = task

    @commands.command(
        name="청소",
        aliases=["clean", "c", "C", "CLEAN", "ㅊ"],
        description="청소 [-n 채널명] [-c 주기]",
    )
    @commands.has_permissions(manage_channels=True)
    async def clean_channel(self, ctx, *, arg: str = None):
        channel_name, seconds = self._parse_clean_args(arg)

        if seconds:
            await self._setup_periodic_clean(ctx, channel_name, seconds)
        elif channel_name:
            await self.clean_channel_once(ctx, channel_name)
        else:
            await self.clean_channel_once(ctx)

    def _parse_clean_args(self, arg):
        channel_name = None
        seconds = None

        if not arg:
            return None, None

        tokens = shlex.split(arg)
        i = 0
        while i < len(tokens):
            if (tokens[i] in ("-n", "--name")) and i + 1 < len(tokens):
                channel_name = tokens[i + 1]
                i += 2
            elif (tokens[i] in ("-c", "--cycle")) and i + 1 < len(tokens):
                seconds = parse_time_string(tokens[i + 1])
                i += 2
            else:
                i += 1

        if not channel_name and not seconds:
            parts = arg.split()
            if len(parts) >= 1:
                seconds = parse_time_string(parts[0])
                if seconds:
                    channel_name = parts[1] if len(parts) > 1 else None

        return channel_name, seconds

    async def _setup_periodic_clean(self, ctx, channel_name, seconds):
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
                        f"'{channel_name}' 이런 채널 없는데요"
                    )
                )
                return
            channel = found

        try:
            with get_db_session() as db:
                repo = self.container.periodic_clean_repository(db=db)
                repo.enable(ctx.guild.id, channel.id, channel.name, seconds)
        except Exception as e:
            await ctx.send(
                embed=ChannelEmbed.create_error_embed(
                    f"주기적 청소 등록 중 오류가 발생했습니다: {e}"
                )
            )
            return

        self._start_periodic_clean_task(ctx.guild, channel, seconds)
        period_str = format_seconds(seconds)
        msg = f"`#{channel.name}` 채널을 앞으로 {period_str}마다 청소합니다."
        embed = ChannelEmbed.create_clean_start_embed(msg)
        await ctx.send(embed=embed)

    async def clean_channel_once(self, ctx, channel_name=None):
        channel_service = self.container.channel_service()
        start_embed = ChannelEmbed.create_clean_start_embed(
            channel_name or ctx.channel.name
        )
        await ctx.send(embed=start_embed)
        success, message, new_channel = await channel_service.clean_channel(
            ctx.guild, ctx.channel, channel_name
        )
        if success and new_channel:
            success_embed = ChannelEmbed.create_clean_success_embed()
            await new_channel.send(embed=success_embed)
        else:
            error_embed = ChannelEmbed.create_error_embed(message)
            await ctx.send(embed=error_embed)

    @commands.command(
        name="청소.중지",
        aliases=["clean.stop", "청소멈춰", "청소끄기", "청소 중지"],
        description="청소.중지 [-n 채널명]",
    )
    @commands.has_permissions(manage_channels=True)
    async def stop_periodic_clean(self, ctx, *, arg: str = None):
        guild_id = ctx.guild.id
        channel = ctx.channel
        channel_name_to_search = channel.name

        channel_name = None
        if arg:
            tokens = shlex.split(arg)
            i = 0
            while i < len(tokens):
                if (tokens[i] in ("-n", "--name")) and i + 1 < len(tokens):
                    channel_name = tokens[i + 1]
                    i += 2
                else:
                    channel_name = arg
                    break

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
                repo = self.container.periodic_clean_repository(db=db)

                records = repo.find_by_channel_name(guild_id, channel_name_to_search)

                if not records:
                    await ctx.send(
                        embed=ChannelEmbed.create_error_embed(
                            f"'{channel_name_to_search}' 채널에 등록된 주기적 청소가 없습니다."
                        )
                    )
                    return

                # disabled_records = repo.disable_by_name(
                #     guild_id, channel_name_to_search
                # )
                # logger.info(
                #     f"DB에서 {len(disabled_records)}개 비활"
                # )

                cancelled_tasks = 0
                for record in records:
                    task_key = (guild_id, record.channel_id)
                    task = self.periodic_tasks.get(task_key)
                    if task:
                        task.cancel()
                        del self.periodic_tasks[task_key]
                        cancelled_tasks += 1

                await ctx.send(
                    embed=ChannelEmbed.create_clean_success_embed(
                        f"'{channel_name_to_search}' 채널의 주기적 청소가 중지되었습니다."
                    )
                )
        except Exception as e:
            await ctx.send(
                embed=ChannelEmbed.create_error_embed(
                    f"주기적 청소 중지 중 오류가 발생했습니다: {e}"
                )
            )
