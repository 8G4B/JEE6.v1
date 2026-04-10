import json
import logging
import re
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config.settings.base import BaseConfig
from src.clients.ApiGatewayClient import ApiGatewayClient

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

[음악]
5. get_music — Spotify 랜덤 곡 추천 (파라미터 없음)

[플러딩]
6. get_flooding_music — 오늘의 기상 음악 목록 조회 (파라미터 없음)
7. get_flooding_profile — 플러딩 내 정보 조회 (파라미터 없음)
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

유저: 롤 티어 알려줘
응답: {"ignore": true}

유저: 발로 전적 보여줘
응답: {"ignore": true}

유저: 노래 추천해줘
응답: {"tool": "get_music", "args": {}}

유저: 돈 얼마야
응답: {"ignore": true}

유저: 도박하자
응답: {"ignore": true}

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
- 자살/자해 언급 시 get_water_temp를 호출해.
- 롤, 발로란트, 도박 관련 요청은 ignore해. 이 기능들은 !명령어로만 사용 가능하다.

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

        self.api = ApiGatewayClient()

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
                "get_lol_rotation": lambda: self._exec_lol_rotation(),
                "get_music": lambda: self._exec_music(),
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

    async def _exec_meal(self, args: dict) -> dict:
        meal_type = args.get("meal_type", "auto")
        day = args.get("day", "today")
        data = await self.api.get_meal(meal_type=meal_type, day=day)
        if data.get("error"):
            return {"type": "error", "message": data["error"]}
        if data.get("menu"):
            return {"type": "meal", "title": data["title"], "menu": data["menu"], "cal_info": data.get("cal_info", "")}
        return {"type": "error", "message": "급식 정보를 가져올 수 없습니다."}

    async def _exec_water(self) -> dict:
        data = await self.api.get_water_temp()
        if data.get("error"):
            return {"type": "error", "message": data["error"]}
        return {"type": "water", "hour": data["hour"], "minute": data["minute"], "temp": data["temp"]}

    async def _exec_time(self) -> dict:
        data = await self.api.get_time()
        return {"type": "time", "datetime": data.get("korean", datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분 %S초"))}

    def _exec_info(self, context: dict) -> dict:
        bot = context.get("bot") if context else None
        latency = round(bot.latency * 1000) if bot else 0
        guild_count = len(bot.guilds) if bot else 0
        return {
            "type": "info",
            "latency": latency,
            "guild_count": guild_count,
        }

    async def _exec_lol_tier(self, args: dict) -> dict:
        riot_id = args.get("riot_id", "")
        data = await self.api.get_lol_tier(riot_id)
        if data.get("error"):
            return {"type": "error", "message": data["error"]}
        return {
            "type": "lol_tier",
            "riot_id": riot_id,
            "solo_rank": data.get("solo_rank"),
            "tier": data.get("tier", "UNRANKED"),
        }

    async def _exec_lol_history(self, args: dict) -> dict:
        riot_id = args.get("riot_id", "")
        data = await self.api.get_lol_history(riot_id)
        if data.get("error"):
            return {"type": "error", "message": data["error"]}
        return {"type": "lol_history", "riot_id": riot_id, "matches": data.get("matches", [])}

    async def _exec_lol_rotation(self) -> dict:
        data = await self.api.get_lol_rotation()
        if data.get("error"):
            return {"type": "error", "message": data["error"]}
        return {"type": "lol_rotation", "champions": data.get("champions", [])}

    async def _exec_valo_tier(self, args: dict) -> dict:
        riot_id = args.get("riot_id", "")
        data = await self.api.get_valo_tier(riot_id)
        if data.get("error"):
            return {"type": "error", "message": data["error"]}
        return {"type": "valo_tier", "riot_id": riot_id, "tier": data.get("tier", "UNRANKED")}

    async def _exec_valo_history(self, args: dict) -> dict:
        riot_id = args.get("riot_id", "")
        data = await self.api.get_valo_history(riot_id)
        if data.get("error"):
            return {"type": "error", "message": data["error"]}
        return {"type": "valo_history", "riot_id": riot_id, "matches": data.get("matches", [])}

    async def _exec_music(self) -> dict:
        data = await self.api.get_random_track()
        if data.get("error"):
            return {"type": "error", "message": data["error"]}
        return {"type": "music", "track": data}

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

    def _save_feedback(self, context: dict, user_message: str,
                       llm_raw: str, parsed: dict, result: dict = None,
                       tool_error: str = None, signal: str = None,
                       signal_detail: str = None):
        try:
            from src.infrastructure.database.Session import get_db_session
            from src.domain.models.LangFeedback import LangFeedback

            if parsed.get("ignore"):
                action = "ignore"
            elif "reply" in parsed:
                action = "reply"
            elif "tool" in parsed:
                action = "tool"
            else:
                action = "parse_error"

            tool_name = parsed.get("tool")
            tool_args_str = json.dumps(parsed.get("args", {}), ensure_ascii=False) if tool_name else None

            tool_success = None
            result_type = None
            if result is not None:
                result_type = result.get("type")
                tool_success = result_type != "error"
            elif tool_error:
                tool_success = False

            feedback = LangFeedback(
                guild_id=context.get("server_id", 0),
                channel_id=context.get("channel_id", 0),
                user_id=context.get("user_id", 0),
                user_message=user_message[:2000],
                llm_raw_response=llm_raw[:2000] if llm_raw else None,
                parsed_action=action,
                tool_name=tool_name,
                tool_args=tool_args_str,
                tool_success=tool_success,
                tool_error=str(tool_error)[:500] if tool_error else None,
                result_type=result_type,
                signal=signal,
                signal_detail=signal_detail,
            )

            with get_db_session() as db:
                db.add(feedback)

        except Exception as e:
            logger.warning(f"피드백 저장 실패: {e}")

    async def process_message(self, user_message: str, context: dict = None) -> dict:
        llm_raw = None
        parsed = {}

        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ]

            response = await self.llm.ainvoke(messages)
            llm_raw = response.content
            parsed = self._parse_llm_response(llm_raw)

            if parsed.get("ignore"):
                self._save_feedback(context or {}, user_message, llm_raw, parsed)
                return None

            if "reply" in parsed:
                result = {"type": "text", "content": parsed["reply"]}
                self._save_feedback(context or {}, user_message, llm_raw, parsed, result)
                return result

            if "tool" in parsed:
                tool_name = parsed["tool"]
                tool_args = parsed.get("args", {})
                try:
                    result = await self._execute_tool(tool_name, tool_args, context)
                    self._save_feedback(context or {}, user_message, llm_raw, parsed, result)
                    return result
                except Exception as e:
                    self._save_feedback(context or {}, user_message, llm_raw, parsed, tool_error=str(e))
                    raise

            self._save_feedback(context or {}, user_message, llm_raw, parsed)
            return None

        except Exception as e:
            logger.error(f"LangService 처리 중 오류: {e}", exc_info=True)
            self._save_feedback(context or {}, user_message, llm_raw, parsed, tool_error=str(e))
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
