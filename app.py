import discord
from discord.ext import commands
from shared.discord_token import TOKEN
import asyncio
import logging

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
from features.commands.Timeout import Timeout
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
    await bot.add_cog(Question(bot))
    await bot.add_cog(Lol(bot))
    await bot.add_cog(Anmauija(bot))
    await bot.add_cog(Jaseub(bot))
    await bot.add_cog(Valo(bot))
    await bot.add_cog(Timeout(bot))

@bot.event
async def on_ready():
    print(f'{bot.user.name} connected')

async def main():
    await setup()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())    
