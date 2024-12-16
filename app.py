import discord
from discord.ext import commands
from discord_token import TOKEN
import asyncio
from commands.Greeting import Greeting
from commands.Gambling import Gambling
from commands.Time import Time
from commands.Meal import Meal

intents = discord.Intents.default()
intents.message_content = True
intents.members = False

bot = commands.Bot(command_prefix="!", intents=intents)    

async def setup(bot):
    await bot.add_cog(Greeting(bot))
    await bot.add_cog(Gambling(bot))
    await bot.add_cog(Time(bot))
    await bot.add_cog(Meal(bot))

async def main():
    async with bot:
        await setup(bot)
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
