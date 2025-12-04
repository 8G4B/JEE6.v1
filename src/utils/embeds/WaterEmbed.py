import discord


class WaterEmbed:
    @staticmethod
    def create_water_embed(hour: str, minute: str, temp: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"{hour}시 {minute}분 한강 수온은 {temp}°C 입니다",
            color=discord.Color.blue()
        )
        return embed

    @staticmethod
    def create_error_embed(description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류",
            description=description,
            color=discord.Color.red()
        )
