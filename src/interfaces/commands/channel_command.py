from discord.ext import commands, tasks
import logging
import re
import asyncio
from src.interfaces.commands.base_command import BaseCommand
from src.utils.embeds.channel_embed import ChannelEmbed
from sqlalchemy.orm import Session
from src.infrastructure.database.session import get_db_session

logger = logging.getLogger(__name__)

TIME_UNITS = {
    '초': 1, 's': 1, 'sec': 1,
    '분': 60, 'm': 60, 'min': 60,
    '시간': 3600, 'h': 3600, 'hr': 3600,
    '일': 86400, 'd': 86400, 'day': 86400
}

def parse_time_string(time_str):
    match = re.match(r"(\d+)\s*([a-zA-Z가-힣]+)", time_str)
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    unit = unit.lower()
    for k, v in TIME_UNITS.items():
        if unit.startswith(k):
            return value * v
    return None

def format_seconds(seconds):
    if seconds % 86400 == 0:
        return f"{seconds // 86400}일"
    elif seconds % 3600 == 0:
        return f"{seconds // 3600}시간"
    elif seconds % 60 == 0:
        return f"{seconds // 60}분"
    else:
        return f"{seconds}초"

class ChannelCommands(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.periodic_tasks = {}
        self._init_periodic_tasks()

    def _get_db(self):
        return self.container.db() if hasattr(self.container, 'db') else None

    def _init_periodic_tasks(self):
        db = get_db_session()
        try:
            repo = self.container.periodic_clean_repository(db=db)
            channel_service = self.container.channel_service()
            try:
                schedules = repo.get_all_enabled()
                for sched in schedules:
                    guild = self.bot.get_guild(sched.guild_id)
                    if not guild:
                        continue
                    channel = guild.get_channel(sched.channel_id)
                    if not channel:
                        continue
                    self._start_periodic_clean_task(guild, channel, sched.interval_seconds)
            except Exception as e:
                if "Table" in str(e) and "doesn't exist" in str(e):
                    logger.warning(f"주기적 청소 테이블이 아직 생성되지 않았습니다: {e}")
                else:
                    logger.error(f"주기적 청소 작업 초기화 중 오류: {e}")
        finally:
            db.close()

    def _start_periodic_clean_task(self, guild, channel, seconds):
        key = (guild.id, channel.id)
        if key in self.periodic_tasks:
            return
        channel_service = self.container.channel_service()
        async def periodic_clean():
            current_channel = channel
            while True:
                try:
                    start_embed = ChannelEmbed.create_clean_start_embed(current_channel.name)
                    await current_channel.send(embed=start_embed)
                    success, message, new_channel = await channel_service.clean_channel(
                        guild, current_channel, None
                    )
                    if success and new_channel:
                        success_embed = ChannelEmbed.create_clean_success_embed()
                        await new_channel.send(embed=success_embed)
                        current_channel = new_channel
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
        name='청소',
        aliases=['clean', 'c', 'C', 'CLEAN', 'ㅊ'],
        description="채널을 청소합니다. (!청소 [-n 채널명] [-c 주기])"
    )
    @commands.has_permissions(manage_channels=True)
    async def clean_channel(self, ctx, *, arg: str = None):
        channel_name = None
        seconds = None
        if arg:
            import shlex
            tokens = shlex.split(arg)
            i = 0
            while i < len(tokens):
                if tokens[i] == '-n' and i + 1 < len(tokens):
                    channel_name = tokens[i + 1]
                    i += 2
                elif tokens[i] == '-c' and i + 1 < len(tokens):
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
            if seconds:
                channel = ctx.channel
                if channel_name:
                    found = None
                    for ch in ctx.guild.text_channels:
                        if ch.name == channel_name:
                            found = ch
                            break
                    if not found:
                        await ctx.send(embed=ChannelEmbed.create_error_embed(f"'{channel_name}' 이런 채널 없는데요"))
                        return
                    channel = found
                db = get_db_session()
                try:
                    repo = self.container.periodic_clean_repository(db=db)
                    repo.enable(ctx.guild.id, channel.id, seconds)
                finally:
                    db.close()
                self._start_periodic_clean_task(ctx.guild, channel, seconds)
                period_str = format_seconds(seconds)
                msg = f"`#{channel.name}` 채널을 앞으로 {period_str}마다 청소합니다."
                embed = ChannelEmbed.create_clean_start_embed(msg)
                await ctx.send(embed=embed)
                return
            if channel_name and not seconds:
                await self.clean_channel_once(ctx, channel_name)
                return
        await self.clean_channel_once(ctx)

    async def clean_channel_once(self, ctx, channel_name=None):
        logger.info(f"clean_channel_once({ctx.guild.name}, {ctx.author.name})")
        channel_service = self.container.channel_service()
        start_embed = ChannelEmbed.create_clean_start_embed(
            channel_name or ctx.channel.name
        )
        await ctx.send(embed=start_embed)
        success, message, new_channel = await channel_service.clean_channel(
            ctx.guild,
            ctx.channel,
            channel_name
        )
        if success and new_channel:
            success_embed = ChannelEmbed.create_clean_success_embed()
            await new_channel.send(embed=success_embed)
        else:
            error_embed = ChannelEmbed.create_error_embed(message)
            await ctx.send(embed=error_embed)

    @commands.command(
        name='청소.중지',
        aliases=['clean.stop', '청소.멈춰', '청소.끄기'],
        description="주기적 채널 청소를 중단합니다."
    )
    @commands.has_permissions(manage_channels=True)
    async def stop_periodic_clean(self, ctx, *, channel_name: str = None):
        channel = ctx.channel
        if channel_name:
            found = None
            for ch in ctx.guild.text_channels:
                if ch.name == channel_name:
                    found = ch
                    break
            if not found:
                await ctx.send(embed=ChannelEmbed.create_error_embed(f"'{channel_name}' 이런 채널 없는데요"))
                return
            channel = found
        key = (ctx.guild.id, channel.id)
        db = get_db_session()
        try:
            repo = self.container.periodic_clean_repository(db=db)
            repo.disable(ctx.guild.id, channel.id)
        finally:
            db.close()
        task = self.periodic_tasks.get(key)
        if task:
            task.cancel()
            del self.periodic_tasks[key]
            await ctx.send(embed=ChannelEmbed.create_clean_success_embed())
        else:
            await ctx.send(embed=ChannelEmbed.create_error_embed("이 채널에 등록된 주기적 청소가 없습니다."))