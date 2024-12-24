import discord
from discord.ext import commands
import requests
import os

class Lol(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = 'RGAPI-45f6885e-9973-4365-b991-8d5129816dd8'
        self.base_url = "https://kr.api.riotgames.com"
        self.headers = {
            "X-Riot-Token": self.api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7", 
            "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://developer.riotgames.com"
        }

    def _create_error_embed(self, error_message, additional_info=None):
        description = str(error_message)
        if additional_info:
            description += " " + str(additional_info)
            
        embed = discord.Embed(
            title="❗ 오류",
            description=description,
            color=discord.Color.red()
        )
        return embed
      
    def _get_account_info(self, riot_id: str):
        if '#' not in riot_id:
            raise ValueError("!롤.전적 닉네임#태그")
            
        game_name, tag_line = riot_id.split('#')
        
        account_url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        account_response = requests.get(account_url, headers=self.headers)

        if account_response.status_code != 200:
            raise ValueError(account_response.status_code)

        return account_response.json()

    @commands.command(name="롤.전적", description="소환사 이름을 입력하여 전적을 조회합니다")
    async def lol_history(self, ctx, *, riot_id: str):
        try:
            account_data = self._get_account_info(riot_id)
            puuid = account_data['puuid']
            original_game_name = account_data['gameName'] 
            tag_line = account_data['tagLine']

            embed = discord.Embed(
                title=f"{original_game_name}#{tag_line}의 정보",
                description=f"{original_game_name}#{tag_line}의 PUUID: {puuid}",
                color=discord.Color.dark_blue()
            )

            await ctx.reply(embed=embed)

        except Exception as e:
            await ctx.reply(embed=self._create_error_embed(str(e)))

    @commands.command(name="롤.로테이션", description="현재 무료 로테이션 챔피언 목록을 보여줍니다")
    async def lol_rotation(self, ctx):
        try:
            rotation_url = f"{self.base_url}/lol/platform/v3/champion-rotations"
            rotation_response = requests.get(rotation_url, headers=self.headers)
            
            if rotation_response.status_code != 200:
                await ctx.reply(embed=self._create_error_embed(rotation_response.status_code))
                return
                
            rotation_data = rotation_response.json()
            
            ddragon_version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
            version_response = requests.get(ddragon_version_url)
            latest_version = version_response.json()[0]
            
            champions_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ko_KR/champion.json"
            champions_response = requests.get(champions_url)
            champions_data = champions_response.json()
            
            # 챔 ID를 이름으로 변환
            champion_names = []
            for champ_id in rotation_data['freeChampionIds']:
                for champ_name, champ_info in champions_data['data'].items():
                    if int(champ_info['key']) == champ_id:
                        champion_names.append(champ_info['name'])
                        break
            
            embed = discord.Embed(
                title="이번 주 로테이션",
                description=", ".join(champion_names),
                color=discord.Color.blue()
            )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            await ctx.reply(embed=self._create_error_embed(str(e)))
