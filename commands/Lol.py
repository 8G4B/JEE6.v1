import discord
from discord.ext import commands
import requests
import urllib.request

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
        
        urllib.request.urlretrieve("https://static.wikia.nocookie.net/leagueoflegends/images/1/13/Season_2023_-_Unranked.png/revision/latest?cb=20231007211937", "assets/rank/UNRANKED.png")
        urllib.request.urlretrieve("https://static.wikia.nocookie.net/leagueoflegends/images/f/f8/Season_2023_-_Iron.png/revision/latest?cb=20231007195831", "assets/rank/IRON.png")
        urllib.request.urlretrieve("https://static.wikia.nocookie.net/leagueoflegends/images/c/cb/Season_2023_-_Bronze.png/revision/latest?cb=20231007195824", "assets/rank/BRONZE.png")
        urllib.request.urlretrieve("https://static.wikia.nocookie.net/leagueoflegends/images/c/c4/Season_2023_-_Silver.png/revision/latest?cb=20231007195834", "assets/rank/SILVER.png")
        urllib.request.urlretrieve("https://static.wikia.nocookie.net/leagueoflegends/images/7/78/Season_2023_-_Gold.png/revision/latest?cb=20231007195829", "assets/rank/GOLD.png")
        urllib.request.urlretrieve("https://static.wikia.nocookie.net/leagueoflegends/images/b/bd/Season_2023_-_Platinum.png/revision/latest?cb=20231007195833", "assets/rank/PLATINUM.png")
        urllib.request.urlretrieve("https://static.wikia.nocookie.net/leagueoflegends/images/4/4b/Season_2023_-_Emerald.png/revision/latest?cb=20231007195827", "assets/rank/EMERALD.png")
        urllib.request.urlretrieve("https://static.wikia.nocookie.net/leagueoflegends/images/3/37/Season_2023_-_Diamond.png/revision/latest?cb=20231007195826", "assets/rank/DIAMOND.png")
        urllib.request.urlretrieve("https://static.wikia.nocookie.net/leagueoflegends/images/d/d5/Season_2023_-_Master.png/revision/latest?cb=20231007195832", "assets/rank/MASTER.png")
        urllib.request.urlretrieve("https://static.wikia.nocookie.net/leagueoflegends/images/6/64/Season_2023_-_Grandmaster.png/revision/latest?cb=20231007195830", "assets/rank/GRANDMASTER.png")
        urllib.request.urlretrieve("https://static.wikia.nocookie.net/leagueoflegends/images/1/14/Season_2023_-_Challenger.png/revision/latest?cb=20231007195825", "assets/rank/CHALLENGER.png")
        
        self.rank_images = {
            "UNRANKED": discord.File("assets/rank/UNRANKED.png", filename="UNRANKED.png"),
            "IRON": discord.File("assets/rank/IRON.png", filename="IRON.png"),
            "BRONZE": discord.File("assets/rank/BRONZE.png", filename="BRONZE.png"), 
            "SILVER": discord.File("assets/rank/SILVER.png", filename="SILVER.png"),
            "GOLD": discord.File("assets/rank/GOLD.png", filename="GOLD.png"),
            "PLATINUM": discord.File("assets/rank/PLATINUM.png", filename="PLATINUM.png"),
            "EMERALD": discord.File("assets/rank/EMERALD.png", filename="EMERALD.png"),
            "DIAMOND": discord.File("assets/rank/DIAMOND.png", filename="DIAMOND.png"),
            "MASTER": discord.File("assets/rank/MASTER.png", filename="MASTER.png"),
            "GRANDMASTER": discord.File("assets/rank/GRANDMASTER.png", filename="GRANDMASTER.png"),
            "CHALLENGER": discord.File("assets/rank/CHALLENGER.png", filename="CHALLENGER.png")
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

        account_data = account_response.json()
        return account_data

    @commands.command(name="롤.티어", description="이번 시즌 통계")
    async def lol_history(self, ctx, *, riot_id: str):
        try:
            account_data = self._get_account_info(riot_id)
            
            puuid = account_data['puuid']
            original_game_name = account_data['gameName'] 
            tag_line = account_data['tagLine']

            summoner_url = f"{self.base_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"
            summoner_response = requests.get(summoner_url, headers=self.headers)

            if summoner_response.status_code != 200:
                raise ValueError(summoner_response.status_code)

            summoner_data = summoner_response.json()
            summoner_id = summoner_data['id']  # summonerId

            ranked_url = f"{self.base_url}/lol/league/v4/entries/by-summoner/{summoner_id}"
            ranked_response = requests.get(ranked_url, headers=self.headers)

            if ranked_response.status_code != 200:
                raise ValueError(ranked_response.status_code)

            ranked_data = ranked_response.json()
            
            tier = "UNRANKED"
            if not ranked_data:
                description = "랭크 정보가 없습니다."
            else:
                solo_rank = next((queue for queue in ranked_data if queue['queueType'] == 'RANKED_SOLO_5x5'), None)
                
                if solo_rank:
                    tier = solo_rank['tier']
                    rank = solo_rank['rank'] 
                    lp = solo_rank['leaguePoints']
                    wins = solo_rank['wins']
                    losses = solo_rank['losses']
                    win_rate = round((wins / (wins + losses)) * 100, 1)
                    
                    description = f"티어: {tier} {rank} {lp}LP\n{wins+losses}전 {wins}승 {losses}패 (승률 {win_rate}%)"
                else:
                    description = "솔로랭크 정보가 없습니다."

            embed = discord.Embed(
                title=f"{original_game_name}#{tag_line}의 전적",
                description=description,
                color=discord.Color.dark_blue()
            )
            
            rank_image = discord.File(f"assets/rank/{tier}.png", filename=f"{tier}.png")
            embed.set_thumbnail(url=f"attachment://{tier}.png")

            await ctx.reply(embed=embed, file=rank_image)

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
