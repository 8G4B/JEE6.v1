import logging
import discord
from discord.ext import commands
from src.interfaces.commands.Base import BaseCommand
from src.services.LangService import LangService
from src.infrastructure.database.Session import get_db_session
from src.config.settings.base import BaseConfig
from src.utils.embeds.MealEmbed import MealEmbed
from src.utils.embeds.WaterEmbed import WaterEmbed
from src.utils.embeds.TimeEmbed import TimeEmbed
from src.utils.embeds.LolEmbed import LolEmbed
from src.utils.embeds.ValoEmbed import ValoEmbed
from src.utils.embeds.GamblingEmbed import GamblingEmbed

logger = logging.getLogger(__name__)


class LangCommand(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.lang_service = LangService()
        self._enabled_channels: set[int] = set()
        self._cache_loaded = False
        self._services_wired = False

    def _wire_services(self):
        if self._services_wired:
            return
        try:
            from src.services.GamblingService import GamblingService
            self.lang_service.set_gambling_service(GamblingService())
        except Exception as e:
            logger.warning(f"GamblingService 연동 실패: {e}")

        try:
            flooding_api = self.container.flooding_api_service()
            flooding_auth = self.container.flooding_auth_service()
            self.lang_service.set_flooding_services(flooding_api, flooding_auth)
        except Exception as e:
            logger.warning(f"FloodingService 연동 실패: {e}")

        self._services_wired = True

    def _load_enabled_channels(self):
        if self._cache_loaded:
            return
        try:
            with get_db_session() as db:
                repo = self.container.channel_lang_repository(db=db)
                self._enabled_channels = repo.get_all_enabled_channel_ids()
            self._cache_loaded = True
            self._wire_services()
            logger.info(f"자연어 모드 활성 채널 {len(self._enabled_channels)}개 로드")
        except Exception as e:
            logger.error(f"자연어 모드 채널 로드 실패: {e}")

    def _build_response(self, result: dict) -> dict:
        t = result.get("type")

        if t == "meal":
            embed = MealEmbed.create_meal_embed(result["title"], result["menu"], result.get("cal_info", ""))
            return {"embed": embed}

        if t == "water":
            embed = WaterEmbed.create_water_embed(result["hour"], result["minute"], result["temp"])
            return {"embed": embed}

        if t == "time":
            embed = TimeEmbed.create_time_embed(result["datetime"])
            return {"embed": embed}

        if t == "info":
            embed = discord.Embed(
                title="🤖 JEE6 봇 정보",
                color=discord.Color.blurple(),
            )
            embed.add_field(name="지연 시간", value=f"{result['latency']}ms", inline=True)
            embed.add_field(name="서버 수", value=f"{result['guild_count']}개", inline=True)
            return {"embed": embed}

        if t == "lol_tier":
            solo_rank = result.get("solo_rank")
            riot_id = result["riot_id"]
            tier = result["tier"]
            if solo_rank:
                desc = (
                    f"**{solo_rank['tier']} {solo_rank['rank']}** ({solo_rank['leaguePoints']}LP)\n"
                    f"{solo_rank['wins']}승 {solo_rank['losses']}패"
                )
            else:
                desc = tier
            embed = LolEmbed.create_tier_embed(f"🎮 {riot_id}", desc, tier)
            return {"embed": embed}

        if t == "lol_history":
            embed = LolEmbed.create_history_embed(f"🎮 {result['riot_id']} 최근 전적", result["matches"])
            return {"embed": embed}

        if t == "lol_rotation":
            champions = result.get("champions", [])
            if not champions:
                return {"content": "로테이션 정보를 가져올 수 없습니다."}
            names = [c.get("name", "?") for c in champions]
            embed = discord.Embed(
                title="🎮 금주 무료 챔피언 로테이션",
                description=", ".join(names),
                color=discord.Color.blue(),
            )
            return {"embed": embed}

        if t == "valo_tier":
            embed = ValoEmbed.create_tier_embed(f"🎯 {result['riot_id']}", result["tier"], result["tier"])
            return {"embed": embed}

        if t == "valo_history":
            embed = ValoEmbed.create_history_embed(f"🎯 {result['riot_id']} 최근 전적", result["matches"])
            return {"embed": embed}

        if t == "music":
            track = result["track"]
            embed = discord.Embed(
                title=track["name"],
                url=track["url"],
                description=f"**{track['artists']}**\n앨범: {track['album']}",
                color=discord.Color.from_rgb(30, 215, 96),
            )
            genre_text = ", ".join(track["genres"][:2]) if track.get("genres") else ""
            footer = f"⏱ {track['duration']}"
            if genre_text:
                footer += f"  |  {genre_text}"
            embed.set_footer(text=footer)
            if track.get("image"):
                embed.set_thumbnail(url=track["image"])
            return {"embed": embed}

        if t == "balance":
            embed = GamblingEmbed.create_balance_embed(
                result.get("author_name", "유저"), result["balance"]
            )
            return {"embed": embed}

        if t == "ranking":
            rankings = result.get("rankings", [])
            if not rankings:
                return {"content": "랭킹 데이터가 없습니다."}
            lines = []
            for i, (name, balance) in enumerate(rankings[:10], 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i}.**")
                lines.append(f"{medal} {name}: {balance:,}원")
            embed = GamblingEmbed.create_ranking_embed(
                "🏆 도박 랭킹 TOP 10", "\n".join(lines)
            )
            return {"embed": embed}

        if t == "work":
            embed = GamblingEmbed.create_work_embed(
                result.get("author_name", "유저"), result["reward"], result["balance"]
            )
            return {"embed": embed}

        if t == "cooldown":
            embed = GamblingEmbed.create_cooldown_embed(result["remaining"])
            return {"embed": embed}

        if t == "jackpot":
            amount = result.get("amount", 0)
            embed = discord.Embed(
                title="🎰 현재 잭팟",
                description=f"**{amount:,}원**",
                color=discord.Color.gold(),
            )
            return {"embed": embed}

        if t == "flooding_music":
            data = result.get("data")
            if not data or not data.get("items"):
                return {"content": "오늘의 기상 음악이 없습니다."}
            lines = []
            for i, item in enumerate(data["items"][:10], 1):
                title = item.get("title", "?")
                artist = item.get("artist", "")
                lines.append(f"**{i}.** {title}" + (f" — {artist}" if artist else ""))
            embed = discord.Embed(
                title="🎵 오늘의 기상 음악",
                description="\n".join(lines),
                color=discord.Color.orange(),
            )
            return {"embed": embed}

        if t == "flooding_profile":
            data = result.get("data")
            if not data:
                return {"content": "프로필 정보를 가져올 수 없습니다."}
            embed = discord.Embed(
                title="📋 플러딩 프로필",
                description=str(data),
                color=discord.Color.teal(),
            )
            return {"embed": embed}

        if t == "error":
            embed = discord.Embed(
                title="❗ 오류",
                description=result.get("message", "알 수 없는 오류"),
                color=discord.Color.red(),
            )
            return {"embed": embed}

        # type == "text"
        content = result.get("content", "")
        if not content:
            return {}
        return {"content": content}

    @commands.command(
        name="lang",
        aliases=["자연어", "ㅈㅇㅇ"],
        description="현재 채널의 자연어 명령 모드를 토글합니다. (관리자 전용)",
    )
    @commands.has_permissions(manage_channels=True)
    async def toggle_lang(self, ctx):
        logger.info(f"lang_toggle({ctx.guild.name}, {ctx.channel.name}, {ctx.author.name})")

        try:
            with get_db_session() as db:
                repo = self.container.channel_lang_repository(db=db)
                enabled = repo.toggle(ctx.guild.id, ctx.channel.id)

            if enabled:
                self._enabled_channels.add(ctx.channel.id)
            else:
                self._enabled_channels.discard(ctx.channel.id)

            status = "활성화" if enabled else "비활성화"
            color = discord.Color.green() if enabled else discord.Color.red()

            embed = discord.Embed(
                title="🧠 자연어 명령 모드",
                description=f"이 채널에서 자연어 명령 모드가 **{status}** 되었습니다.",
                color=color,
            )
            if enabled:
                embed.add_field(
                    name="사용법",
                    value="이제 `!` 없이 자연스럽게 말하면 됩니다.\n"
                          "예: \"오늘 급식 뭐야?\", \"한강 수온 알려줘\"",
                    inline=False,
                )
            await ctx.reply(embed=embed)

        except Exception as e:
            logger.error(f"lang 토글 오류: {e}")
            await ctx.reply(f"오류가 발생했습니다: {e}")

    @commands.command(
        name="질문",
        aliases=["ask", "ㅈㅁ"],
        description="AI에게 질문합니다.",
    )
    async def ask(self, ctx, *, question: str = None):
        if not question:
            await ctx.reply("질문 내용을 입력해주세요. 예: `!질문 파이썬이 뭐야?`")
            return

        logger.info(f"ask({ctx.guild.name}, {ctx.author.name}, {question[:50]})")

        async with ctx.typing():
            answer = await self.lang_service.ask_question(question)

        if len(answer) > 4096:
            answer = answer[:4093] + "..."

        embed = discord.Embed(
            title="🤖 AI 답변",
            description=answer,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"질문: {question[:100]}")
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if not message.guild:
            return

        if message.content.startswith(BaseConfig.PREFIX):
            return

        self._load_enabled_channels()

        if message.channel.id not in self._enabled_channels:
            return

        content = message.content.strip()
        if not content or len(content) < 2:
            return

        logger.info(f"lang_process({message.guild.name}, {message.channel.name}, {message.author.name}, {content[:50]})")

        context = {
            "user_id": message.author.id,
            "server_id": message.guild.id,
            "author_name": message.author.display_name,
            "bot": self.bot,
        }

        # LLM 호출 (typing 없이 — IGNORE 시 입력 중 표시 방지)
        result = await self.lang_service.process_message(content, context)

        if not result:
            return

        # 실제 응답이 있을 때만 typing 표시 후 응답 전송
        response = self._build_response(result)
        if not response:
            return

        if "embed" in response:
            await message.reply(embed=response["embed"], mention_author=False)
        elif "content" in response:
            text = response["content"].strip()
            if not text or text == "IGNORE":
                return
            if len(text) > 2000:
                text = text[:1997] + "..."
            await message.reply(text, mention_author=False)
