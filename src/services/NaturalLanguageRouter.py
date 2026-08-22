import re


_SELF_HARM = re.compile(r"(죽고\s*싶|자살|자해)")
_MEAL = re.compile(
    r"(급식|조식|중식|석식|(?:아침|점심|저녁).{0,8}(?:뭐|메뉴|알려|조회)|"
    r"밥.{0,8}(?:뭐|메뉴|알려|조회))"
)
_WATER = re.compile(r"(한강.{0,8}(?:수온|온도)|(?:수온|온도).{0,8}한강)")
_TIME = re.compile(r"(몇\s*시|현재\s*시간|지금\s*시간)")
_FLOODING_MUSIC = re.compile(r"(기상\s*음악|날씨\s*음악)")
_MUSIC = re.compile(r"(?:노래|음악).{0,8}(?:추천|골라|틀어)")
_INFO = re.compile(r"(?:봇|jee6).{0,12}(?:상태|정보|뭐.{0,4}할\s*수)")


def route_fast(user_message: str) -> dict | None:
    """Route explicit, low-ambiguity intents without invoking the LLM."""
    text = " ".join(user_message.casefold().split())

    if _SELF_HARM.search(text) or _WATER.search(text):
        return {"tool": "get_water_temp", "args": {}}

    if _MEAL.search(text):
        if "조식" in text or "아침" in text:
            meal_type = "breakfast"
        elif "중식" in text or "점심" in text:
            meal_type = "lunch"
        elif "석식" in text or "저녁" in text:
            meal_type = "dinner"
        else:
            meal_type = "auto"
        return {
            "tool": "get_meal",
            "args": {
                "meal_type": meal_type,
                "day": "tomorrow" if "내일" in text else "today",
            },
        }

    if _TIME.search(text):
        return {"tool": "get_time", "args": {}}

    if _FLOODING_MUSIC.search(text):
        return {"tool": "get_flooding_music", "args": {}}

    if _MUSIC.search(text):
        return {"tool": "get_music", "args": {}}

    if _INFO.search(text):
        return {"tool": "get_info", "args": {}}

    return None
