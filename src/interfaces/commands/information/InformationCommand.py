from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.InformationEmbed import InformationEmbed
from src.infrastructure.database.Connection import test_connection

logger = logging.getLogger(__name__)


class InformationCommands(BaseCommand):
    @commands.command(
        name="정보",
        aliases=["도움", "info", "help"],
        description="봇 정보를 보여줍니다.",
    )
    async def information(self, ctx):
        logger.info(f"information({ctx.guild.name}, {ctx.author.name})")

        try:
            latency = round(self.bot.latency * 1000)

            db_status = "🟢 굿" if test_connection() else "🔴 좆됨"

            embed = InformationEmbed.create_info_embed(latency, db_status)

            await ctx.reply(embed=embed)

        except Exception as e:
            logger.error(f"정보 명령어 처리 중 오류: {e}")
            await ctx.send(f"오류가 발생했습니다: {e}")
