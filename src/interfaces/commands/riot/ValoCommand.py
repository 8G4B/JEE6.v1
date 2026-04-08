from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.ValoEmbed import ValoEmbed
from src.clients.ApiGatewayClient import ApiGatewayClient

logger = logging.getLogger(__name__)


class ValoCommands(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.api = ApiGatewayClient()

    @commands.command(
        name="발로.티어",
        aliases=["발로.랭크", "valo.tier", "valo.rank", "ㅂㄹ.ㅌㅇ"],
        description="현재 시즌 티어를 보여줍니다. (!발로.티어 닉네임#태그)",
    )
    async def valo_tier(self, ctx, *, riot_id: str):
        logger.info(f"valo_tier({ctx.guild.name}, {ctx.author.name}, {riot_id})")
        try:
            data = await self.api.get_valo_tier(riot_id)

            if data.get("error"):
                await ctx.reply(embed=ValoEmbed.create_error_embed(data["error"]))
                return

            rank_data = data.get("rank_data")
            tier = data.get("tier", "UNRANKED")
            account = data.get("account", {})
            display_name = f"{account.get('gameName', '')}#{account.get('tagLine', '')}" if account else riot_id

            if not rank_data:
                description = "랭크 정보가 없습니다."
            else:
                rating = rank_data.get("rankedRating", 0)
                description = f"## {tier} - {rating}RP"

            title = f"🇻 {display_name}의 티어"
            embed = ValoEmbed.create_tier_embed(title, description, tier)
            await ctx.reply(embed=embed)
        except ValueError as e:
            await ctx.reply(embed=ValoEmbed.create_error_embed(str(e)))
        except Exception as e:
            logger.error(f"발로란트 티어 명령어 처리 중 오류: {e}")
            await ctx.reply(
                embed=ValoEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )

    @commands.command(
        name="발로.전적",
        aliases=["발로.기록", "valo.history", "ㅂㄹ.ㅈㅈ"],
        description="최근 5게임 전적을 조회합니다. (!발로.전적 닉네임#태그)",
    )
    async def valo_history(self, ctx, *, riot_id: str):
        logger.info(f"valo_history({ctx.guild.name}, {ctx.author.name}, {riot_id})")
        try:
            data = await self.api.get_valo_history(riot_id)

            if data.get("error"):
                await ctx.reply(embed=ValoEmbed.create_error_embed(data["error"]))
                return

            account = data.get("account", {})
            display_name = f"{account.get('gameName', '')}#{account.get('tagLine', '')}" if account else riot_id

            title = f"🇻 {display_name}의 최근 5게임"
            embed = ValoEmbed.create_history_embed(title, data.get("matches", []))
            await ctx.reply(embed=embed)
        except ValueError as e:
            await ctx.reply(embed=ValoEmbed.create_error_embed(str(e)))
        except Exception as e:
            logger.error(f"발로란트 전적 명령어 처리 중 오류: {e}")
            await ctx.reply(
                embed=ValoEmbed.create_error_embed(f"오류가 발생했습니다: {e}")
            )
