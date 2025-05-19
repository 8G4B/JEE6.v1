import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


class Clean(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="청소", aliases=["clean", "c", "C", "CLEAN", "ㅊ"])
    @commands.has_permissions(manage_channels=True)
    async def clean_channel(self, ctx, *, channel_name: str = None):
        logger.info(f"clean_channel({ctx.guild.name}, {ctx.author.name})")
        try:
            original_channel = ctx.channel
            channel_to_delete = original_channel

            if channel_name:
                found_channel = discord.utils.get(
                    ctx.guild.text_channels, name=channel_name
                )
                if found_channel:
                    channel_to_delete = found_channel
                else:
                    embed = discord.Embed(
                        title="❌ 오류",
                        description=f"'{channel_name}' 이런 채널 없는데요",
                        color=discord.Color.red(),
                    )
                    await ctx.send(embed=embed)
                    return

            # 채널 속성 저장
            category = channel_to_delete.category
            position = channel_to_delete.position
            topic = channel_to_delete.topic
            slowmode_delay = channel_to_delete.slowmode_delay
            nsfw = channel_to_delete.is_nsfw()
            overwrites = channel_to_delete.overwrites

            # 청소 시작 알림
            embed = discord.Embed(
                title="🧹 채널 청소",
                description=f"채널 '{channel_to_delete.name}'을(를) 삭제하고 다시 생성합니다.",
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)

            # 채널 삭제
            await channel_to_delete.delete(reason="채널 청소")

            # 새 채널 생성
            new_channel = await ctx.guild.create_text_channel(
                name=channel_to_delete.name,
                category=category,
                topic=topic,
                slowmode_delay=slowmode_delay,
                nsfw=nsfw,
                overwrites=overwrites,
                position=position,
                reason="채널 청소",
            )

            # 완료 메시지
            embed = discord.Embed(
                title="✅ 청소 완료",
                description="채널이 성공적으로 청소되었습니다.",
                color=discord.Color.green(),
            )
            await new_channel.send(embed=embed)

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ 오류",
                description="권한이 부족합니다.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ 오류", description=str(e), color=discord.Color.red()
            )
            await ctx.send(embed=embed)
