from dotenv import load_dotenv
import os

load_dotenv()

RIOT_API_KEY = os.getenv("RIOT_API_KEY", "RIOT-API-KEY-NEEDED")

LOL_BASE_URL = "https://kr.api.riotgames.com"
LOL_ASIA_URL = "https://asia.api.riotgames.com"

VALO_ASIA_URL = "https://asia.api.riotgames.com"
VALO_AP_URL = "https://ap.api.riotgames.com"

LOL_GAME_MODES = {
    "CLASSIC": "소환사의 협곡",
    "ARAM": "칼바람 나락",
    "URF": "우르프",
    "ARURF": "무작위 우르프",
    "ONEFORALL": "단일 챔피언",
    "TUTORIAL": "튜토리얼",
    "PRACTICETOOL": "연습",
    "NEXUSBLITZ": "넥서스 돌격",
    "ULTBOOK": "궁극기 주문서",
}

RIOT_HEADERS = {
    "X-Riot-Token": RIOT_API_KEY,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://developer.riotgames.com",
}
