import discord
from discord.ext import commands
import logging
import aiohttp
from src.interfaces.commands.base_command import BaseCommand
from src.utils.embeds.valo_embed import ValoEmbed
from src.services.valo_service import ValoService

logger = logging.getLogger(__name__)

class ValoCommands(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.valo_service = ValoService()
        self.session = None
        self._setup_session()
    
    def _setup_session(self):
        """비동기 세션 설정"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        """명령어 해제 시 세션 정리"""
        if self.session:
            await self.session.close()
            self.session = None
    
    @commands.command(
        name='발로.티어',
        aliases=['발로.랭크', 'valo.tier', 'valo.rank', 'ㅂㄹ.ㅌㅇ'],
        description="현재 시즌 티어를 보여줍니다. (!발로.티어 닉네임#태그)"
    )
    async def valo_tier(self, ctx, *, riot_id: str):
        """발로란트 티어 정보 명령어"""
        logger.info(f"valo_tier({ctx.guild.name}, {ctx.author.name}, {riot_id})")
        
        try:
            self._setup_session()
            
            # 계정 정보 가져오기
            account_data = await self.valo_service.get_account_info(self.session, riot_id)
            
            # 티어 정보 가져오기
            rank_info, tier = await self.valo_service.get_rank_info(self.session, account_data['puuid'])
            
            # 티어 정보 표시
            if not rank_info:
                description = "랭크 정보가 없습니다."
            else:
                rating = rank_info.get('rankedRating', 0)
                description = f"## {tier} - {rating}RP"

            title = f"🇻 {account_data['gameName']}#{account_data['tagLine']}의 티어"
            embed = ValoEmbed.create_tier_embed(title, description, tier)
            
            # 티어 이미지가 있는 경우 추가
            # try:
            #     rank_image = discord.File(f"assets/valo_rank/{tier}.png", filename=f"{tier}.png")
            #     await ctx.reply(embed=embed, file=rank_image)
            # except FileNotFoundError:
            await ctx.reply(embed=embed)
            
        except ValueError as e:
            # 사용자 입력 오류
            await ctx.reply(embed=ValoEmbed.create_error_embed(str(e)))
        except Exception as e:
            # 기타 오류
            logger.error(f"발로란트 티어 명령어 처리 중 오류: {e}")
            await ctx.reply(embed=ValoEmbed.create_error_embed(f"오류가 발생했습니다: {e}"))
    
    @commands.command(
        name='발로.전적',
        aliases=['발로.기록', 'valo.history', 'ㅂㄹ.ㅈㅈ'],
        description="최근 5게임 전적을 조회합니다. (!발로.전적 닉네임#태그)"
    )
    async def valo_history(self, ctx, *, riot_id: str):
        """발로란트 최근 전적 조회 명령어"""
        logger.info(f"valo_history({ctx.guild.name}, {ctx.author.name}, {riot_id})")
        
        try:
            self._setup_session()
            
            # 계정 정보 가져오기
            account_data = await self.valo_service.get_account_info(self.session, riot_id)
            
            # 전적 정보 가져오기
            matches = await self.valo_service.get_match_history(self.session, account_data['puuid'])
            
            title = f"🇻 {account_data['gameName']}#{account_data['tagLine']}의 최근 5게임"
            embed = ValoEmbed.create_history_embed(title, matches)
            
            await ctx.reply(embed=embed)
            
        except ValueError as e:
            # 사용자 입력 오류
            await ctx.reply(embed=ValoEmbed.create_error_embed(str(e)))
        except Exception as e:
            # 기타 오류
            logger.error(f"발로란트 전적 명령어 처리 중 오류: {e}")
            await ctx.reply(embed=ValoEmbed.create_error_embed(f"오류가 발생했습니다: {e}")) 