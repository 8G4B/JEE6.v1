import discord
from discord.ext import commands
import urllib.request
from shared.riot_api_key import RIOT_API_KEY
import aiohttp
from typing import Dict, List
import time
import os


class RequestValo:
    def __init__(self):
        self.api_key = RIOT_API_KEY
        self.base_url = "https://asia.api.riotgames.com"
        self.val_url = "https://ap.api.riotgames.com"
        self.headers = {
            "X-Riot-Token": self.api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        self.download_rank_images()

    @staticmethod
    def download_rank_images():
        pass

    #  try:
    #      os.makedirs('assets/valo_rank', exist_ok=True)

    #     for rank, url in rank_urls.items():
    #         try:
    #             response = urllib.request.urlopen(url)
    #                if response.status == 200:
    #                        with open(f"assets/valo_rank/{rank}.png", 'wb') as f:
    #                            f.write(response.read())
    #                    else:
    #                        print(f"Failed to download {rank} image: HTTP {response.status}")
    #                except Exception as e:
    #                    print(f"Error downloading {rank} image: {str(e)}")
    #                    continue
    #        except Exception as e:
    #            print(f"Error in download_rank_images: {str(e)}")


class ValoEmbed:
    @staticmethod
    def create_tier_embed(title: str, description: str, tier: str) -> discord.Embed:
        embed = discord.Embed(
            title=title, description=description, color=discord.Color.red()
        )
        # embed.set_thumbnail(url=f"attachment://{tier}.png")
        return embed

    @staticmethod
    def create_history_embed(title: str, matches: List[dict]) -> discord.Embed:
        embed = discord.Embed(title=title, color=discord.Color.red())

        for match in matches:
            embed.add_field(name=match["name"], value=match["value"], inline=False)

        return embed

    @staticmethod
    def create_error_embed(description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류", description=description, color=discord.Color.red()
        )


class ValoService:
    def __init__(self):
        self.request = RequestValo()
        self.account_cache = {}
        self.match_cache = {}
        self.cache_timeout = 600

    async def get_account_info(
        self, session: aiohttp.ClientSession, riot_id: str
    ) -> Dict:
        if "#" not in riot_id:
            raise ValueError("닉넴#태그 형식으로 입력하세요")

        game_name, tag_line = riot_id.split("#")
        account_url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"

        async with session.get(account_url, headers=self.request.headers) as response:
            if response.status != 200:
                raise ValueError("계정을 찾을 수 없습니다")
            account_data = await response.json()
            self.account_cache[riot_id] = (time.time(), account_data)
            return account_data

    async def get_match_history(
        self, session: aiohttp.ClientSession, puuid: str
    ) -> List[Dict]:
        matches_url = f"{self.request.val_url}/val/match/v1/matchlists/by-puuid/{puuid}"

        async with session.get(matches_url, headers=self.request.headers) as response:
            if response.status != 200:
                raise ValueError(response.status)
            matches_data = await response.json()

        formatted_matches = []
        for match in matches_data["history"][:5]:  # 최근 5게임만
            match_detail_url = (
                f"{self.request.val_url}/val/match/v1/matches/{match['matchId']}"
            )
            async with session.get(
                match_detail_url, headers=self.request.headers
            ) as response:
                if response.status == 200:
                    match_data = await response.json()
                    player = next(
                        p for p in match_data["players"] if p["puuid"] == puuid
                    )

                    kills = player["stats"]["kills"]
                    deaths = player["stats"]["deaths"]
                    assists = player["stats"]["assists"]
                    kda = (
                        "Perfect"
                        if deaths == 0
                        else round((kills + assists) / deaths, 2)
                    )

                    formatted_matches.append(
                        {
                            "name": f"[{'승리' if player['team'] == match_data['teams'][0]['teamId'] else '패배'}] - {player['character']}, {match_data['metadata']['map']}",
                            "value": f"- **{kills}/{deaths}/{assists}** (KDA: {kda})\n- 점수: {player['stats']['score']}",
                        }
                    )

        return formatted_matches

    async def get_rank_info(
        self, session: aiohttp.ClientSession, puuid: str
    ) -> tuple[Dict, str]:
        rank_url = f"{self.request.val_url}/val/ranked/v1/by-puuid/{puuid}"

        async with session.get(rank_url, headers=self.request.headers) as response:
            if response.status != 200:
                return None, "UNRANKED"

            rank_data = await response.json()
            if not rank_data or not rank_data.get("currenttier"):
                return None, "UNRANKED"

            tier = rank_data["currenttierpatched"]
            return rank_data, tier


class Valo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.valo_service = ValoService()
        # RequestValo.download_rank_images()

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    @commands.command(
        name="발로.티어", aliases=["발로.랭크"], description="현재 시즌 티어"
    )
    async def valo_tier(self, ctx, *, riot_id: str):
        try:
            account_data = await self.valo_service.get_account_info(
                self.session, riot_id
            )
            rank_info, tier = await self.valo_service.get_rank_info(
                self.session, account_data["puuid"]
            )

            if not rank_info:
                description = "랭크 정보가 없습니다."
            else:
                rating = rank_info.get("rankedRating", 0)
                description = f"## {tier} - {rating}RP"

            title = f"🇻 {account_data['gameName']}#{account_data['tagLine']}의 티어"
            embed = ValoEmbed.create_tier_embed(title, description, tier)

            # rank_image = discord.File(f"assets/valo_rank/{tier}.png", filename=f"{tier}.png")
            # await ctx.reply(embed=embed, file=rank_image)
            await ctx.reply(embed=embed)

        except Exception as e:
            await ctx.reply(embed=ValoEmbed.create_error_embed(str(e)))

    @commands.command(name="발로.전적", description="최근 5게임 전적 조회")
    async def valo_history(self, ctx, *, riot_id: str):
        try:
            account_data = await self.valo_service.get_account_info(
                self.session, riot_id
            )
            matches = await self.valo_service.get_match_history(
                self.session, account_data["puuid"]
            )

            title = (
                f"🇻 {account_data['gameName']}#{account_data['tagLine']}의 최근 5게임"
            )
            embed = ValoEmbed.create_history_embed(title, matches)

            await ctx.reply(embed=embed)

        except Exception as e:
            await ctx.reply(embed=ValoEmbed.create_error_embed(str(e)))
