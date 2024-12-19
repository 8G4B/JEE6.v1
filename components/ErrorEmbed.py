import discord

def error_embed(description: str) -> discord.Embed:
    return discord.Embed(
        title="❗ 오류",
        description=description,
        color=discord.Color.red()
    )
  