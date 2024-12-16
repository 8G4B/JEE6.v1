import discord
from discord.ext import commands
import random
    
class Greeting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="안녕", aliases=['아녕', '안녕하세요', '아녕하세요', '안ㄴ녕'], description="안녕")
    async def greet(self, ctx):
        if ctx.author.name in ["aiden300.", "aiden300_"]:
            title = "야 이주언 싸려"
        elif random.random() <= 0.01:
            title = "야 싸려" 
        else:
            title = "안녕!"
            
        embed = discord.Embed(
            title=title,
            color=discord.Color.red() if title != "안녕!" else discord.Color.purple()
        )
        await ctx.reply(embed=embed)
        
    @commands.command(name="이주언", aliases=['주언'], description="이주언")
    async def greet(self, ctx):
        title = "병신"
        embed = discord.Embed(
            title=title,
            color=discord.Color.purple()
        )
        await ctx.reply(embed=embed)
    