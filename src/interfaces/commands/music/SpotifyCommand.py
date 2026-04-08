import discord
from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.clients.ApiGatewayClient import ApiGatewayClient

logger = logging.getLogger(__name__)


class SpotifyCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.api = ApiGatewayClient()

    @commands.command(name="오노추", description="Spotify 플레이리스트에서 랜덤 곡을 추천합니다.")
    async def random_track(self, ctx):
        async with ctx.typing():
            data = await self.api.get_random_track()

        if data.get("error"):
            embed = discord.Embed(
                title="❌ 오류",
                description=data["error"],
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed)
            return

        embed = discord.Embed(
            title=data["name"],
            url=data["url"],
            description=f"**{data['artists']}**\n앨범: {data['album']}",
            color=discord.Color.from_rgb(30, 215, 96),
        )
        genre_text = ", ".join(data["genres"][:2]) if data.get("genres") else ""
        footer = f"⏱ {data['duration']}"
        if genre_text:
            footer += f"  |  {genre_text}"
        embed.set_footer(text=footer)
        if data.get("image"):
            embed.set_thumbnail(url=data["image"])

        await ctx.reply(embed=embed)
