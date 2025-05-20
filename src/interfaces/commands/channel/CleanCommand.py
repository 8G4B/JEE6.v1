from discord.ext import commands
import shlex
from src.interfaces.commands.Basee import BaseCommand
from src.utils.embeds.ChannelEmbed import ChannelEmbed
import logging

logger = logging.getLogger(__name__)


class CleanCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)

    @commands.command(
        name="청소",
        aliases=["clean", "c", "C", "CLEAN", "ㅊ"],
        description="청소 [-n 채널명]",
    )
    @commands.has_permissions(manage_channels=True)
    async def clean_channel(self, ctx, *, arg: str = None):
        channel_name = self._parse_clean_args(arg)

        if channel_name:
            await self.clean_channel_once(ctx, channel_name)
        else:
            await self.clean_channel_once(ctx)

    def _parse_clean_args(self, arg):
        if not arg:
            return None

        channel_name = None
        tokens = shlex.split(arg)
        i = 0
        while i < len(tokens):
            if (tokens[i] in ("-n", "--name")) and i + 1 < len(tokens):
                channel_name = tokens[i + 1]
                i += 2
            else:
                channel_name = arg
                break

        return channel_name

    async def clean_channel_once(self, ctx, channel_name=None):
        channel_service = self.container.channel_service()
        start_embed = ChannelEmbed.create_clean_start_embed(
            channel_name or ctx.channel.name
        )
        await ctx.send(embed=start_embed)
        success, message, new_channel = await channel_service.clean_channel(
            ctx.guild, ctx.channel, channel_name
        )
        if success and new_channel:
            success_embed = ChannelEmbed.create_clean_success_embed()
            await new_channel.send(embed=success_embed)
        else:
            error_embed = ChannelEmbed.create_error_embed(message)
            await ctx.send(embed=error_embed)
