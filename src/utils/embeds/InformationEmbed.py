import discord


class InformationEmbed:
    @staticmethod
    def create_info_embed(latency: int, db_status: str) -> discord.Embed:
        embed = discord.Embed(
            title="💬 JEE6",
            description=(
                f"- [명령어 + 도박 관련](https://github.com/8G4B/JEE6.v1/blob/master/README.md#%EB%AA%85%EB%A0%B9%EC%96%B4-%EC%9D%BC%EB%9E%8C)\n"
                f"- [실행 방법](https://github.com/8G4B/JEE6.v1/blob/master/README.md#%EB%A1%9C%EC%BB%AC%EC%97%90%EC%84%9C-%EC%8B%A4%ED%96%89)\n"
                f"- [소스코드](https://github.com/8G4B/JEE6.v1)\n\n"
                f"- [만든놈](https://github.com/976520) \n"
                f"- [만든놈한테 쌕쌕 사주기](https://aq.gy/f/9LOJx)\n\n"
                f"- 핑: {latency}ms\n"
                f"- DB: {db_status}"
            ),
            color=discord.Color.yellow(),
        )
        return embed
