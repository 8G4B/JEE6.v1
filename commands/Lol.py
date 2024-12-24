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

    def _create_error_embed(self, error_message):
        embed = discord.Embed(
            title="❗ 오류",
            description=str(error_message),
            color=discord.Color.red()
        )
        return embed

    @commands.command(name="롤.전적", aliases=['롤.전적검색'], description="롤 전적조회")
    async def lol_record(self, ctx, *, arg=None):
        if arg is None:
            await ctx.reply("!롤.전적 닉넴#태그")
            return

        try:
            name, tag = arg.split('#')
            
            if not self.api_key:
                await ctx.reply(embed=self._create_error_embed("API 키 없음"))
                return
                
            try:
                summoner = self.watcher.summoner.by_name(self.summoner_region, name)
            except Exception as e:
                if "401" in str(e):
                    await ctx.reply(embed=self._create_error_embed("API 키 이상해"))
                    return
                raise e
                
            puuid = summoner['puuid']
            
            # 최근 5게임 조회
            matches = self.watcher.match.matchlist_by_puuid(self.match_region, puuid, count=5)
            
            embed = discord.Embed(
                title=f"{name}#{tag}님의 최근 전적",
                color=discord.Color.dark_blue()
            )

            for match_id in matches:
                match = self.watcher.match.by_id(self.match_region, match_id)
                
                # 게임 정보
                game_duration = match['info']['gameDuration'] // 60  
                queue_id = match['info']['queueId']
                game_mode = self._get_queue_type(queue_id)  
                
                for participant in match['info']['participants']:
                    if participant['puuid'] == puuid:
                        champion = participant['championName']
                        kills = participant['kills']
                        deaths = participant['deaths']
                        assists = participant['assists']
                        kda = f"{kills}/{deaths}/{assists}"
                        win = "승리" if participant['win'] else "패배"
                        
                        embed.add_field(
                            name=f"{champion} - {win} ({game_mode})",
                            value=f"KDA: {kda} | 게임 시간: {game_duration}분",
                            inline=False
                        )

            await ctx.reply(embed=embed)

        except Exception as e:
            await ctx.reply(embed=self._create_error_embed(str(e)))

    def _get_queue_type(self, queue_id):
        queue_types = {
            400: "일반",
            420: "솔랭",
            430: "일반",
            440: "자유랭크",
            450: "무작위 총력전",
            700: "격전",
            830: "AI 대전",
            840: "AI 대전",
            850: "AI 대전",
            900: "URF",
            1020: "단일챔피언",
            1300: "돌격 넥서스",
            1400: "궁극기 주문서"
        }
        return queue_types.get(queue_id, "기타")
