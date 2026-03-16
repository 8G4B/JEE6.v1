from __future__ import annotations

import logging
from discord.ext import commands

from src.clients.FloodingApiClient import BotBaseError
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.FloodingEmbed import FloodingEmbed

logger = logging.getLogger(__name__)


class FloodingCommand(BaseCommand):
    def __init__(self, bot, api_service):
        super().__init__(bot, None)
        self._api_service = api_service
        self._in_progress: set[str] = set()

    @commands.command(name="플러딩.내정보", description="플러딩에서 내 정보를 조회합니다.")
    async def me(self, ctx: commands.Context) -> None:
        try:
            async with ctx.typing():
                status = await self._api_service.get_user_status(str(ctx.author.id))
            embed = FloodingEmbed.info(f"👤 {status.name}")
            embed.add_field(name="성별", value=status.status, inline=True)
            for k, v in list(status.extra.items())[:5]:
                embed.add_field(name=k, value=str(v), inline=True)
            embed.set_footer(text=ctx.author.display_name)
            await ctx.reply(embed=embed)
        except BotBaseError as e:
            await ctx.reply(embed=FloodingEmbed.error(e.user_message))
        except Exception as e:
            logger.error(f"플러딩 내정보 오류: {e}")
            await ctx.reply(embed=FloodingEmbed.error(f"오류가 발생했습니다: {e}"))

    @commands.command(name="플러딩.음악신청", aliases=["플러딩.기상음악신청"], description="유튜브 URL로 음악을 신청합니다.")
    async def request_music(self, ctx: commands.Context, music_url: str = None) -> None:
        if music_url is None:
            await ctx.reply(embed=FloodingEmbed.info("사용법", "`!플러딩.음악신청 <유튜브 URL>`"))
            return

        key = f"music:{ctx.author.id}"
        if key in self._in_progress:
            await ctx.reply(embed=FloodingEmbed.info("⏳ 처리 중", "이미 처리 중입니다."))
            return

        self._in_progress.add(key)
        try:
            async with ctx.typing():
                await self._api_service.request_music(str(ctx.author.id), music_url)
            await ctx.reply(embed=FloodingEmbed.success("🎵 음악 신청 완료", music_url))
        except BotBaseError as e:
            await ctx.reply(embed=FloodingEmbed.error(e.user_message))
        except Exception as e:
            logger.error(f"플러딩 음악신청 오류: {e}")
            await ctx.reply(embed=FloodingEmbed.error(f"오류가 발생했습니다: {e}"))
        finally:
            self._in_progress.discard(key)
