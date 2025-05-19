import discord
from discord.ext import commands
import logging
from src.interfaces.commands.base_command import BaseCommand
from src.utils.embeds.justice_embed import JusticeEmbed

logger = logging.getLogger(__name__)

class JusticeCommands(BaseCommand):
    @commands.command(
        name='심판',
        aliases=['judge', 'j', 'J', 'JUDGE', '타임아웃', 'ㅓ'],
        description="사용자를 타임아웃 시킵니다."
    )
    @commands.has_permissions(moderate_members=True)
    async def judge(self, ctx, member: discord.Member, *, reason: str = "없"):
        logger.info(f"judge({ctx.guild.name}, {ctx.author.name}, {member.name}, {reason})")
        
        try:
            justice_service = self.container.justice_service()
            count, duration = await justice_service.judge_user(
                member=member,
                server_id=ctx.guild.id,
                moderator_id=ctx.author.id,
                reason=reason
            )
            
            # Apply timeout
            await member.timeout(duration, reason=reason)
            
            # Send DM to user
            try:
                dm_embed = JusticeEmbed.create_judge_dm_embed(
                    server_name=ctx.guild.name,
                    duration=duration,
                    count=count,
                    reason=reason
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                await ctx.send(f"{member.mention}에게 메시지가 안보내져요")
            except Exception as e:
                logger.error(f"DM send error: {e}")
            
            # Send response in channel
            embed = JusticeEmbed.create_judge_embed(
                member=member,
                duration=duration,
                count=count,
                reason=reason,
                moderator_name=ctx.author.display_name
            )
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=JusticeEmbed.create_error_embed("봇 권한 이슈"))
        except Exception as e:
            await ctx.send(embed=JusticeEmbed.create_error_embed(str(e)))

    @commands.command(
        name='석방',
        aliases=['release', 'r', 'R', 'RELEASE', 'ㄱ'],
        description="사용자의 타임아웃을 해제합니다."
    )
    @commands.has_permissions(moderate_members=True)
    async def release(self, ctx, member: discord.Member, clear_record: bool = False):
        logger.info(f"release({ctx.guild.name}, {ctx.author.name}, {member.name}, clear_record={clear_record})")
        
        try:
            justice_service = self.container.justice_service()
            was_timeout, count = await justice_service.release_user(
                member=member,
                server_id=ctx.guild.id,
                clear_record=clear_record
            )
            
            if not was_timeout:
                await ctx.send(embed=JusticeEmbed.create_not_timeout_embed(member))
                return
                
            await member.timeout(None)
            
            embed = JusticeEmbed.create_release_embed(
                member=member,
                count=count,
                clear_record=clear_record,
                moderator_name=ctx.author.display_name
            )
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=JusticeEmbed.create_error_embed("봇 권한 이슈"))
        except Exception as e:
            await ctx.send(embed=JusticeEmbed.create_error_embed(str(e)))