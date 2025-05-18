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

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)    

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
    await bot.add_cog(Justice(bot))
    await bot.add_cog(Clean(bot))

@bot.event
async def on_ready():
    print(f'{bot.user.name} connected')

async def main():
    if not test_connection():
        print("데이터베이스 연결 실패!")
        return
    
    init_db()
    print("데이터베이스 초기화 완료!")
    
    await setup()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())    
