import discord
from discord.ext import commands
import requests
import urllib.request
from shared.riot_api_key import RIOT_API_KEY
import aiohttp
import asyncio
from typing import Dict, List

class RequestLol:
    def __init__(self):
        self.api_key = RIOT_API_KEY
        self.base_url = "https://kr.api.riotgames.com"
        self.headers = {
            "X-Riot-Token": self.api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://developer.riotgames.com"
        }
        
    @staticmethod
    def download_rank_images():
        rank_urls = {
            "UNRANKED": "https://static.wikia.nocookie.net/leagueoflegends/images/1/13/Season_2023_-_Unranked.png/revision/latest?cb=20231007211937",
            "IRON": "https://static.wikia.nocookie.net/leagueoflegends/images/f/f8/Season_2023_-_Iron.png/revision/latest?cb=20231007195831",
            "BRONZE": "https://static.wikia.nocookie.net/leagueoflegends/images/c/cb/Season_2023_-_Bronze.png/revision/latest?cb=20231007195824",
            "SILVER": "https://static.wikia.nocookie.net/leagueoflegends/images/c/c4/Season_2023_-_Silver.png/revision/latest?cb=20231007195834",
            "GOLD": "https://static.wikia.nocookie.net/leagueoflegends/images/7/78/Season_2023_-_Gold.png/revision/latest?cb=20231007195829",
            "PLATINUM": "https://static.wikia.nocookie.net/leagueoflegends/images/b/bd/Season_2023_-_Platinum.png/revision/latest?cb=20231007195833",
            "EMERALD": "https://static.wikia.nocookie.net/leagueoflegends/images/4/4b/Season_2023_-_Emerald.png/revision/latest?cb=20231007195827",
            "DIAMOND": "https://static.wikia.nocookie.net/leagueoflegends/images/3/37/Season_2023_-_Diamond.png/revision/latest?cb=20231007195826",
            "MASTER": "https://static.wikia.nocookie.net/leagueoflegends/images/d/d5/Season_2023_-_Master.png/revision/latest?cb=20231007195832",
            "GRANDMASTER": "https://static.wikia.nocookie.net/leagueoflegends/images/6/64/Season_2023_-_Grandmaster.png/revision/latest?cb=20231007195830",
            "CHALLENGER": "https://static.wikia.nocookie.net/leagueoflegends/images/1/14/Season_2023_-_Challenger.png/revision/latest?cb=20231007195825"
        }
        
        for rank, url in rank_urls.items():
            urllib.request.urlretrieve(url, f"assets/rank/{rank}.png")
            
    @staticmethod
    def get_champion_data():
        ddragon_version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        version_response = requests.get(ddragon_version_url)
        latest_version = version_response.json()[0]
        
        champions_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ko_KR/champion.json"
        champions_response = requests.get(champions_url)
        return champions_response.json()
        
    @staticmethod
    def get_champion_name_kr(champions_data: dict, champion_id: str) -> str:
        return next((champ_info['name']
                    for champ_name, champ_info in champions_data['data'].items()
                    if champ_name == champion_id), champion_id)

class LolEmbed:
    @staticmethod
    def create_tier_embed(game_name: str, tag_line: str, tier_info: dict, tier: str) -> discord.Embed:
        if not tier_info:
            description = "솔로랭크 정보가 없습니다."
        else:
            wins = tier_info['wins']
            losses = tier_info['losses']
            win_rate = round((wins / (wins + losses)) * 100, 1)
            description = f"## {tier_info['tier']} {tier_info['rank']} {tier_info['leaguePoints']}LP\n {wins+losses}전 {wins}승 {losses}패 (승률 {win_rate}%)"
            
        embed = discord.Embed(
            title=f"🇱 이번 시즌 {game_name}#{tag_line}의 티어",
            description=description,
            color=discord.Color.dark_blue()
        )
        
        embed.set_thumbnail(url=f"attachment://{tier}.png")
        return embed
        
    @staticmethod
    def create_history_embed(game_name: str, tag_line: str, matches: List[dict]) -> discord.Embed:
        embed = discord.Embed(
            title=f"🇱 {game_name}#{tag_line}의 최근 5게임",
            color=discord.Color.blue()
        )
        
        for match in matches:
            name = match['name']
            value = match['value']
            embed.add_field(name=name, value=value, inline=False)
            
        return embed
        
    @staticmethod
    def create_rotation_embed(champion_names: List[str]) -> discord.Embed:
        return discord.Embed(
            title="🇱 이번 주 로테이션",
            description=", ".join(champion_names),
            color=discord.Color.blue()
        )
        
    @staticmethod
    def create_error_embed(error_message: str, additional_info: str = None) -> discord.Embed:
        description = str(error_message)
        if additional_info:
            description += " " + str(additional_info)
            
        return discord.Embed(
            title="❗ 오류",
            description=description,
            color=discord.Color.red()
        )

class LolService:
    def __init__(self):
        self.request = RequestLol()
        self.champions_data = self.request.get_champion_data()
        self.game_mode_kr = {
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
        
    async def get_account_info(self, session: aiohttp.ClientSession, riot_id: str) -> Dict:
        if '#' not in riot_id:
            raise ValueError("닉넴#태그 형식으로 입력하세요")
            
        game_name, tag_line = riot_id.split('#')
        account_url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        
        async with session.get(account_url, headers=self.request.headers) as response:
            if response.status != 200:
                raise ValueError(response.status)
            return await response.json()
            
    async def get_tier_info(self, session: aiohttp.ClientSession, puuid: str) -> tuple[Dict, str]:
        summoner_url = f"{self.request.base_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        async with session.get(summoner_url, headers=self.request.headers) as response:
            if response.status != 200:
                raise ValueError(response.status)
            summoner_data = await response.json()

        ranked_url = f"{self.request.base_url}/lol/league/v4/entries/by-summoner/{summoner_data['id']}"
        async with session.get(ranked_url, headers=self.request.headers) as response:
            if response.status != 200:
                raise ValueError(response.status)
            ranked_data = await response.json()
            
        tier = "UNRANKED"
        if ranked_data:
            solo_rank = next((queue for queue in ranked_data if queue['queueType'] == 'RANKED_SOLO_5x5'), None)
            if solo_rank:
                tier = solo_rank['tier']
                return solo_rank, tier
                
        return None, tier
        
    async def get_match_history(self, session: aiohttp.ClientSession, puuid: str) -> List[Dict]:
        matches_url = f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"
        async with session.get(matches_url, headers=self.request.headers) as response:
            if response.status != 200:
                raise ValueError(response.status)
            match_ids = await response.json()

        if not match_ids:
            raise ValueError("최근 게임 기록이 없습니다.")
            
        async def fetch_match(match_id):
            match_url = f"https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}"
            async with session.get(match_url, headers=self.request.headers) as response:
                if response.status == 200:
                    return await response.json()
                return None
                
        match_data_tasks = [fetch_match(match_id) for match_id in match_ids]
        match_data_list = await asyncio.gather(*match_data_tasks)
        match_data_list = [data for data in match_data_list if data is not None]
        
        formatted_matches = []
        for match_data in match_data_list:
            participant = next(p for p in match_data['info']['participants'] if p['puuid'] == puuid)
            
            champion_id = participant['championName']
            champion_name = self.request.get_champion_name_kr(self.champions_data, champion_id)
            
            kills = participant['kills']
            deaths = participant['deaths']
            assists = participant['assists']
            kda = "Perfect" if deaths == 0 else round((kills + assists) / deaths, 2)
            win = participant['win']
            
            minutes = match_data['info']['gameDuration'] // 60
            seconds = match_data['info']['gameDuration'] % 60
            
            game_mode = match_data['info']['gameMode']
            kr_mode = self.game_mode_kr.get(game_mode, game_mode)
            
            formatted_matches.append({
                'name': f"[{"승리" if win else "패배"}] - {champion_name}, {kr_mode}",
                'value': f"- **{kills}/{deaths}/{assists}** ({kda})\n- {minutes}분 {seconds}초"
            })
            
        return formatted_matches
        
    async def get_rotation(self, session: aiohttp.ClientSession) -> List[str]:
        rotation_url = f"{self.request.base_url}/lol/platform/v3/champion-rotations"
        async with session.get(rotation_url, headers=self.request.headers) as response:
            if response.status != 200:
                raise ValueError(response.status)
            rotation_data = await response.json()
            
        champion_names = []
        for champ_id in rotation_data['freeChampionIds']:
            for champ_name, champ_info in self.champions_data['data'].items():
                if int(champ_info['key']) == champ_id:
                    champion_names.append(champ_info['name'])
                    break
                    
        return champion_names

class Lol(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.lol_service = LolService()
        RequestLol.download_rank_images()
        
    async def cog_load(self):
        self.session = aiohttp.ClientSession()
        
    async def cog_unload(self):
        if self.session:
            await self.session.close()
            
    @commands.command(name="롤.티어", aliases=['롤.랭크'], description="이번 시즌 티어")
    async def lol_tier(self, ctx, *, riot_id: str):
        try:
            account_data = await self.lol_service.get_account_info(self.session, riot_id)
            tier_info, tier = await self.lol_service.get_tier_info(self.session, account_data['puuid'])
            
            embed = LolEmbed.create_tier_embed(
                account_data['gameName'],
                account_data['tagLine'],
                tier_info,
                tier
            )
            
            rank_image = discord.File(f"assets/rank/{tier}.png", filename=f"{tier}.png")
            await ctx.reply(embed=embed, file=rank_image)
            
        except Exception as e:
            await ctx.reply(embed=LolEmbed.create_error_embed(str(e)))
            
    @commands.command(name="롤.전적", description="최근 5게임 전적 조회")
    async def lol_history(self, ctx, *, riot_id: str):
        try:
            account_data = await self.lol_service.get_account_info(self.session, riot_id)
            matches = await self.lol_service.get_match_history(self.session, account_data['puuid'])
            
            embed = LolEmbed.create_history_embed(
                account_data['gameName'],
                account_data['tagLine'],
                matches
            )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            await ctx.reply(embed=LolEmbed.create_error_embed(str(e)))
            
    @commands.command(name="롤.로테이션", description="현재 무료 로테이션 챔피언 목록을 보여줍니다")
    async def lol_rotation(self, ctx):
        try:
            champion_names = await self.lol_service.get_rotation(self.session)
            embed = LolEmbed.create_rotation_embed(champion_names)
            await ctx.reply(embed=embed)
            
        except Exception as e:
            await ctx.reply(embed=LolEmbed.create_error_embed(str(e)))
