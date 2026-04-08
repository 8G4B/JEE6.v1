from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.MealEmbed import MealEmbed
from src.clients.ApiGatewayClient import ApiGatewayClient

logger = logging.getLogger(__name__)


class MealCommands(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.api = ApiGatewayClient()

    async def _send_meal(self, ctx, meal_type: str, day: str):
        try:
            data = await self.api.get_meal(meal_type=meal_type, day=day)

            if data.get("error"):
                embed = MealEmbed.create_error_embed(data["error"])
            elif data.get("menu"):
                embed = MealEmbed.create_meal_embed(
                    data["title"], data["menu"], data.get("cal_info", "")
                )
            else:
                embed = MealEmbed.create_error_embed("급식 정보를 가져올 수 없습니다.")

            await ctx.reply(embed=embed)
        except Exception as e:
            logger.error(e)
            await ctx.send(embed=MealEmbed.create_error_embed(e))

    @commands.command(
        name="급식",
        aliases=["밥", "meal", "ㄱㅅ"],
        description="현재 시간에 맞는 급식 조회",
    )
    async def meal(self, ctx):
        logger.info(f"meal({ctx.guild.name}, {ctx.author.name})")
        await self._send_meal(ctx, "auto", "today")

    @commands.command(
        name="급식.아침",
        aliases=["급식.조식", "meal.breakfast", "ㄱㅅ.ㅇㅊ", "아침"],
        description="아침 급식 조회",
    )
    async def breakfast(self, ctx):
        await self._send_meal(ctx, "breakfast", "today")

    @commands.command(
        name="급식.점심",
        aliases=["급식.중식", "meal.lunch", "ㄱㅅ.ㅈㅅ", "점심"],
        description="점심 급식 조회",
    )
    async def lunch(self, ctx):
        await self._send_meal(ctx, "lunch", "today")

    @commands.command(
        name="급식.저녁",
        aliases=["급식.석식", "meal.dinner", "ㄱㅅ.ㅈㄴ", "저녁"],
        description="저녁 급식 조회",
    )
    async def dinner(self, ctx):
        await self._send_meal(ctx, "dinner", "today")

    @commands.command(
        name="급식.내일아침",
        aliases=["급식.내일조식", "meal.tomorrow_breakfast", "ㄱㅅ.ㄴㅇㅊ", "내일아침"],
        description="내일 아침 급식 조회",
    )
    async def tomorrow_breakfast(self, ctx):
        await self._send_meal(ctx, "breakfast", "tomorrow")

    @commands.command(
        name="급식.내일점심",
        aliases=["급식.내일중식", "meal.tomorrow_lunch", "ㄱㅅ.ㄴㅈㅅ", "내일점심"],
        description="내일 점심 급식 조회",
    )
    async def tomorrow_lunch(self, ctx):
        await self._send_meal(ctx, "lunch", "tomorrow")

    @commands.command(
        name="급식.내일저녁",
        aliases=["급식.내일석식", "meal.tomorrow_dinner", "ㄱㅅ.ㄴㅓㄴ", "내일저녁"],
        description="내일 저녁 급식 조회",
    )
    async def tomorrow_dinner(self, ctx):
        await self._send_meal(ctx, "dinner", "tomorrow")
