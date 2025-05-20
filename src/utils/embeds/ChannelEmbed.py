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
            timestamp=discord.utils.utcnow(),
        )

    @staticmethod
    def create_error_embed(error_message: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류",
            description=error_message,
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
