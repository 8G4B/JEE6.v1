from __future__ import annotations

import logging
import discord
from discord.ext import commands

from src.clients.FloodingApiClient import BotBaseError
from src.interfaces.commands.Base import BaseCommand

logger = logging.getLogger(__name__)


class FloodingCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self._in_progress: set[str] = set()

    @property
    def _api_service(self):
        return self.container.flooding_api_service()

    @commands.command(name="플러딩.내정보", description="플러딩에서 내 정보를 조회합니다.")
    async def me(self, ctx: commands.Context) -> None:
        try:
            async with ctx.typing():
                status = await self._api_service.get_user_status(str(ctx.author.id))
            embed = discord.Embed(title=f"👤 {status.name}", color=discord.Color.blue())
            embed.add_field(name="상태", value=status.status, inline=True)
            for k, v in list(status.extra.items())[:5]:
                embed.add_field(name=k, value=str(v), inline=True)
            embed.set_footer(text=ctx.author.display_name)
            await ctx.reply(embed=embed)
        except BotBaseError as e:
            await ctx.reply(f"❌ {e.user_message}")
        except Exception as e:
            logger.error(f"플러딩 내정보 오류: {e}")
            await ctx.reply(f"❌ 오류가 발생했습니다: {e}")

    @commands.command(name="플러딩.음악신청", aliases=["플러딩.음악"], description="유튜브 URL로 음악을 신청합니다.")
    async def request_music(self, ctx: commands.Context, music_url: str) -> None:
        """사용법: !플러딩.음악신청 <유튜브 URL>"""
        key = f"music:{ctx.author.id}"
        if key in self._in_progress:
            await ctx.reply("⏳ 이미 처리 중입니다.")
            return

        self._in_progress.add(key)
        try:
            async with ctx.typing():
                await self._api_service.request_music(str(ctx.author.id), music_url)
            await ctx.reply("🎵 음악 신청이 완료되었습니다.")
        except BotBaseError as e:
            await ctx.reply(f"❌ {e.user_message}")
        except Exception as e:
            logger.error(f"플러딩 음악신청 오류: {e}")
            await ctx.reply(f"❌ 오류가 발생했습니다: {e}")
        finally:
            self._in_progress.discard(key)