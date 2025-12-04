from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.services.WaterService import WaterService

logger = logging.getLogger(__name__)


class WaterCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.water_service = WaterService()

    @commands.command(
        name="한강",
        aliases=["수온", "한강수온", "water"],
        description="한강 수온 조회",
    )
    async def water(self, ctx):
        logger.info(f"water({ctx.guild.name}, {ctx.author.name})")

        try:
            result = await self.water_service.get_han_river_temp()

            if result:
                hour, minute, temp = result
                await ctx.reply(f"{hour}시 {minute}분 한강 수온은 {temp}°C 입니다")
            else:
                await ctx.reply("한강 수온 정보를 가져올 수 없습니다.")

        except Exception as e:
            logger.error(f"Error in water command: {e}")
            await ctx.reply("오류가 발생했습니다.")
