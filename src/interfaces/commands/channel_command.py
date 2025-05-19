from discord.ext import commands
import logging
from src.interfaces.commands.base_command import BaseCommand
from src.utils.embeds.channel_embed import ChannelEmbed

logger = logging.getLogger(__name__)

class ChannelCommands(BaseCommand):
    @commands.command(
        name='청소',
        aliases=['clean', 'c', 'C', 'CLEAN', 'ㅊ'],
        description="채널을 청소합니다."
    )
    @commands.has_permissions(manage_channels=True)
    async def clean_channel(self, ctx, *, channel_name: str = None):
        logger.info(f"clean_channel({ctx.guild.name}, {ctx.author.name})")
        
        channel_service = self.container.channel_service()
        
        start_embed = ChannelEmbed.create_clean_start_embed(
            channel_name or ctx.channel.name
        )
        await ctx.send(embed=start_embed)
        
        success, message, new_channel = await channel_service.clean_channel(
            ctx.guild,
            ctx.channel,
            channel_name
        )
        
        if success and new_channel:
            success_embed = ChannelEmbed.create_clean_success_embed()
            await new_channel.send(embed=success_embed)
        else:
            error_embed = ChannelEmbed.create_error_embed(message)
            await ctx.send(embed=error_embed) 