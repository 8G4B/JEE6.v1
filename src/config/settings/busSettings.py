import os
from datetime import timedelta

# BIS API 설정
BIS_API_KEY = os.getenv("BIS_API_KEY")
BIS_BASE_URL = "http://api.gwangju.go.kr/json/arriveInfo"

NODE_ID = "5254"

CACHE_DURATION = timedelta(minutes=1)

# 오류 메시지
NO_BUS_INFO = "🚌 현재 도착 예정인 버스가 없습니다."
API_ERROR = "❌ 버스 도착 정보를 가져올 수 없습니다."
