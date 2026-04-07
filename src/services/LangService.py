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

[급식]
1. get_meal — 급식 조회
   - meal_type: "breakfast" | "lunch" | "dinner" | "auto" (기본값: "auto")
   - day: "today" | "tomorrow" (기본값: "today")

[정보]
2. get_water_temp — 한강 수온 조회 (파라미터 없음)
3. get_time — 현재 시간 조회 (파라미터 없음)
4. get_info — 봇 정보/상태 조회 (파라미터 없음)

[게임 전적]
5. get_lol_tier — 롤 티어 조회 (riot_id: "닉네임#태그" 필수)
6. get_lol_history — 롤 최근 전적 조회 (riot_id: "닉네임#태그" 필수)
7. get_lol_rotation — 롤 금주 무료 챔피언 로테이션 조회 (파라미터 없음)
8. get_valo_tier — 발로란트 티어 조회 (riot_id: "닉네임#태그" 필수)
9. get_valo_history — 발로란트 최근 전적 조회 (riot_id: "닉네임#태그" 필수)

[음악]
10. get_music — Spotify 랜덤 곡 추천 (파라미터 없음)

[도박]
11. get_balance — 내 잔액 조회 (파라미터 없음)
12. get_ranking — 도박 랭킹 TOP 10 조회 (파라미터 없음)
13. do_work — 노동으로 돈 벌기 (파라미터 없음)
14. get_jackpot — 현재 잭팟 금액 조회 (파라미터 없음)

[플러딩]
15. get_flooding_music — 오늘의 기상 음악 목록 조회 (파라미터 없음)
16. get_flooding_profile — 플러딩 내 정보 조회 (파라미터 없음)
"""

FEW_SHOT_EXAMPLES = """
예시:

유저: 오늘 급식 뭐야?
응답: {"tool": "get_meal", "args": {"meal_type": "auto", "day": "today"}}

유저: 내일 점심 알려줘
응답: {"tool": "get_meal", "args": {"meal_type": "lunch", "day": "tomorrow"}}

유저: 한강 수온
응답: {"tool": "get_water_temp", "args": {}}

유저: 지금 몇시야
응답: {"tool": "get_time", "args": {}}

유저: Hide on bush#KR1 롤 티어
응답: {"tool": "get_lol_tier", "args": {"riot_id": "Hide on bush#KR1"}}

유저: Hide on bush#KR1 전적
응답: {"tool": "get_lol_history", "args": {"riot_id": "Hide on bush#KR1"}}

유저: 롤 티어 알려줘
응답: {"reply": "닉네임#태그를 알려주세요! 예: Hide on bush#KR1"}

유저: 이번주 무료 챔피언 뭐야
응답: {"tool": "get_lol_rotation", "args": {}}

유저: 노래 추천해줘
응답: {"tool": "get_music", "args": {}}

유저: 내 돈 얼마야
응답: {"tool": "get_balance", "args": {}}

유저: 랭킹 보여줘
응답: {"tool": "get_ranking", "args": {}}

유저: 돈 벌고 싶어
응답: {"tool": "do_work", "args": {}}

유저: 일하기
응답: {"tool": "do_work", "args": {}}

유저: 잭팟 얼마야
응답: {"tool": "get_jackpot", "args": {}}

유저: 기상음악 뭐야
응답: {"tool": "get_flooding_music", "args": {}}

유저: 죽고싶다
응답: {"tool": "get_water_temp", "args": {}}

유저: ㅋㅋㅋㅋㅋㅋ
응답: {"ignore": true}

유저: 아 배고프다
응답: {"ignore": true}

유저: ㄹㅇㅋㅋ 그거 개웃기네
응답: {"ignore": true}

유저: gg
응답: {"ignore": true}

유저: 야 너 뭐할 수 있어?
응답: {"reply": "급식 조회, 한강 수온, 롤/발로 전적, 음악 추천, 도박 잔액/랭킹/노동, 시간 조회 등을 할 수 있어!"}

유저: 봇 상태 어때
응답: {"tool": "get_info", "args": {}}
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
- 대부분의 메시지는 유저끼리 대화이므로 ignore가 기본이다.
- 봇에게 직접 기능을 요청하는 경우에만 도구를 호출하거나 reply해.
- 롤/발로란트 조회 시 닉네임#태그가 없으면 reply로 요청해.
- 자살/자해 언급 시 get_water_temp를 호출해.
- 도박 관련 언급은 미니게임 도박 명령어를 뜻한다.
- "돈 벌기", "일하기", "노동" 등은 do_work를 호출해.

{FEW_SHOT_EXAMPLES}"""


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
        self._flooding_api_service = None
        self._flooding_auth_service = None

        logger.info(f"LangService 초기화: vLLM {BaseConfig.VLLM_BASE_URL}")

    def set_gambling_service(self, gambling_service):
        self._gambling_service = gambling_service

    def set_flooding_services(self, api_service, auth_service):
        self._flooding_api_service = api_service
        self._flooding_auth_service = auth_service

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
            executors = {
                "get_meal": lambda: self._exec_meal(tool_args),
                "get_water_temp": lambda: self._exec_water(),
                "get_time": lambda: self._exec_time(),
                "get_info": lambda: self._exec_info(context),
                "get_lol_tier": lambda: self._exec_lol_tier(tool_args),
                "get_lol_history": lambda: self._exec_lol_history(tool_args),
                "get_lol_rotation": lambda: self._exec_lol_rotation(),
                "get_valo_tier": lambda: self._exec_valo_tier(tool_args),
                "get_valo_history": lambda: self._exec_valo_history(tool_args),
                "get_music": lambda: self._exec_music(),
                "get_balance": lambda: self._exec_balance(context),
                "get_ranking": lambda: self._exec_ranking(context),
                "do_work": lambda: self._exec_work(context),
                "get_jackpot": lambda: self._exec_jackpot(context),
                "get_flooding_music": lambda: self._exec_flooding_music(context),
                "get_flooding_profile": lambda: self._exec_flooding_profile(context),
            }

            executor = executors.get(tool_name)
            if not executor:
                return {"type": "text", "content": "알 수 없는 명령입니다."}

            result = executor()
            if hasattr(result, "__await__"):
                return await result
            return result

        except Exception as e:
            logger.error(f"Tool 실행 오류 ({tool_name}): {e}", exc_info=True)
            return {"type": "error", "message": str(e)}

    # --- 급식 ---

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

    # --- 정보 ---

    async def _exec_water(self) -> dict:
        result = await self.water_service.get_han_river_temp()
        if result:
            hour, minute, temp = result
            return {"type": "water", "hour": hour, "minute": minute, "temp": temp}
        return {"type": "error", "message": "한강 수온 정보를 가져올 수 없습니다."}

    def _exec_time(self) -> dict:
        dt = self.time_service.get_current_datetime()
        return {"type": "time", "datetime": dt}

    def _exec_info(self, context: dict) -> dict:
        bot = context.get("bot") if context else None
        latency = round(bot.latency * 1000) if bot else 0
        guild_count = len(bot.guilds) if bot else 0
        return {
            "type": "info",
            "latency": latency,
            "guild_count": guild_count,
        }

    # --- 게임 전적 ---

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

    async def _exec_lol_rotation(self) -> dict:
        async with aiohttp.ClientSession() as session:
            rotation = await self.lol_service.get_rotation(session)
            return {"type": "lol_rotation", "champions": rotation}

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

    # --- 음악 ---

    async def _exec_music(self) -> dict:
        playlist_ids = BaseConfig.SPOTIFY_PLAYLIST_ID
        if not playlist_ids:
            return {"type": "error", "message": "Spotify 설정이 되어있지 않습니다."}
        playlist_id = random.choice(playlist_ids)
        track = await self.spotify_service.get_random_track(playlist_id)
        if track:
            return {"type": "music", "track": track}
        return {"type": "error", "message": "곡을 가져오는데 실패했습니다."}

    # --- 도박 ---

    def _get_gambling(self):
        if not self._gambling_service:
            return None
        return self._gambling_service

    def _exec_balance(self, context: dict) -> dict:
        gs = self._get_gambling()
        if not gs or not context:
            return {"type": "error", "message": "도박 기능을 사용할 수 없습니다."}
        user_id = context.get("user_id")
        server_id = context.get("server_id")
        balance = gs.get_balance(user_id, server_id)
        return {
            "type": "balance",
            "balance": balance,
            "author_name": context.get("author_name", "유저"),
        }

    async def _exec_ranking(self, context: dict) -> dict:
        gs = self._get_gambling()
        if not gs or not context:
            return {"type": "error", "message": "도박 기능을 사용할 수 없습니다."}
        rankings = await gs.get_cached_rankings(context["server_id"], context["bot"])
        return {"type": "ranking", "rankings": rankings}

    def _exec_work(self, context: dict) -> dict:
        gs = self._get_gambling()
        if not gs or not context:
            return {"type": "error", "message": "도박 기능을 사용할 수 없습니다."}
        user_id = context["user_id"]
        server_id = context["server_id"]

        remaining = gs.check_cooldown(user_id, "work")
        if remaining:
            return {"type": "cooldown", "remaining": remaining}

        from src.config.settings.gamblingSettings import GamblingSettings
        import secrets
        reward = secrets.randbelow(
            GamblingSettings.WORK_REWARD_RANGE[1] - GamblingSettings.WORK_REWARD_RANGE[0] + 1
        ) + GamblingSettings.WORK_REWARD_RANGE[0]

        gs.add_balance(user_id, server_id, reward)
        gs.set_cooldown(user_id, "work")
        balance = gs.get_balance(user_id, server_id)

        return {
            "type": "work",
            "reward": reward,
            "balance": balance,
            "author_name": context.get("author_name", "유저"),
        }

    def _exec_jackpot(self, context: dict) -> dict:
        gs = self._get_gambling()
        if not gs or not context:
            return {"type": "error", "message": "도박 기능을 사용할 수 없습니다."}
        amount = gs.get_jackpot(context["server_id"])
        return {"type": "jackpot", "amount": amount}

    # --- 플러딩 ---

    async def _exec_flooding_music(self, context: dict) -> dict:
        if not self._flooding_api_service or not context:
            return {"type": "error", "message": "플러딩 서비스를 사용할 수 없습니다."}
        try:
            result = await self._flooding_api_service.get_music_list(
                context["user_id"]
            )
            return {"type": "flooding_music", "data": result}
        except Exception as e:
            return {"type": "error", "message": f"플러딩 음악 조회 실패: {e}"}

    async def _exec_flooding_profile(self, context: dict) -> dict:
        if not self._flooding_api_service or not context:
            return {"type": "error", "message": "플러딩 서비스를 사용할 수 없습니다."}
        try:
            result = await self._flooding_api_service.get_user_status(
                context["user_id"]
            )
            return {"type": "flooding_profile", "data": result}
        except Exception as e:
            return {"type": "error", "message": f"플러딩 프로필 조회 실패: {e}"}

    # --- 메인 처리 ---

    async def process_message(self, user_message: str, context: dict = None) -> dict:
        """자연어 메시지를 처리. None 반환 시 IGNORE."""
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
