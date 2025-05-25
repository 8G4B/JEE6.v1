import asyncio
import logging
from src.infrastructure.di.Container import Container
from src.infrastructure.discord.Bot import Bot
from src.config.settings.Base import BaseConfig
from src.infrastructure.database.Connection import init_db, test_connection
from src.infrastructure.database.Session import create_tables

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    try:
        logger.info("데이터베이스 연결 테스트 중...")
        if not test_connection():
            logger.error("데이터베이스 연결 실패")
            return

        logger.info("데이터베이스 초기화 중...")
        init_db()

        logger.info("컨테이너 초기화 중...")
        create_tables()
        container = Container()

        logger.info("봇 인스턴스 생성 중...")
        bot = Bot(container)

        logger.info("봇 시작...")
        await bot.start(BaseConfig.DISCORD_TOKEN)

    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("봇이 안전하게 종료되었습니다.")
    except Exception as e:
        logger.error(f"사소한 오류 발생: {e}", exc_info=True)
