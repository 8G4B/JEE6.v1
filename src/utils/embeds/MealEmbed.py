import discord


class MealEmbed:
    @staticmethod
    def create_meal_embed(title: str, menu: str, cal_info: str = "") -> discord.Embed:
        embed = discord.Embed(
            title=title, description=menu, color=discord.Color.orange()
        )

        if cal_info:
            embed.set_footer(text=f"{cal_info}kcal")

        return embed

    @staticmethod
    def create_error_embed(description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류", description=description, color=discord.Color.red()
        )
