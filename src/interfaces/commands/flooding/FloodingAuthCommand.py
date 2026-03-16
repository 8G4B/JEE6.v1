from __future__ import annotations

import logging
import discord
from discord.ext import commands

from src.interfaces.commands.Base import BaseCommand
from src.utils.errors import BotBaseError
from src.utils.time.datetimeFormatter import format_time

logger = logging.getLogger(__name__)


class FloodingAuthCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self._in_progress: set[str] = set()

    @property
    def _auth_service(self):
        return self.container.flooding_auth_service()

    @commands.command(name="플러딩.로그인", description="플러딩 계정을 Discord와 연동합니다. !플러딩.로그인 <이메일(@gsm.hs.kr)> <비밀번호>")
    async def link(self, ctx: commands.Context, email: str, password: str) -> None:
        key = f"link:{ctx.author.id}"
        if key in self._in_progress:
            await ctx.reply("⏳ 이미 처리 중입니다.")
            return

        self._in_progress.add(key)
        try:
            async with ctx.typing():
                profile = await self._auth_service.login_with_credentials(
                    discord_user_id=str(ctx.author.id),
                    email=email,
                    password=password,
                )
            embed = discord.Embed(
                title="✅ 연동 완료",
                description=f"플러딩 **{profile.display_name or profile.username}** 계정과 연동되었습니다.",
                color=discord.Color.green(),
            )
            await ctx.reply(embed=embed)
        except BotBaseError as e:
            await ctx.reply(f"❌ {e.user_message}")
        except Exception as e:
            logger.error(f"플러딩 연동 오류: {e}")
            await ctx.reply(f"❌ 오류가 발생했습니다: {e}")
        finally:
            self._in_progress.discard(key)

    @commands.command(name="플러딩.로그아웃", description="플러딩 계정 연동을 해제합니다.")
    async def unlink(self, ctx: commands.Context) -> None:
        try:
            await self._auth_service.logout(str(ctx.author.id))
            await ctx.reply("🔓 플러딩 연동이 해제되었습니다.")
        except Exception as e:
            logger.error(f"플러딩 연동해제 오류: {e}")
            await ctx.reply(f"❌ 오류가 발생했습니다: {e}")