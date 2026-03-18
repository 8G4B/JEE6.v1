import discord
import random
from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.services.SpotifyService import SpotifyService
from src.config.settings.base import BaseConfig

logger = logging.getLogger(__name__)


class SpotifyCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self._service = SpotifyService()

    @commands.command(name="오노추", description="Spotify 플레이리스트에서 랜덤 곡을 추천합니다.")
    async def random_track(self, ctx):
        playlist_ids = BaseConfig.SPOTIFY_PLAYLIST_ID
        if not playlist_ids:
            await ctx.reply("❌ SPOTIFY_PLAYLIST_ID가 설정되지 않았습니다.")
            return

        playlist_id = random.choice(playlist_ids)
        async with ctx.typing():
            track = await self._service.get_random_track(playlist_id)

        if track is None:
            embed = discord.Embed(
                title="❌ 오류",
                description="곡을 가져오는데 실패했습니다. Spotify 설정을 확인해주세요.",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed)
            return

        embed = discord.Embed(
            title=track["name"],
            url=track["url"],
            description=f"**{track['artists']}**\n앨범: {track['album']}",
            color=discord.Color.from_rgb(30, 215, 96),  # Spotify green
        )
        genre_text = ", ".join(track["genres"][:2]) if track.get("genres") else ""
        footer = f"⏱ {track['duration']}"
        if genre_text:
            footer += f"  |  {genre_text}"
        embed.set_footer(text=footer)
        if track["image"]:
            embed.set_thumbnail(url=track["image"])

        await ctx.reply(embed=embed)
