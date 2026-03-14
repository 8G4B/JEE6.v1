import discord
from discord.ext import commands
import logging
from src.interfaces.commands.Base import BaseCommand

logger = logging.getLogger(__name__)


class MentionCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)

    @commands.command(name="멘션", description="답장한 메시지에 이모지를 단 사람들을 멘션합니다.")
    async def mention_reactors(self, ctx):
        if ctx.message.reference is None:
            embed = discord.Embed(
                title="❌ 오류",
                description="멘션할 메시지에 **답장**으로 `!멘션` 명령어를 사용해주세요.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed)
            return

        try:
            ref = ctx.message.reference
            if ref.cached_message:
                original_message = ref.cached_message
            else:
                original_message = await ctx.channel.fetch_message(ref.message_id)
        except discord.NotFound:
            embed = discord.Embed(
                title="❌ 오류",
                description="원본 메시지를 찾을 수 없습니다.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed)
            return

        if not original_message.reactions:
            embed = discord.Embed(
                title="😶 이모지 없음",
                description="해당 메시지에 이모지를 단 사람이 없습니다.",
                color=discord.Color.orange()
            )
            await ctx.reply(embed=embed)
            return

        reacted_users = set()
        for reaction in original_message.reactions:
            async for user in reaction.users():
                if not user.bot:
                    reacted_users.add(user)

        if not reacted_users:
            embed = discord.Embed(
                title="😶 이모지 없음",
                description="해당 메시지에 이모지를 단 사람이 없습니다. (봇 제외)",
                color=discord.Color.orange()
            )
            await ctx.reply(embed=embed)
            return

        mentions = " ".join(user.mention for user in reacted_users)
        await ctx.reply(mentions)
