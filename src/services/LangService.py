import json
import logging
import random
import re
import aiohttp
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config.settings.base import BaseConfig
from src.services.MealService import MealService
from src.services.WaterService import WaterService
from src.services.TimeService import TimeService
from src.services.LolService import LolService
from src.services.ValoService import ValoService
from src.services.SpotifyService import SpotifyService

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = """
사용 가능한 도구 목록:

1. get_meal
   - 설명: 급식 조회
   - 파라미터:
     - meal_type: "breakfast" | "lunch" | "dinner" | "auto" (기본값: "auto")
     - day: "today" | "tomorrow" (기본값: "today")

2. get_water_temp
   - 설명: 한강 수온 조회
   - 파라미터: 없음

3. get_time
   - 설명: 현재 시간 조회
   - 파라미터: 없음

4. get_lol_tier
   - 설명: 롤(League of Legends) 티어 조회
   - 파라미터:
     - riot_id: "닉네임#태그" (필수)

5. get_lol_history
   - 설명: 롤 최근 전적 조회
   - 파라미터:
     - riot_id: "닉네임#태그" (필수)

6. get_valo_tier
   - 설명: 발로란트 티어 조회
   - 파라미터:
     - riot_id: "닉네임#태그" (필수)

7. get_valo_history
   - 설명: 발로란트 최근 전적 조회
   - 파라미터:
     - riot_id: "닉네임#태그" (필수)

8. get_music
   - 설명: Spotify 랜덤 곡 추천
   - 파라미터: 없음

9. get_balance
   - 설명: 도박 잔액 조회
   - 파라미터: 없음
   - 참고: 유저의 현재 잔액을 알려줌

10. get_ranking
    - 설명: 도박 랭킹 조회
    - 파라미터: 없음
"""

SYSTEM_PROMPT = f"""너는 디스코드 봇 JEE6이야.
사용자의 자연어 메시지를 분석해서 적절한 도구를 호출해야 해.

{TOOL_DEFINITIONS}

반드시 아래 JSON 형식으로만 응답해:

도구를 호출할 경우:
{{"tool": "도구이름", "args": {{"파라미터": "값"}}}}

일반 대화 응답인 경우 (봇에게 직접 말을 건 경우):
{{"reply": "응답 내용"}}

봇에게 말을 건 게 아닌 경우 (유저끼리 대화, 독백, 감탄사, 잡담 등):
{{"ignore": true}}

규칙:
- 반드시 위 JSON 형식 중 하나로만 응답해. 다른 텍스트는 절대 포함하지 마.
- 봇에게 말을 거는 게 아닌 일반 대화에는 반드시 ignore로 응답해.
- 롤/발로란트 조회 시 닉네임#태그가 없으면 reply로 요청해.
- 자살/자해 언급 시 get_water_temp를 호출해.
- 도박 언급은 실제 도박이 아니라 미니게임 도박 명령어를 뜻하는 거야.
"""


class LangService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=BaseConfig.VLLM_MODEL,
            api_key="not-needed",
            base_url=BaseConfig.VLLM_BASE_URL,
            temperature=0,
            max_tokens=512,
        )

        self.meal_service = MealService()
        self.water_service = WaterService()
        self.time_service = TimeService()
        self.lol_service = LolService()
        self.valo_service = ValoService()
        self.spotify_service = SpotifyService()

        self._gambling_service = None

        logger.info(f"LangService 초기화: vLLM {BaseConfig.VLLM_BASE_URL}")

    def set_gambling_service(self, gambling_service):
        self._gambling_service = gambling_service

    def _parse_llm_response(self, text: str) -> dict:
        text = text.strip()

        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
        if not json_match:
            logger.warning(f"JSON 파싱 실패, 원문: {text[:200]}")
            return {"ignore": True}

        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning(f"JSON 디코딩 실패: {json_match.group()[:200]}")
            return {"ignore": True}

    async def _execute_tool(self, tool_name: str, tool_args: dict, context: dict = None) -> dict:
        try:
            if tool_name == "get_meal":
                return await self._exec_meal(tool_args)
            elif tool_name == "get_water_temp":
                return await self._exec_water()
            elif tool_name == "get_time":
                return self._exec_time()
            elif tool_name == "get_lol_tier":
                return await self._exec_lol_tier(tool_args)
            elif tool_name == "get_lol_history":
                return await self._exec_lol_history(tool_args)
            elif tool_name == "get_valo_tier":
                return await self._exec_valo_tier(tool_args)
            elif tool_name == "get_valo_history":
                return await self._exec_valo_history(tool_args)
            elif tool_name == "get_music":
                return await self._exec_music()
            elif tool_name == "get_balance":
                return self._exec_balance(context)
            elif tool_name == "get_ranking":
                return await self._exec_ranking(context)
        except Exception as e:
            logger.error(f"Tool 실행 오류 ({tool_name}): {e}", exc_info=True)
            return {"type": "error", "message": str(e)}

        return {"type": "text", "content": "알 수 없는 명령입니다."}

    async def _exec_meal(self, args: dict) -> dict:
        meal_type = args.get("meal_type", "auto")
        day = args.get("day", "today")
        now = datetime.now()

        if meal_type == "auto":
            title, menu, cal_info = await self.meal_service.get_current_meal(now)
        else:
            if day == "tomorrow":
                date_str = (now + timedelta(days=1)).strftime("%Y%m%d")
            else:
                date_str = now.strftime("%Y%m%d")
            code_map = {"breakfast": "1", "lunch": "2", "dinner": "3"}
            title_map = {
                "breakfast": "🍳 아침" if day == "today" else "🍳 내일 아침",
                "lunch": "🍚 점심" if day == "today" else "🍚 내일 점심",
                "dinner": "🍖 저녁" if day == "today" else "🍖 내일 저녁",
            }
            title, menu, cal_info = await self.meal_service.get_meal_by_type(
                date_str, code_map.get(meal_type, "2"), title_map.get(meal_type, "급식")
            )

        if title and menu:
            return {"type": "meal", "title": title, "menu": menu, "cal_info": cal_info or ""}
        return {"type": "error", "message": "급식 정보를 가져올 수 없습니다."}

    async def _exec_water(self) -> dict:
        result = await self.water_service.get_han_river_temp()
        if result:
            hour, minute, temp = result
            return {"type": "water", "hour": hour, "minute": minute, "temp": temp}
        return {"type": "error", "message": "한강 수온 정보를 가져올 수 없습니다."}

    def _exec_time(self) -> dict:
        dt = self.time_service.get_current_datetime()
        return {"type": "time", "datetime": dt}

    async def _exec_lol_tier(self, args: dict) -> dict:
        riot_id = args.get("riot_id", "")
        async with aiohttp.ClientSession() as session:
            account = await self.lol_service.get_account_info(session, riot_id)
            solo_rank, tier = await self.lol_service.get_tier_info(session, account["puuid"])
            return {
                "type": "lol_tier",
                "riot_id": riot_id,
                "solo_rank": solo_rank,
                "tier": tier,
            }

    async def _exec_lol_history(self, args: dict) -> dict:
        riot_id = args.get("riot_id", "")
        async with aiohttp.ClientSession() as session:
            account = await self.lol_service.get_account_info(session, riot_id)
            matches = await self.lol_service.get_match_history(session, account["puuid"])
            return {"type": "lol_history", "riot_id": riot_id, "matches": matches}

    async def _exec_valo_tier(self, args: dict) -> dict:
        riot_id = args.get("riot_id", "")
        async with aiohttp.ClientSession() as session:
            account = await self.valo_service.get_account_info(session, riot_id)
            rank_data, tier = await self.valo_service.get_rank_info(session, account["puuid"])
            return {"type": "valo_tier", "riot_id": riot_id, "tier": tier}

    async def _exec_valo_history(self, args: dict) -> dict:
        riot_id = args.get("riot_id", "")
        async with aiohttp.ClientSession() as session:
            account = await self.valo_service.get_account_info(session, riot_id)
            matches = await self.valo_service.get_match_history(session, account["puuid"])
            return {"type": "valo_history", "riot_id": riot_id, "matches": matches}

    async def _exec_music(self) -> dict:
        playlist_ids = BaseConfig.SPOTIFY_PLAYLIST_ID
        if not playlist_ids:
            return {"type": "error", "message": "Spotify 설정이 되어있지 않습니다."}
        playlist_id = random.choice(playlist_ids)
        track = await self.spotify_service.get_random_track(playlist_id)
        if track:
            return {"type": "music", "track": track}
        return {"type": "error", "message": "곡을 가져오는데 실패했습니다."}

    def _exec_balance(self, context: dict) -> dict:
        if not self._gambling_service or not context:
            return {"type": "error", "message": "도박 기능을 사용할 수 없습니다."}
        user_id = context.get("user_id")
        server_id = context.get("server_id")
        if not user_id or not server_id:
            return {"type": "error", "message": "유저 정보를 확인할 수 없습니다."}
        balance = self._gambling_service.get_balance(user_id, server_id)
        return {
            "type": "balance",
            "balance": balance,
            "user_id": user_id,
            "author_name": context.get("author_name", "유저"),
        }

    async def _exec_ranking(self, context: dict) -> dict:
        if not self._gambling_service or not context:
            return {"type": "error", "message": "도박 기능을 사용할 수 없습니다."}
        server_id = context.get("server_id")
        bot = context.get("bot")
        if not server_id or not bot:
            return {"type": "error", "message": "서버 정보를 확인할 수 없습니다."}
        rankings = await self._gambling_service.get_cached_rankings(server_id, bot)
        return {"type": "ranking", "rankings": rankings}

    async def process_message(self, user_message: str, context: dict = None) -> dict:
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ]

            response = await self.llm.ainvoke(messages)
            parsed = self._parse_llm_response(response.content)

            if parsed.get("ignore"):
                return None

            if "reply" in parsed:
                return {"type": "text", "content": parsed["reply"]}

            if "tool" in parsed:
                tool_name = parsed["tool"]
                tool_args = parsed.get("args", {})
                return await self._execute_tool(tool_name, tool_args, context)

            return None

        except Exception as e:
            logger.error(f"LangService 처리 중 오류: {e}", exc_info=True)
            return {"type": "error", "message": f"처리 중 오류가 발생했습니다: {e}"}

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
