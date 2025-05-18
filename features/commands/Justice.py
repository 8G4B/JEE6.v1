import discord
from discord.ext import commands
import datetime
import logging
import json
import os

logger = logging.getLogger(__name__)

class Justice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.counts_file = 'counts.json'
        self._load_counts()

    def _load_counts(self):
        if os.path.exists(self.counts_file):
            with open(self.counts_file, 'r') as f:
                self.counts = json.load(f)
        else:
            self.counts = {}

    def _save_counts(self):
        with open(self.counts_file, 'w') as f:
            json.dump(self.counts, f, indent=4)

    async def get_user_count(self, user_id: str, server_id: str) -> int:
        server_counts = self.counts.get(server_id, {})
        return server_counts.get(user_id, 0)

    async def set_user_count(self, user_id: str, server_id: str, count: int):
        if server_id not in self.counts:
            self.counts[server_id] = {}
        self.counts[server_id][user_id] = count
        self._save_counts()

    @commands.command(name='심판', aliases=['judge', 'j', 'J', 'JUDGE', '타임아웃', 'ㅓ'])
    @commands.has_permissions(moderate_members=True)
    async def judge(self, ctx, member: discord.Member, *, reason: str = "없"):
        logger.info(f"judge({ctx.guild.name}, {ctx.author.name}, {member.name}, {reason})")
        
        user_id = str(member.id)
        server_id = str(ctx.guild.id)
        
        count = await self.get_user_count(user_id, server_id) + 1
        await self.set_user_count(user_id, server_id, count)
        
        if count <= 3:
            timeout_duration = datetime.timedelta(minutes=1)
            duration_text = "60초"
        else:
            timeout_duration = datetime.timedelta(weeks=1)
            duration_text = "1주일"
        
        try:
            await member.timeout(timeout_duration, reason=reason)
            
            try:
                dm_embed = discord.Embed(
                    title="✉️ 통지서",
                    description=f"당신은 **{ctx.guild.name}** 서버에서 {duration_text}동안 타임아웃 되었습니다.",
                    color=discord.Color.blue()
                )
                dm_embed.set_footer(text=f"전과 {count}회")
                dm_embed.add_field(name="사유", value=reason, inline=True)
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                await ctx.send(f"{member.mention}에게 메시지가 안보내져요")
            except Exception as e:
                print(e)
            
            embed = discord.Embed(
                title="⚖️ 처벌",
                description=f"전과 {count}범 {member.mention}를 {duration_text}동안 구금했습니다.",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"by {ctx.author.display_name}")
            embed.add_field(name="사유", value=reason, inline=True)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ 오류",
                description="봇 권한 이슈",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 오류",
                description=str(e),
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)

    @commands.command(name='석방', aliases=['release', 'r', 'R', 'RELEASE', 'ㄱ'])
    @commands.has_permissions(moderate_members=True)
    async def release(self, ctx, member: discord.Member, clear_record: bool = False):
        logger.info(f"release({ctx.guild.name}, {ctx.author.name}, {member.name}, clear_record={clear_record})")
        
        user_id = str(member.id)
        server_id = str(ctx.guild.id)
        count = await self.get_user_count(user_id, server_id)

        if member.timed_out_until is None:
            notice_embed = discord.Embed(
                title="ℹ️ 알림",
                description=f"{member.mention}은(는) 타임아웃 상태가 아닙니다.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=notice_embed)
            return

        try:
            await member.timeout(None)
            
            if clear_record and count > 0:
                await self.set_user_count(user_id, server_id, count - 1)
                count -= 1
                clear_msg = "(전과 -1)"
            else:
                clear_msg = "(전과 유지)"
            
            embed = discord.Embed(
                title="🕊️ 석방",
                description=f"전과 {count}범 {member.mention}를 석방했습니다.\n{clear_msg}",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"by {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ 오류",
                description="봇 권한 이슈",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 오류",
                description=str(e),
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed) 