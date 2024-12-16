import discord
from discord.ext import commands

class Meal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.command(name='급식.아침', description='아침 조회')
    async def breakfast(self, ctx):
        embed = discord.Embed(
            title="아침",
            description="test",
            color=discord.Color.purple()
        )
        await ctx.message.delete()
        await ctx.send(f"{ctx.author.mention}", embed=embed)
        
    @commands.command(name='급식.점심', description='점심 조회')
    async def lunch(self, ctx):
        embed = discord.Embed(
            title="점심", 
            description="test",
            color=discord.Color.purple()
        )
        await ctx.message.delete()
        await ctx.send(f"{ctx.author.mention}", embed=embed)
        
    @commands.command(name='급식.저녁', description='저녁 조회')
    async def dinner(self, ctx):
        embed = discord.Embed(
            title="저녁",
            description="test", 
            color=discord.Color.purple()
        )
        await ctx.message.delete()
        await ctx.send(f"{ctx.author.mention}", embed=embed)
        

