import discord
from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.JusticeEmbed import JusticeEmbed

logger = logging.getLogger(__name__)


class JusticeCommands(BaseCommand):
    def _parse_judge_args(self, args):
        message = "없"
        custom_duration = None

        i = 0
        while i < len(args):
            if args[i] in ("-m", "--message") and i + 1 < len(args):
                message_parts = []
                j = i + 1
                while j < len(args) and not args[j].startswith("-"):
                    message_parts.append(args[j])
                    j += 1
                message = " ".join(message_parts)
                i = j
            elif args[i] in ("-p", "--period") and i + 1 < len(args):
                custom_duration = args[i + 1]
                i += 2
            else:
                i += 1

        return message, custom_duration

    @commands.command(
        name="심판",
        aliases=["judge", "j", "J", "JUDGE", "타임아웃", "ㅓ"],
        description="!심판 [유저] (-m [메시지]) (-p [기간])",
    )
    @commands.has_permissions(moderate_members=True)
    async def judge(self, ctx, member: discord.Member, *args):
        logger.info(
            f"judge({ctx.guild.name}, {ctx.author.name}, {member.name}, {args})"
        )

        message, custom_duration = self._parse_judge_args(args)

        try:
            justice_service = self.container.justice_service()
            count, duration = await justice_service.judge_user(
                member=member,
                server_id=ctx.guild.id,
                moderator_id=ctx.author.id,
                reason=message,
                custom_duration=custom_duration,
            )

            await member.timeout(duration, reason=message)

            try:
                dm_embed = JusticeEmbed.create_judge_dm_embed(
                    server_name=ctx.guild.name,
                    duration=duration,
                    count=count,
                    reason=message,
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                await ctx.send(f"{member.mention}에게 메시지가 안보내져요")
            except Exception as e:
                logger.error(f"DM send error: {e}")

            embed = JusticeEmbed.create_judge_embed(
                member=member,
                duration=duration,
                count=count,
                reason=message,
                moderator_name=ctx.author.display_name,
            )
            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send(embed=JusticeEmbed.create_error_embed("봇 권한 이슈"))
        except Exception as e:
            await ctx.send(embed=JusticeEmbed.create_error_embed(str(e)))
