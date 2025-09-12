import discord


class ChannelEmbed:
    @staticmethod
    def create_clean_start_embed(channel_name: str) -> discord.Embed:
        return discord.Embed(
            title="🧹 채널 청소",
            description=f"채널 '{channel_name}'을(를) 삭제하고 다시 생성합니다.",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

    @staticmethod
    def create_clean_success_embed(
        message: str = "채널이 성공적으로 청소되었습니다.",
    ) -> discord.Embed:
        return discord.Embed(
            title="✅ 청소 완료",
            description=message,
            color=discord.Color.green(),
        )

    @staticmethod
    def create_error_embed(error_message: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류",
            description=error_message,
            color=discord.Color.red(),
        )

    @staticmethod
    def create_slow_mode_enabled_embed(
        channel_name: str, period: str = None
    ) -> discord.Embed:
        return discord.Embed(
            title=f"채널 `#{channel_name}`에 슬로우 활성화 ({period or '수업 시간 X'})",
            color=discord.Color.blue(),
        )

    @staticmethod
    def create_slow_mode_disabled_embed(channel_name: str) -> discord.Embed:
        return discord.Embed(
            title=f"✅ `#{channel_name}` 슬로우 상태 비활성화",
            color=discord.Color.green(),
        )

    @staticmethod
    def create_slow_mode_applied_embed(period: str, delay: int) -> discord.Embed:
        return discord.Embed(
            title="🐌 슬로우 적용",
            description=f"{period}교시가 시작되었습니다.",
            color=discord.Color.blue(),
        )

    @staticmethod
    def create_slow_mode_removed_embed() -> discord.Embed:
        return discord.Embed(
            title="⏰ 슬로우 해제",
            color=discord.Color.orange(),
        )
