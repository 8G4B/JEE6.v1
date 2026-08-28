import asyncio
import logging
from dataclasses import replace
from datetime import datetime

import discord
from discord.ext import commands

from src.interfaces.commands.Base import BaseCommand
from src.services.HomeService import HomeService
from src.utils.embeds.HomeEmbed import HomeEmbed

logger = logging.getLogger(__name__)
_COUNTDOWN_UPDATE_INTERVAL = 1


class HomeCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.home_service = HomeService()
        self._countdown_tasks: dict[int, asyncio.Task] = {}

    async def cog_unload(self) -> None:
        tasks = list(self._countdown_tasks.values())
        self._countdown_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _now(status):
        return datetime.now(status.now.tzinfo)

    def _stop_countdown(self, channel_id: int) -> None:
        task = self._countdown_tasks.pop(channel_id, None)
        if task is not None:
            task.cancel()

    def _start_countdown(self, channel_id: int, message, status) -> None:
        self._stop_countdown(channel_id)
        task = asyncio.create_task(
            self._update_countdown(message, status),
            name=f"home-countdown-{channel_id}",
        )
        self._countdown_tasks[channel_id] = task
        task.add_done_callback(
            lambda completed: self._discard_countdown_task(channel_id, completed)
        )

    def _discard_countdown_task(
        self,
        channel_id: int,
        completed: asyncio.Task,
    ) -> None:
        if self._countdown_tasks.get(channel_id) is completed:
            self._countdown_tasks.pop(channel_id, None)

    async def _update_countdown(self, message, status) -> None:
        loop = asyncio.get_running_loop()
        next_update = loop.time() + _COUNTDOWN_UPDATE_INTERVAL
        try:
            while status.state == "countdown" and status.target is not None:
                await asyncio.sleep(max(0, next_update - loop.time()))
                now = self._now(status)
                if now >= status.target:
                    status = await self.home_service.get_status(now)
                else:
                    status = replace(status, now=now)
                await message.edit(embed=HomeEmbed.create_home_embed(status))

                next_update += _COUNTDOWN_UPDATE_INTERVAL
                if next_update <= loop.time():
                    next_update = loop.time() + _COUNTDOWN_UPDATE_INTERVAL
        except asyncio.CancelledError:
            raise
        except (discord.NotFound, discord.Forbidden):
            logger.info("하교 카운트다운 메시지가 없어 갱신을 종료합니다.")
        except discord.HTTPException:
            logger.warning("하교 카운트다운 메시지 갱신에 실패했습니다.", exc_info=True)
        except Exception:
            logger.exception("하교 카운트다운 갱신 중 오류가 발생했습니다.")

    @commands.command(
        name="집",
        aliases=["하교", "home"],
        description="금요일 또는 휴일 전날 하교까지 남은 시간을 확인합니다.",
    )
    async def home(self, ctx):
        try:
            status = await self.home_service.get_status()
            message = await ctx.reply(embed=HomeEmbed.create_home_embed(status))
            if status.state == "countdown":
                self._start_countdown(ctx.channel.id, message, status)
            else:
                self._stop_countdown(ctx.channel.id)
        except Exception:
            logger.exception("하교 시간 계산 중 오류가 발생했습니다.")
            await ctx.reply(embed=HomeEmbed.create_error_embed())
