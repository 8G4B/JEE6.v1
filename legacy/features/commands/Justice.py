import discord
from discord.ext import commands
import datetime
import logging
from shared.database import get_connection

logger = logging.getLogger(__name__)


class Justice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_count(self, user_id: str, server_id: str) -> int:
        connection = await get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                sql = "SELECT count FROM justice_records WHERE user_id = %s AND server_id = %s"
                cursor.execute(sql, (int(user_id), int(server_id)))
                result = cursor.fetchone()
                cursor.close()
                if result:
                    return result["count"]
                return 0
            except Exception as e:
                logger.error(f"get_user_count({user_id}, {server_id}) FAIL: {e}")
                return 0
            finally:
                connection.close()
        return 0

    async def set_user_count(self, user_id: str, server_id: str, count: int):
        connection = await get_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    sql = """
                    INSERT INTO justice_records (user_id, server_id, count, last_timeout) 
                    VALUES (%s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE count = %s, last_timeout = NOW()
                    """
                    cursor.execute(sql, (int(user_id), int(server_id), count, count))
                connection.commit()
                logger.info(f"set_user_count({user_id}, {server_id}, {count}) OKAY")
                return True
            except Exception as e:
                logger.error(
                    f"set_user_count({user_id}, {server_id}, {count}) FAIL: {e}"
                )
            finally:
                connection.close()
        return False

    async def add_timeout_history(
        self,
        user_id: str,
        server_id: str,
        moderator_id: str,
        reason: str,
        duration: datetime.timedelta,
    ):
        connection = await get_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    duration_seconds = int(duration.total_seconds())
                    sql = """
                    INSERT INTO timeout_history 
                    (user_id, server_id, moderator_id, reason, duration) 
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(
                        sql,
                        (
                            int(user_id),
                            int(server_id),
                            int(moderator_id),
                            reason,
                            duration_seconds,
                        ),
                    )
                connection.commit()
                logger.info(
                    f"add_timeout_history({user_id}, {server_id}, {moderator_id}) OKAY"
                )
                return True
            except Exception as e:
                logger.error(f"add_timeout_history FAIL: {e}")
            finally:
                connection.close()
        return False

    @commands.command(
        name="심판", aliases=["judge", "j", "J", "JUDGE", "타임아웃", "ㅓ"]
    )
    @commands.has_permissions(moderate_members=True)
    async def judge(self, ctx, member: discord.Member, *, reason: str = "없"):
        logger.info(
            f"judge({ctx.guild.name}, {ctx.author.name}, {member.name}, {reason})"
        )

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
            await self.add_timeout_history(
                user_id, server_id, str(ctx.author.id), reason, timeout_duration
            )

            try:
                dm_embed = discord.Embed(
                    title="✉️ 통지서",
                    description=f"당신은 **{ctx.guild.name}** 서버에서 {duration_text}동안 타임아웃 되었습니다.",
                    color=discord.Color.blue(),
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
                color=discord.Color.blue(),
            )
            embed.set_footer(text=f"by {ctx.author.display_name}")
            embed.add_field(name="사유", value=reason, inline=True)

            await ctx.send(embed=embed)

        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ 오류", description="봇 권한 이슈", color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 오류", description=str(e), color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)

    @commands.command(name="석방", aliases=["release", "r", "R", "RELEASE", "ㄱ"])
    @commands.has_permissions(moderate_members=True)
    async def release(self, ctx, member: discord.Member, clear_record: bool = False):
        logger.info(
            f"release({ctx.guild.name}, {ctx.author.name}, {member.name}, clear_record={clear_record})"
        )

        user_id = str(member.id)
        server_id = str(ctx.guild.id)
        count = await self.get_user_count(user_id, server_id)

        if member.timed_out_until is None:
            notice_embed = discord.Embed(
                title="ℹ️ 알림",
                description=f"{member.mention}은(는) 타임아웃 상태가 아닙니다.",
                color=discord.Color.blue(),
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
                color=discord.Color.green(),
            )
            embed.set_footer(text=f"by {ctx.author.display_name}")

            await ctx.send(embed=embed)

        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ 오류", description="봇 권한 이슈", color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 오류", description=str(e), color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
