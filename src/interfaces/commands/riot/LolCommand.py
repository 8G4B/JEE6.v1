import discord
from discord.ext import commands
import logging
import aiohttp
from src.interfaces.commands.Basee import BaseCommand
from src.utils.embeds.LolEmbed import LolEmbed
from src.services.LolService import LolService

logger = logging.getLogger(__name__)


class LolCommands(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.lol_service = LolService()
        self.session = None
        self._setup_session()

    def _setup_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session:
            await self.session.close()
            self.session = None

    @commands.command(
        name="롤.티어",
        aliases=["롤.랭크", "lol.tier", "ㄹ.ㅌㅇ"],
        description="이번 시즌 티어를 보여줍니다. (!롤.티어 닉네임#태그)",
    )
    async def lol_tier(self, ctx, *, riot_id: str):
        logger.info(f"lol_tier({ctx.guild.name}, {ctx.author.name}, {riot_id})")
        try:
            self._setup_session()
            account_data = await self.lol_service.get_account_info(
                self.session, riot_id
            )
            tier_info, tier = await self.lol_service.get_tier_info(
                self.session, account_data["puuid"]
            )
            if not tier_info:
                description = "솔로랭크 정보가 없습니다."
            else:
                wins = tier_info["wins"]
                losses = tier_info["losses"]
                win_rate = round((wins / (wins + losses)) * 100, 1)
                description = f"## {tier_info['tier']} {tier_info['rank']} {tier_info['leaguePoints']}LP\n {wins+losses}전 {wins}승 {losses}패 (승률 {win_rate}%)"

            title = f"🇱 이번 시즌 {account_data['gameName']}#{account_data['tagLine']}의 티어"
            embed = LolEmbed.create_tier_embed(title, description, tier)
            try:
                rank_image_path = f"assets/rank/{tier}.png"
                rank_image = discord.File(rank_image_path, filename=f"{tier}.png")
                await ctx.reply(embed=embed, file=rank_image)
            except FileNotFoundError:
                logger.warning(f"티어 이미지 파일을 찾을 수 없음: {tier}.png")
                await ctx.reply(embed=embed)
        except ValueError as e:
            await ctx.reply(embed=LolEmbed.create_error_embed(str(e)))
        except Exception as e:
            logger.error(f"롤 티어 명령어 처리 중 오류: {e}")
            await ctx.reply(
                embed=LolEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )

    @commands.command(
        name="롤.전적",
        aliases=["롤.기록", "lol.history", "ㄹ.ㅈㅈ"],
        description="최근 5게임 전적을 조회합니다. (!롤.전적 닉네임#태그)",
    )
    async def lol_history(self, ctx, *, riot_id: str):
        logger.info(f"lol_history({ctx.guild.name}, {ctx.author.name}, {riot_id})")

        try:
            self._setup_session()

            account_data = await self.lol_service.get_account_info(
                self.session, riot_id
            )

            matches = await self.lol_service.get_match_history(
                self.session, account_data["puuid"]
            )

            title = (
                f"🇱 {account_data['gameName']}#{account_data['tagLine']}의 최근 5게임"
            )
            embed = LolEmbed.create_history_embed(title, matches)

            await ctx.reply(embed=embed)

        except ValueError as e:
            await ctx.reply(embed=LolEmbed.create_error_embed(str(e)))
        except Exception as e:
            logger.error(f"롤 전적 명령어 처리 중 오류: {e}")
            await ctx.reply(
                embed=LolEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )

    @commands.command(
        name="롤.로테이션",
        aliases=["롤.로테", "lol.rotation", "ㄹ.ㄹㅌ"],
        description="현재 무료 로테이션 챔피언 목록을 보여줍니다.",
    )
    async def lol_rotation(self, ctx):
        logger.info(f"lol_rotation({ctx.guild.name}, {ctx.author.name})")

        try:
            self._setup_session()

            champion_info = await self.lol_service.get_rotation(self.session)

            champion_names = [champ["kr_name"] for champ in champion_info]

            title = "🇱 이번 주 로테이션"
            embed = LolEmbed.create_rotation_embed(title, champion_names)

            await ctx.reply(embed=embed)

        except ValueError as e:
            await ctx.reply(embed=LolEmbed.create_error_embed(str(e)))
        except Exception as e:
            logger.error(f"롤 로테이션 명령어 처리 중 오류: {e}")
            await ctx.reply(
                embed=LolEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )
