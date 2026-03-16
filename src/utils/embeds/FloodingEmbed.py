import discord


class FloodingEmbed:
    @staticmethod
    def success(title: str, description: str = None) -> discord.Embed:
        return discord.Embed(title=title, description=description, color=discord.Color.green())

    @staticmethod
    def error(description: str) -> discord.Embed:
        return discord.Embed(title="❗ 오류", description=description, color=discord.Color.red())

    @staticmethod
    def info(title: str, description: str = None) -> discord.Embed:
        return discord.Embed(title=title, description=description, color=discord.Color.blue())
