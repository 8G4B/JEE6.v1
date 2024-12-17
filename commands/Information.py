import discord
from discord.ext import commands
    
class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="정보", aliases=['도움'], description="정보")
    async def information(self, ctx):
        latency = round(self.bot.latency * 1000) 
        embed = discord.Embed(
            title="❗ JEE6",
            description = f"- [명령어](https://github.com/8G4B/JEE6.v1/blob/master/README.md)\n- [소스코드](https://github.com/8G4B/JEE6.v1)\n- [만든놈](https://github.com/976520)\n\n- 핑: {latency}ms",
            color=discord.Color.yellow()
        )
        await ctx.reply(embed=embed)
    