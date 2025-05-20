import discord
from datetime import timedelta
from src.utils.time.formatSeconds import format_seconds


class JusticeEmbed:
    @staticmethod
    def create_judge_dm_embed(
        server_name: str, duration: timedelta, count: int, reason: str
    ) -> discord.Embed:
        if duration <= timedelta(minutes=1):
            duration_text = "60초"
        elif duration == timedelta(weeks=1):
            duration_text = "1주일"
        else:
            duration_text = format_seconds(int(duration.total_seconds()))

        return (
            discord.Embed(
                title="✉️ 통지서",
                description=f"당신은 **{server_name}** 서버에서 {duration_text}동안 타임아웃 되었습니다.",
                color=discord.Color.blue(),
            )
            .set_footer(text=f"전과 {count}회")
            .add_field(name="사유", value=reason, inline=True)
        )

    @staticmethod
    def create_judge_embed(
        member: discord.Member,
        duration: timedelta,
        count: int,
        reason: str,
        moderator_name: str,
    ) -> discord.Embed:
        if duration <= timedelta(minutes=1):
            duration_text = "60초"
        elif duration == timedelta(weeks=1):
            duration_text = "1주일"
        else:
            duration_text = format_seconds(int(duration.total_seconds()))

        return (
            discord.Embed(
                title="⚖️ 처벌",
                description=f"전과 {count}범 {member.mention}를 {duration_text}동안 구금했습니다.",
                color=discord.Color.blue(),
            )
            .set_footer(text=f"by {moderator_name}")
            .add_field(name="사유", value=reason, inline=True)
        )

    @staticmethod
    def create_release_embed(
        member: discord.Member, count: int, clear_record: bool, moderator_name: str
    ) -> discord.Embed:
        clear_msg = "(전과 -1)" if clear_record else "(전과 유지)"
        return discord.Embed(
            title="🕊️ 석방",
            description=f"전과 {count}범 {member.mention}를 석방했습니다.\n{clear_msg}",
            color=discord.Color.green(),
        ).set_footer(text=f"by {moderator_name}")

    @staticmethod
    def create_not_timeout_embed(member: discord.Member) -> discord.Embed:
        return discord.Embed(
            title="ℹ️ 알림",
            description=f"{member.mention}은(는) 타임아웃 상태가 아닙니다.",
            color=discord.Color.blue(),
        )

    @staticmethod
    def create_error_embed(error: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류", description=str(error), color=discord.Color.red()
        )
