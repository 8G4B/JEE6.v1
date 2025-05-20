import discord


class MealEmbed:
    @staticmethod
    def create_meal_embed(title: str, menu: str) -> discord.Embed:
        return discord.Embed(
            title=title, description=menu, color=discord.Color.orange()
        )

    @staticmethod
    def create_error_embed(description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류", description=description, color=discord.Color.red()
        )
