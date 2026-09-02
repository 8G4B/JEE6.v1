import math

import discord

from src.services.WorkService import WorkStatus

_WEEKDAY_NAMES = ("월", "화", "수", "목", "금", "토", "일")


class WorkEmbed:
    @staticmethod
    def create_work_embed(status: WorkStatus) -> discord.Embed:
        if status.state == "target_time":
            if status.mode == "regular":
                title = "🎉 지금 퇴근 시간이에요!"
                description = "오늘도 수고 많으셨어요. 편안히 쉬세요!"
                color = discord.Color.green()
            else:
                title = "🌙 야근이 끝났어요!"
                description = "늦게까지 고생 많으셨어요. 이제 푹 쉬세요!"
                color = discord.Color.purple()

            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
            )
            embed.set_footer(text="한국 시간(KST) 기준")
            return embed

        remaining_seconds = max(
            0,
            math.ceil((status.target - status.now).total_seconds()),
        )
        hours, remainder = divmod(remaining_seconds, 60 * 60)
        minutes, seconds = divmod(remainder, 60)

        if status.mode == "regular":
            title = "🎉 퇴근까지"
            footer_label = "퇴근 예정"
            target_text = "오후 4시 30분"
            color = discord.Color.green()
        else:
            title = "🌙 야근 종료까지"
            footer_label = "야근 종료 예정"
            target_text = "오후 9시 30분"
            color = discord.Color.purple()

        embed = discord.Embed(
            title=title,
            description=f"## {hours}시간 {minutes}분 {seconds}초 남았습니다",
            color=color,
        )
        embed.set_footer(
            text=(
                f"{footer_label} · {status.target.month}월 {status.target.day}일"
                f"({_WEEKDAY_NAMES[status.target.weekday()]}) {target_text} · KST"
            )
        )
        return embed

    @staticmethod
    def create_error_embed() -> discord.Embed:
        return discord.Embed(
            title="❗ 퇴근 시간을 계산할 수 없어요",
            description="잠시 후 다시 시도해주세요.",
            color=discord.Color.red(),
        )
