from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.services.WaterService import WaterService
from src.utils.embeds.WaterEmbed import WaterEmbed

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
                embed = WaterEmbed.create_water_embed(hour, minute, temp)
                await ctx.reply(embed=embed)
            else:
                embed = WaterEmbed.create_error_embed("한강 수온 정보를 가져올 수 없습니다.")
                await ctx.reply(embed=embed)

        except Exception as e:
            logger.error(f"Error in water command: {e}")
            embed = WaterEmbed.create_error_embed("오류가 발생했습니다.")
            await ctx.reply(embed=embed)
