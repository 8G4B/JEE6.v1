import discord
from datetime import datetime


class TimeEmbed:
    @staticmethod
    def create_time_embed(time: datetime) -> discord.Embed:
        return discord.Embed(
            title="현재 시간",
            description=f"🗓️ {time.strftime('%Y년 %m월 %d일')}\n⌚️ {time.strftime('%H시 %M분 %S초')}",
            color=discord.Color.pink(),
        )
