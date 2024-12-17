import discord
from discord.ext import commands
from discord_token import TOKEN
import asyncio
from commands.Greeting import Greeting
from commands.Gambling import Gambling
from commands.Time import Time
from commands.Meal import Meal
from commands.Information import Information
import logging

intents = discord.Intents.default()
intents.message_content = True
intents.members = False

bot = commands.Bot(command_prefix="!", intents=intents)    

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

async def setup():
    await bot.add_cog(Greeting(bot))
    await bot.add_cog(Gambling(bot))
    await bot.add_cog(Time(bot))
    await bot.add_cog(Meal(bot))
    await bot.add_cog(Information(bot))

@bot.event
async def on_ready():
    print(f'{bot.user.name} connected')

async def main():
    await setup()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
