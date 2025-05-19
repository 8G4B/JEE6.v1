import discord
from typing import List

class ValoEmbed:
    @staticmethod
    def create_tier_embed(title: str, description: str, tier: str) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.red()
        )
        return embed

    @staticmethod
    def create_history_embed(title: str, matches: List[dict]) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            color=discord.Color.red()
        )
        
        for match in matches:
            embed.add_field(
                name=match['name'],
                value=match['value'],
                inline=False
            )
        
        return embed

    @staticmethod
    def create_error_embed(description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류",
            description=description,
            color=discord.Color.red()
        ) 