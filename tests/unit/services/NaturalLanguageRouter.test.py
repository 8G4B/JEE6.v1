import pytest

from src.services.NaturalLanguageRouter import route_fast


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "오늘 급식 뭐야?",
            {
                "tool": "get_meal",
                "args": {"meal_type": "auto", "day": "today"},
            },
        ),
        (
            "내일 점심 알려줘",
            {
                "tool": "get_meal",
                "args": {"meal_type": "lunch", "day": "tomorrow"},
            },
        ),
        ("한강 수온 알려줘", {"tool": "get_water_temp", "args": {}}),
        ("지금 몇 시야?", {"tool": "get_time", "args": {}}),
        ("노래 추천해줘", {"tool": "get_music", "args": {}}),
        ("오늘 기상 음악 뭐야", {"tool": "get_flooding_music", "args": {}}),
        ("봇 상태 알려줘", {"tool": "get_info", "args": {}}),
        ("죽고 싶다", {"tool": "get_water_temp", "args": {}}),
    ],
)
def test_route_fast_explicit_intents(message, expected):
    assert route_fast(message) == expected


@pytest.mark.parametrize(
    "message",
    [
        "아 배고프다",
        "밥 먹었어?",
        "ㅋㅋㅋㅋㅋㅋ",
        "롤 티어 알려줘",
        "그 음악 좋더라",
    ],
)
def test_route_fast_leaves_ambiguous_messages_for_llm(message):
    assert route_fast(message) is None
