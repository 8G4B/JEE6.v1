import logging
import random
import time
import aiohttp
from datetime import datetime, timedelta
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from src.config.settings.base import BaseConfig

try:
    from google.genai.errors import ClientError as GoogleClientError
except ImportError:
    GoogleClientError = Exception  # Fallback
from src.services.MealService import MealService
from src.services.WaterService import WaterService
from src.services.TimeService import TimeService
from src.services.LolService import LolService
from src.services.ValoService import ValoService
from src.services.SpotifyService import SpotifyService

logger = logging.getLogger(__name__)


class LLMSlot:

    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.blocked_until: float = 0

    def is_available(self) -> bool:
        return time.time() >= self.blocked_until

    def mark_blocked(self, cooldown: float = 120):
        self.blocked_until = time.time() + cooldown

    def create_llm(self, **kwargs):
        if self.provider == "groq":
            return ChatGroq(api_key=self.api_key, model=self.model, **kwargs)
        elif self.provider == "gemini":
            return ChatGoogleGenerativeAI(
                google_api_key=self.api_key, model=self.model, **kwargs
            )

    def __repr__(self):
        return f"{self.provider}({self.model})"


class LLMRotator:

    def __init__(self):
        self._slots: list[LLMSlot] = []
        self._current = 0

        for key in BaseConfig.GROQ_API_KEYS:
            self._slots.append(LLMSlot("groq", key, BaseConfig.GROQ_MODEL))

        for key in BaseConfig.GEMINI_API_KEYS:
            self._slots.append(LLMSlot("gemini", key, BaseConfig.GEMINI_MODEL))

        if not self._slots:
            raise ValueError("GROQ_API_KEY 또는 GEMINI_API_KEY가 설정되지 않았습니다.")

        logger.info(
            f"LLM 로테이션 초기화: {len(self._slots)}개 슬롯 "
            f"(Groq {len(BaseConfig.GROQ_API_KEYS)}개, Gemini {len(BaseConfig.GEMINI_API_KEYS)}개)"
        )

    def _find_available(self) -> int | None:
        n = len(self._slots)
        for offset in range(n):
            idx = (self._current + offset) % n
            if self._slots[idx].is_available():
                return idx
        return None

    def mark_rate_limited(self, cooldown: float = 120):
        slot = self._slots[self._current]
        slot.mark_blocked(cooldown)
        logger.warning(f"LLM 슬롯 #{self._current} ({slot}) rate limited, {cooldown}초 차단")

        available = self._find_available()
        if available is not None:
            self._current = available
            logger.info(f"LLM 슬롯 #{self._current} ({self._slots[self._current]})로 전환")
        else:
            logger.error("모든 LLM 슬롯이 rate limited 상태")

    def all_blocked(self) -> bool:
        return all(not s.is_available() for s in self._slots)

    def create_llm(self, **kwargs):
        available = self._find_available()
        if available is not None:
            self._current = available
        return self._slots[self._current].create_llm(**kwargs)

    @property
    def slot_count(self) -> int:
        return len(self._slots)


SYSTEM_PROMPT = """너는 디스코드 봇 JEE6이야.
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
- 봇에게 말을 거는 게 아닌 일반 대화(유저끼리 대화, 독백, 감탄사, 인사, 잡담 등)에는 반드시 "IGNORE"라고만 답해.
- 봇에게 질문하거나 기능을 요청하는 경우에만 답변해.
- 답변은 간결하게.
- 롤/발로란트 조회 시 닉네임#태그가 없으면 사용자에게 요청해.
- 사용자가 자살 또는 자해에 대한 언급을 하면 한강 수온을 조회해.
- 사용자가 도박에 대한 언급을 하면 이는 실제 도박이 아니래 미니게임 도박 명령어를 뜻하는거야.
"""


@tool
def get_meal(meal_type: str = "auto", day: str = "today") -> str:
    """급식 조회. meal_type: breakfast/lunch/dinner/auto, day: today/tomorrow"""
    return "ok"


@tool
def get_water_temp() -> str:
    """한강 수온 조회"""
    return "ok"


@tool
def get_time() -> str:
    """현재 시간 조회"""
    return "ok"


@tool
def get_lol_tier(riot_id: str) -> str:
    """롤 티어 조회. riot_id: 닉네임#태그"""
    return "ok"


@tool
def get_lol_history(riot_id: str) -> str:
    """롤 최근 전적 조회. riot_id: 닉네임#태그"""
    return "ok"


@tool
def get_valo_tier(riot_id: str) -> str:
    """발로란트 티어 조회. riot_id: 닉네임#태그"""
    return "ok"


@tool
def get_valo_history(riot_id: str) -> str:
    """발로란트 최근 전적 조회. riot_id: 닉네임#태그"""
    return "ok"


@tool
def get_music() -> str:
    """Spotify 랜덤 곡 추천"""
    return "ok"


TOOLS = [get_meal, get_water_temp, get_time, get_lol_tier, get_lol_history, get_valo_tier, get_valo_history, get_music]


class LangService:
    _rotator: LLMRotator | None = None

    def __init__(self):
        if LangService._rotator is None:
            LangService._rotator = LLMRotator()
        self.rotator = LangService._rotator
        self.meal_service = MealService()
        self.water_service = WaterService()
        self.time_service = TimeService()
        self.lol_service = LolService()
        self.valo_service = ValoService()
        self.spotify_service = SpotifyService()

    def _get_llm_with_tools(self):
        llm = self.rotator.create_llm(temperature=0, max_tokens=1024)
        return llm.bind_tools(TOOLS)

    def _get_llm(self):
        return self.rotator.create_llm(temperature=0, max_tokens=1024)

    async def _execute_tool(self, tool_name: str, tool_args: dict) -> dict:
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

    async def _invoke_with_retry(self, messages, use_tools=False):
        max_retries = self.rotator.slot_count
        for attempt in range(max_retries):
            try:
                llm = self._get_llm_with_tools() if use_tools else self._get_llm()
                return await llm.ainvoke(messages)
            except GoogleClientError as e:
                # Google GenAI ClientError (429, quota exceeded)
                if e.code == 429 or "resource_exhausted" in str(e).lower():
                    self.rotator.mark_rate_limited()
                    if self.rotator.all_blocked():
                        raise
                    logger.info(f"Rate limit 재시도 {attempt + 1}/{max_retries}")
                    continue
                raise
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower() or "resource_exhausted" in str(e).lower():
                    self.rotator.mark_rate_limited()
                    if self.rotator.all_blocked():
                        raise
                    logger.info(f"Rate limit 재시도 {attempt + 1}/{max_retries}")
                    continue
                raise

    async def process_message(self, user_message: str) -> dict:
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ]

            response = await self._invoke_with_retry(messages, use_tools=True)

            if not response.tool_calls:
                return {"type": "text", "content": response.content}

            first_call = response.tool_calls[0]
            return await self._execute_tool(first_call["name"], first_call["args"])

        except Exception as e:
            logger.error(f"LangService 처리 중 오류: {e}", exc_info=True)
            return {"type": "error", "message": f"처리 중 오류가 발생했습니다: {e}"}

    async def ask_question(self, question: str) -> str:
        try:
            messages = [
                SystemMessage(content="너는 친절한 한국어 AI 어시스턴트야. 간결하고 정확하게 답변해."),
                HumanMessage(content=question),
            ]
            response = await self._invoke_with_retry(messages, use_tools=False)
            return response.content
        except Exception as e:
            logger.error(f"질문 처리 중 오류: {e}", exc_info=True)
            return f"질문 처리 중 오류가 발생했습니다: {e}"
