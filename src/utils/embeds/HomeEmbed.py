import math

import discord

from src.services.HomeService import HomeStatus

_WEEKDAY_NAMES = ("월", "화", "수", "목", "금", "토", "일")


class HomeEmbed:
    @staticmethod
    def create_home_embed(status: HomeStatus) -> discord.Embed:
        if status.state == "day_off":
            embed = discord.Embed(
                title="🏠 오늘은 쉬는 날이에요!",
                description=f"**{status.day_off_name}**이라 하교 카운트다운이 필요 없어요.",
                color=discord.Color.gold(),
            )
        elif status.state == "dismissal_time":
            embed = discord.Embed(
                title="🏠 지금 하교 시간이에요!",
                description="드디어 집에 갈 시간이에요. 조심히 가세요!",
                color=discord.Color.green(),
            )
        elif status.state == "dismissed":
            embed = discord.Embed(
                title="🏠 하교 완료!",
                description="오늘 하교 시간인 **오후 4시 20분**이 지났어요.",
                color=discord.Color.blue(),
            )
        else:
            return HomeEmbed._create_countdown_embed(status)

        embed.set_footer(text="한국 시간(KST) 기준")
        return embed

    @staticmethod
    def _create_countdown_embed(status: HomeStatus) -> discord.Embed:
        if status.target is None:
            raise ValueError("카운트다운 상태에는 하교 시각이 필요합니다.")

        remaining_seconds = max(
            0,
            math.ceil((status.target - status.now).total_seconds()),
        )
        duration = HomeEmbed._format_duration(remaining_seconds)
        target = status.target

        embed = discord.Embed(
            title="🏠 하교 카운트다운",
            description=f"## ⏳ {duration} 남았어요!",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="✨ 하교 기준",
            value=status.reason,
            inline=False,
        )
        if not status.schedule_available:
            embed.add_field(
                name="⚠️ 일정 안내",
                value="학사일정을 확인하지 못해 금요일 기준으로 계산했어요.",
                inline=False,
            )
        embed.set_footer(
            text=(
                f"하교 예정 · {target.month}월 {target.day}일"
                f"({_WEEKDAY_NAMES[target.weekday()]}) 오후 4시 20분 · KST"
            )
        )
        return embed

    @staticmethod
    def _format_duration(total_seconds: int) -> str:
        hours, remainder = divmod(total_seconds, 60 * 60)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if hours:
            parts.append(f"{hours}시간")
        if minutes:
            parts.append(f"{minutes}분")
        if seconds or not parts:
            parts.append(f"{seconds}초")
        return " ".join(parts)

    @staticmethod
    def create_error_embed() -> discord.Embed:
        return discord.Embed(
            title="❗ 하교 시간을 계산할 수 없어요",
            description="잠시 후 다시 시도해주세요.",
            color=discord.Color.red(),
        )
