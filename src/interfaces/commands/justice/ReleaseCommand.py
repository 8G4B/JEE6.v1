import discord
from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.JusticeEmbed import JusticeEmbed

logger = logging.getLogger(__name__)


class ReleaseCommand(BaseCommand):
    @commands.command(
        name="석방",
        aliases=["release", "r", "R", "RELEASE", "ㄱ"],
        description="사용자의 타임아웃을 해제합니다.",
    )
    @commands.has_permissions(moderate_members=True)
    async def release(self, ctx, member: discord.Member, clear_record: bool = False):
        logger.info(
            f"release({ctx.guild.name}, {ctx.author.name}, {member.name}, clear_record={clear_record})"
        )

        try:
            justice_service = self.container.justice_service()
            was_timeout, count = await justice_service.release_user(
                member=member, server_id=ctx.guild.id, clear_record=clear_record
            )

            if not was_timeout:
                await ctx.send(embed=JusticeEmbed.create_not_timeout_embed(member))
                return

            await member.timeout(None)

            embed = JusticeEmbed.create_release_embed(
                member=member,
                count=count,
                clear_record=clear_record,
                moderator_name=ctx.author.display_name,
            )
            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send(embed=JusticeEmbed.create_error_embed("봇 권한 이슈"))
        except Exception as e:
            await ctx.send(embed=JusticeEmbed.create_error_embed(str(e)))
