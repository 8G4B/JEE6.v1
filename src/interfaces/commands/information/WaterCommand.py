from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.WaterEmbed import WaterEmbed
from src.clients.ApiGatewayClient import ApiGatewayClient

logger = logging.getLogger(__name__)


class WaterCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.api = ApiGatewayClient()

    @commands.command(
        name="한강",
        aliases=["수온", "한강수온", "water"],
        description="한강 수온 조회",
    )
    async def water(self, ctx):
        logger.info(f"water({ctx.guild.name}, {ctx.author.name})")

        try:
            data = await self.api.get_water_temp()

            if data.get("error"):
                embed = WaterEmbed.create_error_embed(data["error"])
            else:
                embed = WaterEmbed.create_water_embed(
                    data["hour"], data["minute"], data["temp"]
                )
            await ctx.reply(embed=embed)

        except Exception as e:
            logger.error(f"Error in water command: {e}")
            embed = WaterEmbed.create_error_embed("오류가 발생했습니다.")
            await ctx.reply(embed=embed)
