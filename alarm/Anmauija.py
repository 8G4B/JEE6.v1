import discord
from discord.ext import commands, tasks
from datetime import datetime, time

class Anmauija(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_alarm.start()

    def cog_unload(self):
        self.daily_alarm.cancel()

    @tasks.loop(seconds=1)  
    async def daily_alarm(self):
        if datetime.now().hour == 20 and datetime.now().minute == 19: # 20, 19
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    if 'jee6' in channel.name.lower():
                        try:
                            await channel.send("@here 안마의자 신청 1분 전\n [DOTORI 바로가기](https://www.dotori-gsm.com/home)")
                            time.sleep(60)
                            break
                        except discord.Forbidden:
                            continue

    @daily_alarm.before_loop
    async def before_daily_alarm(self):
        await self.bot.wait_until_ready()
