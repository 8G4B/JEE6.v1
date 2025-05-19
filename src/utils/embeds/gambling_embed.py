import discord
from typing import Optional

class GamblingEmbed:
    @staticmethod
    def create_error_embed(description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류",
            description=description,
            color=discord.Color.red()
        )
    
    @staticmethod
    def create_balance_embed(author_name: str, balance: int) -> discord.Embed:
        return discord.Embed(
            title=f"💰 {author_name}의 지갑",
            description=f"- 현재 재산: {balance:,}원",
            color=discord.Color.gold()
        )
    
    @staticmethod
    def create_work_embed(author_name: str, reward: int, balance: int) -> discord.Embed:
        return discord.Embed(
            title=f"💸 {author_name} 돈 벌었음",
            description=f"## 수익: +{reward:,}원\n- 재산: {balance:,}원",
            color=discord.Color.green()
        )
    
    @staticmethod
    def create_ranking_embed(title: str, description: str) -> discord.Embed:
        return discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
    
    @staticmethod
    def create_transfer_embed(
        sender_name: str, recipient_name: str, 
        amount: int, tax: int, balance: int
    ) -> discord.Embed:
        return discord.Embed(
            title=f"💸 {sender_name}님이 {recipient_name}님에게 송금",
            description=(
                f"## 송금액: {amount:,}원\n"
                f"- 증여세: {tax:,}원\n"
                f"- 실수령액: {amount - tax:,}원\n"
                f"- 송금 후 잔액: {balance:,}원"
            ),
            color=discord.Color.blue()
        )
    
    @staticmethod
    def create_jackpot_embed(title: str, description: str, color) -> discord.Embed:
        return discord.Embed(
            title=title,
            description=description,
            color=color
        )
    
    @staticmethod
    def create_game_embed(
        author_name: str,
        is_correct: bool,
        guess: str,
        result: str,
        bet: Optional[int] = None,
        winnings: Optional[int] = None,
        balance: Optional[int] = None,
        game_type: Optional[str] = None,
        tax: Optional[int] = None
    ) -> discord.Embed:
        title = f"{'🪙' if game_type == 'coin' else '🎲' if game_type == 'dice' else '🎰'} {author_name} {'맞음 ㄹㅈㄷ' if is_correct else '틀림ㅋ'}"
        color = discord.Color.green() if is_correct else discord.Color.red()

        description_parts = [
            f"- 예측: {guess}",
            f"- 결과: {result}"
        ]

        if bet is not None and winnings is not None and balance is not None:
            if is_correct:
                total_winnings = winnings + (tax or 0)
                multiplier = total_winnings / bet
                description_parts.extend([
                    f"## 수익: {bet:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)" if tax else f"## 수익: {bet:,}원 × {multiplier:.2f} = {winnings:,}원",
                    f"- 재산: {balance:,}원(+{winnings:,})"
                ])
            else:
                description_parts.extend([
                    f"## 수익: {bet:,}원 × -1 = {winnings:,}원",
                    f"- 재산: {balance:,}원({winnings:,})"
                ])

        return discord.Embed(
            title=title,
            description="\n".join(description_parts),
            color=color
        )
    
    @staticmethod
    def create_cooldown_embed(remaining_seconds: int) -> discord.Embed:
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        
        time_str = f"{minutes}분 {seconds}초" if minutes > 0 else f"{seconds}초"
            
        return discord.Embed(
            title="⏱️ 쿨타임",
            description=f"{time_str} 후에 다시 시도해주세요.",
            color=discord.Color.orange()
        )
    
    @staticmethod
    def create_blackjack_embed(title: str, description: str, color) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.add_field(name="선택", value="👊 히트 / 🛑 스탠드", inline=False)
        return embed
    
    @staticmethod
    def create_baccarat_embed(title: str, description: str, color) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.add_field(name="선택", value="👤 플레이어 / 🏦 뱅커 / 🤝 타이", inline=False)
        return embed
    
    @staticmethod
    def create_indian_poker_embed(title: str, description: str, color) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.add_field(name="선택", value="💀 다이 / ✅ 콜", inline=False)
        return embed 