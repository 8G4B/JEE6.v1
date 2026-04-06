import logging
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from src.config.settings.base import BaseConfig
from src.services.MealService import MealService
from src.services.WaterService import WaterService
from src.services.TimeService import TimeService
from src.services.LolService import LolService
from src.services.ValoService import ValoService
from src.services.SpotifyService import SpotifyService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """너는 디스코드 봇 JEE6의 자연어 처리 엔진이야.
사용자의 자연어 메시지를 분석해서 적절한 도구(tool)를 호출해.

사용 가능한 기능:
- 급식 조회 (오늘/내일, 아침/점심/저녁)
- 한강 수온 조회
- 현재 시간 조회
- 롤(League of Legends) 티어/전적 조회 (닉네임#태그 필요)
- 발로란트(Valorant) 티어/전적 조회 (닉네임#태그 필요)
- 음악 추천 (Spotify 랜덤 곡)

규칙:
- 사용자가 명확하게 위 기능 중 하나를 요청한 경우에만 도구를 호출해.
- 어떤 도구에도 해당하지 않는 일반 대화나 질문이면 도구 없이 직접 한국어로 답변해.
- 답변은 간결하게.
- 롤/발로란트 조회 시 닉네임#태그가 없으면 사용자에게 요청해.
"""


class LangService:
    def __init__(self):
        self.llm = ChatGroq(
            api_key=BaseConfig.GROQ_API_KEY,
            model=BaseConfig.GROQ_MODEL,
            temperature=0,
            max_tokens=1024,
        )
        self.meal_service = MealService()
        self.water_service = WaterService()
        self.time_service = TimeService()
        self.lol_service = LolService()
        self.valo_service = ValoService()
        self.spotify_service = SpotifyService()

        self.tools = [
            self._make_get_meal_tool(),
            self._make_get_water_temp_tool(),
            self._make_get_time_tool(),
            self._make_get_lol_tier_tool(),
            self._make_get_lol_history_tool(),
            self._make_get_valo_tier_tool(),
            self._make_get_valo_history_tool(),
            self._make_get_music_tool(),
        ]

        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _make_get_meal_tool(self):
        meal_service = self.meal_service

        @tool
        async def get_meal(meal_type: str = "auto", day: str = "today") -> str:
            """급식을 조회합니다.

            Args:
                meal_type: 'breakfast', 'lunch', 'dinner', or 'auto' (시간에 따라 자동)
                day: 'today' or 'tomorrow'
            """
            now = datetime.now()
            if day == "tomorrow":
                date_str = (now + timedelta(days=1)).strftime("%Y%m%d")
            else:
                date_str = now.strftime("%Y%m%d")

            if meal_type == "auto":
                title, menu, cal_info = await meal_service.get_current_meal(now)
            else:
                code_map = {"breakfast": "1", "lunch": "2", "dinner": "3"}
                title_map = {
                    "breakfast": "🍳 아침" if day == "today" else "🍳 내일 아침",
                    "lunch": "🍚 점심" if day == "today" else "🍚 내일 점심",
                    "dinner": "🍖 저녁" if day == "today" else "🍖 내일 저녁",
                }
                code = code_map.get(meal_type, "2")
                title_text = title_map.get(meal_type, "급식")
                title, menu, cal_info = await meal_service.get_meal_by_type(
                    date_str, code, title_text
                )

            if title and menu:
                result = f"**{title}**\n{menu}"
                if cal_info:
                    result += f"\n({cal_info})"
                return result
            return "급식 정보를 가져올 수 없습니다."

        return get_meal

    def _make_get_water_temp_tool(self):
        water_service = self.water_service

        @tool
        async def get_water_temp() -> str:
            """한강 수온을 조회합니다."""
            result = await water_service.get_han_river_temp()
            if result:
                hour, minute, temp = result
                return f"🌊 한강 수온: **{temp}°C** (측정 시각: {hour}시 {minute}분)"
            return "한강 수온 정보를 가져올 수 없습니다."

        return get_water_temp

    def _make_get_time_tool(self):
        time_service = self.time_service

        @tool
        def get_time() -> str:
            """현재 시간을 조회합니다."""
            return f"🕐 {time_service.get_current_time()}"

        return get_time

    def _make_get_lol_tier_tool(self):
        lol_service = self.lol_service

        @tool
        async def get_lol_tier(riot_id: str) -> str:
            """롤(League of Legends) 티어를 조회합니다.

            Args:
                riot_id: 라이엇 ID (예: 'Hide on bush#KR1')
            """
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    account = await lol_service.get_account_info(session, riot_id)
                    solo_rank, tier = await lol_service.get_tier_info(session, account["puuid"])
                    if solo_rank:
                        return (
                            f"🎮 **{riot_id}** 롤 랭크\n"
                            f"티어: **{solo_rank['tier']} {solo_rank['rank']}** ({solo_rank['leaguePoints']}LP)\n"
                            f"전적: {solo_rank['wins']}승 {solo_rank['losses']}패"
                        )
                    return f"🎮 **{riot_id}**: {tier}"
            except ValueError as e:
                return str(e)

        return get_lol_tier

    def _make_get_lol_history_tool(self):
        lol_service = self.lol_service

        @tool
        async def get_lol_history(riot_id: str) -> str:
            """롤(League of Legends) 최근 전적을 조회합니다.

            Args:
                riot_id: 라이엇 ID (예: 'Hide on bush#KR1')
            """
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    account = await lol_service.get_account_info(session, riot_id)
                    matches = await lol_service.get_match_history(session, account["puuid"])
                    lines = [f"🎮 **{riot_id}** 최근 전적"]
                    for m in matches:
                        lines.append(f"{m['name']}\n{m['value']}")
                    return "\n".join(lines)
            except ValueError as e:
                return str(e)

        return get_lol_history

    def _make_get_valo_tier_tool(self):
        valo_service = self.valo_service

        @tool
        async def get_valo_tier(riot_id: str) -> str:
            """발로란트(Valorant) 티어를 조회합니다.

            Args:
                riot_id: 라이엇 ID (예: 'Player#KR1')
            """
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    account = await valo_service.get_account_info(session, riot_id)
                    rank_data, tier = await valo_service.get_rank_info(session, account["puuid"])
                    return f"🎯 **{riot_id}** 발로란트 랭크: **{tier}**"
            except ValueError as e:
                return str(e)

        return get_valo_tier

    def _make_get_valo_history_tool(self):
        valo_service = self.valo_service

        @tool
        async def get_valo_history(riot_id: str) -> str:
            """발로란트(Valorant) 최근 전적을 조회합니다.

            Args:
                riot_id: 라이엇 ID (예: 'Player#KR1')
            """
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    account = await valo_service.get_account_info(session, riot_id)
                    matches = await valo_service.get_match_history(session, account["puuid"])
                    lines = [f"🎯 **{riot_id}** 최근 전적"]
                    for m in matches:
                        lines.append(f"{m['name']}\n{m['value']}")
                    return "\n".join(lines)
            except ValueError as e:
                return str(e)

        return get_valo_history

    def _make_get_music_tool(self):
        spotify_service = self.spotify_service

        @tool
        async def get_music() -> str:
            """Spotify에서 랜덤 곡을 추천합니다."""
            playlist_ids = BaseConfig.SPOTIFY_PLAYLIST_ID
            if not playlist_ids:
                return "Spotify 설정이 되어있지 않습니다."
            playlist_id = random.choice(playlist_ids)
            track = await spotify_service.get_random_track(playlist_id)
            if track:
                genres = ", ".join(track["genres"][:2]) if track.get("genres") else ""
                result = f"🎵 **{track['name']}**\n아티스트: {track['artists']}\n앨범: {track['album']}\n길이: {track['duration']}"
                if genres:
                    result += f"\n장르: {genres}"
                result += f"\n{track['url']}"
                return result
            return "곡을 가져오는데 실패했습니다."

        return get_music

    async def process_message(self, user_message: str) -> str:
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ]

            response = await self.llm_with_tools.ainvoke(messages)

            if not response.tool_calls:
                return response.content

            results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                tool_fn = None
                for t in self.tools:
                    if t.name == tool_name:
                        tool_fn = t
                        break

                if tool_fn:
                    result = await tool_fn.ainvoke(tool_args)
                    results.append(str(result))

            return "\n\n".join(results) if results else response.content

        except Exception as e:
            logger.error(f"LangService 처리 중 오류: {e}", exc_info=True)
            return f"처리 중 오류가 발생했습니다: {e}"

    async def ask_question(self, question: str) -> str:
        try:
            messages = [
                SystemMessage(content="너는 친절한 한국어 AI 어시스턴트야. 간결하고 정확하게 답변해."),
                HumanMessage(content=question),
            ]

            response = await self.llm.ainvoke(messages)
            return response.content

        except Exception as e:
            logger.error(f"질문 처리 중 오류: {e}", exc_info=True)
            return f"질문 처리 중 오류가 발생했습니다: {e}"
