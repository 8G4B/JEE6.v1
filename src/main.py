import asyncio
from src.infrastructure.di.container import Container
from src.infrastructure.discord.bot import Bot
from src.config.settings.base import BaseConfig

async def main():
    container = Container()
    
    bot = Bot(container)
    
    async with bot:
        await bot.start(BaseConfig.DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main()) 