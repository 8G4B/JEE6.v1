import discord
from typing import List


class LolEmbed:
    @staticmethod
    def create_tier_embed(title: str, description: str, tier: str) -> discord.Embed:
        embed = discord.Embed(
            title=title, description=description, color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(url=f"attachment://{tier}.png")
        return embed

    @staticmethod
    def create_history_embed(title: str, matches: List[dict]) -> discord.Embed:
        embed = discord.Embed(title=title, color=discord.Color.blue())

        for match in matches:
            embed.add_field(name=match["name"], value=match["value"], inline=False)

        return embed

    @staticmethod
    def create_rotation_embed(title: str, champion_names: List[str]) -> discord.Embed:
        embed = discord.Embed(title=title, color=discord.Color.blue())

        description = ""
        for i, name in enumerate(champion_names):
            description += f"`{name}`"
            if i < len(champion_names) - 1:
                description += " "
            if (i + 1) % 5 == 0:
                description += "\n"

        embed.description = description
        return embed

    @staticmethod
    def create_error_embed(description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류", description=description, color=discord.Color.red()
        )
