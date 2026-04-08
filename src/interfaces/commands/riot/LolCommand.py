import discord
from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.LolEmbed import LolEmbed
from src.clients.ApiGatewayClient import ApiGatewayClient

logger = logging.getLogger(__name__)


class LolCommands(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.api = ApiGatewayClient()

    @commands.command(
        name="롤.티어",
        aliases=["롤.랭크", "lol.tier", "ㄹ.ㅌㅇ"],
        description="이번 시즌 티어를 보여줍니다. (!롤.티어 닉네임#태그)",
    )
    async def lol_tier(self, ctx, *, riot_id: str):
        logger.info(f"lol_tier({ctx.guild.name}, {ctx.author.name}, {riot_id})")
        try:
            data = await self.api.get_lol_tier(riot_id)

            if data.get("error"):
                await ctx.reply(embed=LolEmbed.create_error_embed(data["error"]))
                return

            solo_rank = data.get("solo_rank")
            tier = data.get("tier", "UNRANKED")

            if not solo_rank:
                description = "솔로랭크 정보가 없습니다."
            else:
                wins = solo_rank["wins"]
                losses = solo_rank["losses"]
                win_rate = round((wins / (wins + losses)) * 100, 1)
                description = f"## {solo_rank['tier']} {solo_rank['rank']} {solo_rank['leaguePoints']}LP\n {wins+losses}전 {wins}승 {losses}패 (승률 {win_rate}%)"

            title = f"🇱 이번 시즌 {riot_id}의 티어"
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
            data = await self.api.get_lol_history(riot_id)

            if data.get("error"):
                await ctx.reply(embed=LolEmbed.create_error_embed(data["error"]))
                return

            title = f"🇱 {riot_id}의 최근 5게임"
            embed = LolEmbed.create_history_embed(title, data.get("matches", []))
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
            data = await self.api.get_lol_rotation()

            if data.get("error"):
                await ctx.reply(embed=LolEmbed.create_error_embed(data["error"]))
                return

            champions = data.get("champions", [])
            champion_names = [champ["kr_name"] for champ in champions]

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
