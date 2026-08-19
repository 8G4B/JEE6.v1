import logging

from discord.ext import commands

from src.interfaces.commands.Base import BaseCommand
from src.services.HomeService import HomeService, format_home_status

logger = logging.getLogger(__name__)


class HomeCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.home_service = HomeService()

    @commands.command(
        name="집",
        aliases=["하교", "home"],
        description="금요일 또는 휴일 전날 하교까지 남은 시간을 확인합니다.",
    )
    async def home(self, ctx):
        try:
            status = await self.home_service.get_status()
            await ctx.reply(format_home_status(status))
        except Exception:
            logger.exception("하교 시간 계산 중 오류가 발생했습니다.")
            await ctx.reply(
                "하교 시간을 계산하는 중 오류가 발생했어요. 잠시 후 다시 시도해주세요."
            )
