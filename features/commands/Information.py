import discord
from discord.ext import commands
import urllib.request
class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        urllib.request.urlretrieve("https://github.com/user-attachments/assets/d6b5f0cd-9363-40ad-a356-c1449664750b", "assets/profile/JEE6.png")
        self.profile_image = discord.File("assets/profile/JEE6.png", filename="JEE6.png")

    @commands.command(name="정보", aliases=['도움'], description="정보")
    async def information(self, ctx):
        latency = round(self.bot.latency * 1000) 
        embed = discord.Embed(
            title="💬 JEE6",
            description = f"- [명령어 + 도박 관련](https://github.com/8G4B/JEE6.v1/blob/master/README.md#%EB%AA%85%EB%A0%B9%EC%96%B4-%EC%9D%BC%EB%9E%8C)\n- [실행 방법](https://github.com/8G4B/JEE6.v1/blob/master/README.md#%EB%A1%9C%EC%BB%AC%EC%97%90%EC%84%9C-%EC%8B%A4%ED%96%89)\n- [소스코드](https://github.com/8G4B/JEE6.v1)\n\n- [만든놈](https://github.com/976520) \n- [만든놈한테 쌕쌕 사주기](https://aq.gy/f/9LOJx)\n\n- 핑: {latency}ms",
            color=discord.Color.yellow()
        )
        embed.set_thumbnail(url="attachment://JEE6.png")
        await ctx.reply(embed=embed, file=self.profile_image)