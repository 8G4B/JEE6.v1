import discord
from discord.ext import commands
import requests
import urllib.request
from shared.riot_api_key import RIOT_API_KEY

class Lol(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = RIOT_API_KEY
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
            raise ValueError("닉넴#태그 형식으로 입력하세요")
            
        game_name, tag_line = riot_id.split('#')
        
        account_url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        account_response = requests.get(account_url, headers=self.headers)

        if account_response.status_code != 200:
            raise ValueError(account_response.status_code)

        account_data = account_response.json()
        return account_data

    def _get_champion_data(self):
        ddragon_version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        version_response = requests.get(ddragon_version_url)
        latest_version = version_response.json()[0]
        
        champions_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ko_KR/champion.json"
        champions_response = requests.get(champions_url)
        return champions_response.json()

    def _get_champion_name_kr(self, champion_id, champions_data):
        return next((champ_info['name'] 
                    for champ_name, champ_info in champions_data['data'].items() 
                    if champ_name == champion_id), champion_id)

    @commands.command(name="롤.티어", aliases=['롤.랭크'], description="이번 시즌 티어")
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
                    
                    description = f"## {tier} {rank} {lp}LP\n {wins+losses}전 {wins}승 {losses}패 (승률 {win_rate}%)"
                else:
                    description = "솔로랭크 정보가 없습니다."

            embed = discord.Embed(
                title=f"🇱 이번 시즌 {original_game_name}#{tag_line}의 티어",
                description=description,
                color=discord.Color.dark_blue()
            )
            
            rank_image = discord.File(f"assets/rank/{tier}.png", filename=f"{tier}.png")
            embed.set_thumbnail(url=f"attachment://{tier}.png")

            await ctx.reply(embed=embed, file=rank_image)

        except Exception as e:
            await ctx.reply(embed=self._create_error_embed(str(e)))
            
    @commands.command(name="롤.전적", description="최근 5게임 전적 조회")
    async def lol_history(self, ctx, *, riot_id: str):
        try:
            account_data = self._get_account_info(riot_id)
            puuid = account_data['puuid']
            original_game_name = account_data['gameName']
            tag_line = account_data['tagLine']

            matches_url = f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"
            matches_response = requests.get(matches_url, headers=self.headers)
            
            if matches_response.status_code != 200:
                raise ValueError(matches_response.status_code)
                
            match_ids = matches_response.json()
            
            if not match_ids:
                raise ValueError("최근 게임 기록이 없습니다.")

            champions_data = self._get_champion_data()

            embed = discord.Embed(
                title=f"🇱 {original_game_name}#{tag_line}의 최근 5게임",
                color=discord.Color.blue()
            )

            game_mode_kr = {
                'CLASSIC': '소환사의 협곡',
                'ARAM': '칼바람 나락',
                'URF': '우르프',
                'ARURF': '무작위 우르프',
                'ONEFORALL': '단일 챔피언',
                'TUTORIAL': '튜토리얼',
                'PRACTICETOOL': '연습',
                'NEXUSBLITZ': '넥서스 돌격',
                'ULTBOOK': '궁극기 주문서'
            }

            for match_id in match_ids:
                match_url = f"https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}"
                match_response = requests.get(match_url, headers=self.headers)
                
                if match_response.status_code != 200:
                    continue
                    
                match_data = match_response.json()
                
                participant = next(p for p in match_data['info']['participants'] if p['puuid'] == puuid)
                
                champion_id = participant['championName']
                champion_name = self._get_champion_name_kr(champion_id, champions_data)
                
                kills = participant['kills']
                deaths = participant['deaths']
                assists = participant['assists']
                kda = "Perfect" if deaths == 0 else round((kills + assists) / deaths, 2)
                win = participant['win']
                
                minutes = match_data['info']['gameDuration'] // 60
                seconds = match_data['info']['gameDuration'] % 60
                
                game_mode = match_data['info']['gameMode']
                kr_mode = game_mode_kr.get(game_mode, game_mode)
                
                embed.add_field(
                    name=f"[{"승리" if win else "패배"}] - {champion_name}, {kr_mode}",
                    value=f"- **{kills}/{deaths}/{assists}** ({kda})\n- {minutes}분 {seconds}초",
                    inline=False
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
            
            champions_data = self._get_champion_data()
            
            # 챔 ID를 이름으로 변환
            champion_names = []
            for champ_id in rotation_data['freeChampionIds']:
                for champ_name, champ_info in champions_data['data'].items():
                    if int(champ_info['key']) == champ_id:
                        champion_names.append(champ_info['name'])
                        break
            
            embed = discord.Embed(
                title="🇱 이번 주 로테이션",
                description=", ".join(champion_names),
                color=discord.Color.blue()
            )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            await ctx.reply(embed=self._create_error_embed(str(e)))
