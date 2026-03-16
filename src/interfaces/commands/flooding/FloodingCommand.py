from __future__ import annotations

import asyncio
import logging
import discord
from discord.ext import commands

from src.clients.FloodingApiClient import BotBaseError
from src.interfaces.commands.Base import BaseCommand
from src.schemas.FloodingResponse import MusicItem
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

    @commands.command(name="플러딩.음악", aliases=["플러딩.기상음악"], description="오늘의 기상음악 목록을 조회합니다.")
    async def music_list(self, ctx: commands.Context) -> None:
        try:
            async with ctx.typing():
                items = await self._api_service.get_music_list(str(ctx.author.id))
        except BotBaseError as e:
            await ctx.reply(embed=FloodingEmbed.error(e.user_message))
            return
        except Exception as e:
            logger.error(f"플러딩 음악목록 오류: {e}")
            await ctx.reply(embed=FloodingEmbed.error(f"오류가 발생했습니다: {e}"))
            return

        if not items:
            await ctx.reply(embed=FloodingEmbed.info("🎵 오늘의 기상음악", "신청된 음악이 없습니다."))
            return

        def make_embed(item: MusicItem, page: int, total: int) -> discord.Embed:
            embed = FloodingEmbed.info(
                f"🎵 {item.music_name}",
                item.music_url,
            )
            embed.add_field(name="신청자", value=f"{item.proposer_name} ({item.proposer_school_number})", inline=True)
            embed.add_field(name="좋아요", value=str(item.like_count), inline=True)
            embed.set_thumbnail(url=item.thumbnail_image_url)
            embed.set_footer(text=f"{page}/{total}")
            return embed

        current = 0
        message = await ctx.reply(embed=make_embed(items[current], current + 1, len(items)))

        if len(items) == 1:
            return

        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) in ["◀️", "▶️"]
                and reaction.message.id == message.id
            )

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)

                if str(reaction.emoji) == "▶️" and current < len(items) - 1:
                    current += 1
                elif str(reaction.emoji) == "◀️" and current > 0:
                    current -= 1

                await message.edit(embed=make_embed(items[current], current + 1, len(items)))
                await message.remove_reaction(reaction, user)

            except asyncio.TimeoutError:
                await message.clear_reactions()
                break

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
