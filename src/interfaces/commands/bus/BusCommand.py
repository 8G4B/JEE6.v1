from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.BusEmbed import BusEmbed
from src.services.BusService import BusService

logger = logging.getLogger(__name__)


class BusCommands(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.bus_service = BusService()

    @commands.command(
        name="버스",
        aliases=["bus", "ㅂㅅ"],
        description="버스 도착 정보 조회",
    )
    async def bus(self, ctx):
        logger.info(f"bus_command({ctx.guild.name}, {ctx.author.name})")

        try:
            status, bus_info = await self.bus_service.get_bus_arrival_info()
            
            if status == "success" and bus_info:
                embed = BusEmbed.create_bus_arrival_embed(bus_info)
            else:
                # status가 에러 메시지인 경우
                embed = BusEmbed.create_error_embed(status)

            await ctx.reply(embed=embed)

        except Exception as e:
            logger.error(f"Error in bus command: {e}")
            await ctx.send(embed=BusEmbed.create_error_embed("버스 정보를 가져오는 중 오류가 발생했습니다.")) 