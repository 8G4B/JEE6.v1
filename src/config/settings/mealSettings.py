from datetime import timedelta
from dotenv import load_dotenv
import os

BASE_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

load_dotenv()
MEAL_API_KEY = os.getenv("MEAL_API_KEY")

ATPT_OFCDC_SC_CODE = "F10"
SD_SCHUL_CODE = "7380292"

NO_MEAL = "급식이 없습니다."

MEAL_TIMES = [
    ((lambda h, m: h < 7 or (h == 7 and m < 30)), "1", "🍳 아침"),
    ((lambda h, m: h < 12 or (h == 12 and m < 30)), "2", "🍚 점심"),
    ((lambda h, m: h < 18 or (h == 18 and m < 30)), "3", "🍖 저녁"),
]

CACHE_DURATION = timedelta(hours=6)
