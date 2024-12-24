import discord
from discord.ext import commands
from riotwatcher import LolWatcher
import riot_api_key

class Lol(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = riot_api_key.RIOT_API_KEY
        self.watcher = LolWatcher(str(self.api_key))
        self.summoner_region = 'kr'  
        self.match_region = 'ASIA'  

    @commands.command(name="롤.전적", aliases=['롤.전적검색'], description="롤 전적조회")
    async def lol_record(self, ctx, *, arg=None):
        if arg is None:
            await ctx.reply("!롤.전적 닉넴#태그")
            return

        try:
            name, tag = arg.split('#')
            
            summoner = self.watcher.summoner.by_name(self.summoner_region, name)
            puuid = summoner['puuid']
            
            # 최근 5게임 조회
            matches = self.watcher.match.matchlist_by_puuid(self.match_region, puuid, count=5)
            
            embed = discord.Embed(
                title=f"{name}#{tag}님의 최근 전적",
                color=discord.Color.dark_blue()
            )

            for match_id in matches:
                match = self.watcher.match.by_id(self.match_region, match_id)
                
                for participant in match['info']['participants']:
                    if participant['puuid'] == puuid:
                        champion = participant['championName']
                        kills = participant['kills']
                        deaths = participant['deaths']
                        assists = participant['assists']
                        kda = f"{kills}/{deaths}/{assists}"
                        win = "승리" if participant['win'] else "패배"
                        
                        embed.add_field(
                            name=f"{champion} - {win}",
                            value=f"KDA: {kda}",
                            inline=False
                        )

            await ctx.reply(embed=embed)

        except Exception as e:
            await ctx.reply(self._create_error_embed(str(e)))
