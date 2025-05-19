import discord
from discord.ext import commands
from shared.discord_token import TOKEN
import asyncio
import logging
from shared.database import init_db, test_connection

from features.commands.Greeting import Greeting
from features.commands.Gambling import Gambling
from features.commands.Time import Time
from features.commands.Meal import Meal
from features.commands.Information import Information
from features.commands.Question import Question
from features.commands.Lol import Lol
from features.commands.Valo import Valo
from features.alarm.Anmauija import Anmauija
from features.alarm.Jaseub import Jaseub
from features.commands.Justice import Justice
from features.commands.Clean import Clean

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def setup():
    logger.info("명령어 add_cog 시작")
    await bot.add_cog(Greeting(bot))
    await bot.add_cog(Gambling(bot))
    await bot.add_cog(Time(bot))
    await bot.add_cog(Meal(bot))
    await bot.add_cog(Information(bot))
    await bot.add_cog(Question(bot))
    await bot.add_cog(Lol(bot))
    await bot.add_cog(Anmauija(bot))
    await bot.add_cog(Jaseub(bot))
    await bot.add_cog(Valo(bot))
    await bot.add_cog(Justice(bot))
    await bot.add_cog(Clean(bot))
    logger.info("명령어 add_cog 완료")


@bot.event
async def on_ready():
    logger.info(f"{bot.user.name} 봇 연결 완료")


async def main():
    try:
        logger.info("데이터베이스 연결 테스트")
        if not await test_connection():
            logger.error("데이터베이스 연결 실패")
            return

        logger.info("데이터베이스 초기화")
        if not await init_db():
            logger.error("데이터베이스 초기화 실패")
            return

        logger.info("데이터베이스 초기화 완료")

        logger.info("명령어 설정")
        await setup()

        logger.info("봇 시작")
        await bot.start(TOKEN)
    except Exception as e:
        logger.error(f"봇 시작 실패: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("봇 시작")
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"봇 시작 실패: {e}", exc_info=True)
