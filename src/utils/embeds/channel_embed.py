import discord

class ChannelEmbed:
    @staticmethod
    def create_clean_start_embed(channel_name: str) -> discord.Embed:
        return discord.Embed(
            title="🧹 채널 청소",
            description=f"채널 '{channel_name}'을(를) 삭제하고 다시 생성합니다.",
            color=discord.Color.blue()
        )

    @staticmethod
    def create_clean_success_embed() -> discord.Embed:
        return discord.Embed(
            title="✅ 청소 완료",
            description="채널이 성공적으로 청소되었습니다.",
            color=discord.Color.green()
        )

    @staticmethod
    def create_error_embed(error_message: str) -> discord.Embed:
        return discord.Embed(
            title="❌ 오류",
            description=error_message,
            color=discord.Color.red()
        ) 