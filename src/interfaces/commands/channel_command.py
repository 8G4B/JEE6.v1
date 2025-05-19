from discord.ext import commands, tasks
import logging
import re
import asyncio
from src.interfaces.commands.base_command import BaseCommand
from src.utils.embeds.channel_embed import ChannelEmbed
from sqlalchemy.orm import Session
from src.infrastructure.database.session import get_db_session
from sqlalchemy import text

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
                self._update_channel_names(db, repo)
                
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
                elif "Unknown column" in str(e) and "channel_name" in str(e):
                    logger.warning(f"channel_name 컬럼이 아직 추가되지 않았습니다. 앱을 재시작하면 자동으로 추가됩니다: {e}")
                else:
                    logger.error(f"주기적 청소 작업 초기화 중 오류: {e}")
        finally:
            db.close()

    def _update_channel_names(self, db, repo):
        try:
            result = db.execute(text("SELECT guild_id, channel_id FROM periodic_clean WHERE channel_name = '' OR channel_name IS NULL"))
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
                    text("UPDATE periodic_clean SET channel_name = :name WHERE guild_id = :guild_id AND channel_id = :channel_id"),
                    {"name": channel.name, "guild_id": guild_id, "channel_id": channel_id}
                )
                updated += 1
                
            if updated > 0:
                db.commit()
                logger.info(f"{updated}개의 레코드에 channel_name 필드가 업데이트되었습니다.")
        except Exception as e:
            logger.error(f"channel_name 업데이트 중 오류: {e}")

    def _start_periodic_clean_task(self, guild, channel, seconds):
        key = (guild.id, channel.id)
        logger.info(f"주기적 청소 등록: guild_id={guild.id}, channel_id={channel.id}, channel_name={channel.name}, seconds={seconds}")
        if key in self.periodic_tasks:
            logger.info(f"이미 메모리에 등록된 태스크 존재: {key}")
            return
        channel_service = self.container.channel_service()
        async def periodic_clean():
            current_channel = channel
            old_key = (guild.id, current_channel.id)
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
                        
                        new_key = (guild.id, current_channel.id)
                        if old_key != new_key and old_key in self.periodic_tasks:
                            task = self.periodic_tasks.pop(old_key)
                            self.periodic_tasks[new_key] = task
                            old_key = new_key
                            logger.info(f"태스크 키 업데이트: {old_key} -> {new_key}")
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
        logger.info(f"주기적 청소 태스크 시작: {key}")

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
                    logger.info(f"주기적 청소 DB 등록: guild_id={ctx.guild.id}, channel_id={channel.id}, channel_name={channel.name}, seconds={seconds}")
                    repo.enable(ctx.guild.id, channel.id, channel.name, seconds)
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
        name='청소중지',
        aliases=['clean.stop', '청소멈춰', '청소끄기', '청소.중지', '청소 중지'],
        description="주기적 채널 청소를 중단합니다."
    )
    @commands.has_permissions(manage_channels=True)
    async def stop_periodic_clean(self, ctx, *, channel_name: str = None):
        db = get_db_session()
        guild_id = ctx.guild.id
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
        
        logger.info(f"주기적 청소 중지 요청: guild_id={guild_id}, channel_name={channel_name_to_search}")
        
        try:
            repo = self.container.periodic_clean_repository(db=db)
            
            records = repo.find_by_channel_name(guild_id, channel_name_to_search)
            
            if not records:
                logger.info(f"DB에 '{channel_name_to_search}' 채널의 주기적 청소 기록이 없습니다.")
                await ctx.send(embed=ChannelEmbed.create_error_embed(f"'{channel_name_to_search}' 채널에 등록된 주기적 청소가 없습니다."))
                db.close()
                return
            
            disabled_records = repo.disable_by_name(guild_id, channel_name_to_search)
            logger.info(f"DB에서 {len(disabled_records)}개의 주기적 청소 기록을 비활성화했습니다.")
            
            cancelled_tasks = 0
            for record in records:
                task_key = (guild_id, record.channel_id)
                task = self.periodic_tasks.get(task_key)
                if task:
                    task.cancel()
                    del self.periodic_tasks[task_key]
                    cancelled_tasks += 1
                    logger.info(f"메모리에서 태스크 취소: {task_key}")
            
            await ctx.send(embed=ChannelEmbed.create_clean_success_embed(f"'{channel_name_to_search}' 채널의 주기적 청소가 중지되었습니다."))
        finally:
            db.close()