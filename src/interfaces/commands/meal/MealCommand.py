from discord.ext import commands
import logging
from datetime import datetime, timedelta
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.MealEmbed import MealEmbed
from src.services.MealService import MealService

logger = logging.getLogger(__name__)


class MealCommands(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.meal_service = MealService()

    async def _handle_meal_command(
        self, ctx, date: str, meal_code: str, title: str, error_message: str
    ):
        logger.info(
            f"meal_command({ctx.guild.name}, {ctx.author.name}, {date}, {meal_code})"
        )

        try:
            title, menu = await self.meal_service.get_meal_by_type(
                date, meal_code, title
            )

            if title and menu:
                embed = MealEmbed.create_meal_embed(title, menu)
            else:
                embed = MealEmbed.create_error_embed(error_message)

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

        try:
            title, menu = await self.meal_service.get_current_meal(datetime.now())

            if title and menu:
                embed = MealEmbed.create_meal_embed(title, menu)
            else:
                embed = MealEmbed.create_error_embed("나이스 API 이슈")

            await ctx.reply(embed=embed)

        except Exception as e:
            logger.error(e)
            await ctx.send(embed=MealEmbed.create_error_embed(e))

    @commands.command(
        name="급식.아침",
        aliases=["급식.조식", "meal.breakfast", "ㄱㅅ.ㅇㅊ"],
        description="아침 급식 조회",
    )
    async def breakfast(self, ctx):
        await self._handle_meal_command(
            ctx,
            datetime.now().strftime("%Y%m%d"),
            "1",
            "🍳 아침",
            "조식 정보를 가져올 수 없습니다.",
        )

    @commands.command(
        name="급식.점심",
        aliases=["급식.중식", "meal.lunch", "ㄱㅅ.ㅈㅅ"],
        description="점심 급식 조회",
    )
    async def lunch(self, ctx):
        await self._handle_meal_command(
            ctx,
            datetime.now().strftime("%Y%m%d"),
            "2",
            "🍚 점심",
            "중식 정보를 가져올 수 없습니다.",
        )

    @commands.command(
        name="급식.저녁",
        aliases=["급식.석식", "meal.dinner", "ㄱㅅ.ㅓㄴ"],
        description="저녁 급식 조회",
    )
    async def dinner(self, ctx):
        await self._handle_meal_command(
            ctx,
            datetime.now().strftime("%Y%m%d"),
            "3",
            "🍖 저녁",
            "석식 정보를 가져올 수 없습니다.",
        )

    @commands.command(
        name="급식.내일아침",
        aliases=["급식.내일조식", "meal.tomorrow_breakfast", "ㄱㅅ.ㄴㅇㅊ"],
        description="내일 아침 급식 조회",
    )
    async def tomorrow_breakfast(self, ctx):
        await self._handle_meal_command(
            ctx,
            (datetime.now() + timedelta(days=1)).strftime("%Y%m%d"),
            "1",
            "🍳 내일 아침",
            "내일 조식 정보를 가져올 수 없습니다.",
        )

    @commands.command(
        name="급식.내일점심",
        aliases=["급식.내일중식", "meal.tomorrow_lunch", "ㄱㅅ.ㄴㅈㅅ"],
        description="내일 점심 급식 조회",
    )
    async def tomorrow_lunch(self, ctx):
        await self._handle_meal_command(
            ctx,
            (datetime.now() + timedelta(days=1)).strftime("%Y%m%d"),
            "2",
            "🍚 내일 점심",
            "내일 중식 정보를 가져올 수 없습니다.",
        )

    @commands.command(
        name="급식.내일저녁",
        aliases=["급식.내일석식", "meal.tomorrow_dinner", "ㄱㅅ.ㄴㅓㄴ"],
        description="내일 저녁 급식 조회",
    )
    async def tomorrow_dinner(self, ctx):
        await self._handle_meal_command(
            ctx,
            (datetime.now() + timedelta(days=1)).strftime("%Y%m%d"),
            "3",
            "🍖 내일 저녁",
            "내일 석식 정보를 가져올 수 없습니다.",
        )
