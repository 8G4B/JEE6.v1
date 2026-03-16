from __future__ import annotations

import logging
import discord
from discord.ext import commands

from src.clients.FloodingApiClient import BotBaseError
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.FloodingEmbed import FloodingEmbed
from src.utils.time.datetimeFormatter import format_time

logger = logging.getLogger(__name__)


class FloodingAuthCommand(BaseCommand):
    def __init__(self, bot, auth_service):
        super().__init__(bot, None)
        self._auth_service = auth_service
        self._in_progress: set[str] = set()

    @commands.command(name="플러딩.로그인", description="플러딩 계정을 Discord와 연동합니다.")
    async def link(self, ctx: commands.Context, email: str = None, password: str = None) -> None:
        if email is None or password is None:
            await ctx.reply(embed=FloodingEmbed.info("사용법", "`!플러딩.로그인 <이메일(@gsm.hs.kr)> <비밀번호>`"))
            return

        if ctx.guild is not None:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

        key = f"link:{ctx.author.id}"
        if key in self._in_progress:
            await ctx.author.send(embed=FloodingEmbed.info("⏳ 처리 중", "이미 처리 중입니다."))
            return

        self._in_progress.add(key)
        try:
            async with ctx.typing():
                profile = await self._auth_service.login_with_credentials(
                    discord_user_id=str(ctx.author.id),
                    email=email,
                    password=password,
                )
            await ctx.author.send(embed=FloodingEmbed.success(
                "✅ 연동 완료",
                f"플러딩 **{profile.display_name or profile.username}** 계정과 연동되었습니다.",
            ))
        except BotBaseError as e:
            await ctx.author.send(embed=FloodingEmbed.error(e.user_message))
        except Exception as e:
            logger.error(f"플러딩 연동 오류: {e}")
            await ctx.author.send(embed=FloodingEmbed.error(f"오류가 발생했습니다: {e}"))
        finally:
            self._in_progress.discard(key)

    @commands.command(name="플러딩.로그아웃", description="플러딩 계정 연동을 해제합니다.")
    async def unlink(self, ctx: commands.Context) -> None:
        try:
            await self._auth_service.logout(str(ctx.author.id))
            await ctx.reply(embed=FloodingEmbed.success("🔓 연동 해제", "플러딩 연동이 해제되었습니다."))
        except Exception as e:
            logger.error(f"플러딩 연동해제 오류: {e}")
            await ctx.reply(embed=FloodingEmbed.error(f"오류가 발생했습니다: {e}"))

    @commands.command(name="플러딩.상태", description="플러딩 연동 상태를 확인합니다.")
    async def link_status(self, ctx: commands.Context) -> None:
        try:
            status = await self._auth_service.get_link_status(str(ctx.author.id))
            if not status.is_linked:
                await ctx.reply(embed=FloodingEmbed.error("연동된 플러딩 계정이 없습니다. `!플러딩.로그인 <이메일> <비밀번호>`로 연동해주세요."))
                return
            embed = FloodingEmbed.info("🔗 플러딩 연동 상태")
            embed.add_field(name="플러딩 계정 ID", value=status.flooding_user_id, inline=False)
            if status.linked_at:
                embed.add_field(name="연동 일시", value=format_time(status.linked_at), inline=True)
            if status.token_expires_at:
                embed.add_field(name="토큰 만료", value=format_time(status.token_expires_at), inline=True)
            await ctx.reply(embed=embed)
        except Exception as e:
            logger.error(f"플러딩 연동상태 오류: {e}")
            await ctx.reply(embed=FloodingEmbed.error(f"오류가 발생했습니다: {e}"))
