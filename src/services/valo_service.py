import logging
import aiohttp
import time
from typing import Dict, List, Tuple, Optional
from src.config.settings.riot_settings import (
    RIOT_API_KEY, VALO_ASIA_URL, VALO_AP_URL, RIOT_HEADERS
)

logger = logging.getLogger(__name__)

class ValoService:
    """발로란트 게임 정보를 가져오는 서비스 클래스"""
    
    def __init__(self):
        """발로란트 서비스 초기화"""
        self.headers = RIOT_HEADERS
        self.asia_url = VALO_ASIA_URL
        self.val_url = VALO_AP_URL
        
        # 캐시 저장소
        self.account_cache = {}
        self.match_cache = {}
        self.cache_timeout = 600  # 10분 캐시 만료
    
    async def get_account_info(self, session: aiohttp.ClientSession, riot_id: str) -> Dict:
        """라이엇 ID로 계정 정보를 가져옵니다"""
        logger.info(f"발로란트 계정 정보 요청: {riot_id}")
        
        # 캐시 확인
        if riot_id in self.account_cache:
            cache_time, cached_data = self.account_cache[riot_id]
            if time.time() - cache_time < self.cache_timeout:
                logger.debug(f"발로란트 계정 정보 캐시 사용: {riot_id}")
                return cached_data
        
        # 형식 확인
        if '#' not in riot_id:
            error_msg = "닉넴#태그 형식으로 입력하세요"
            logger.warning(f"잘못된 라이엇 ID 형식: {riot_id}, {error_msg}")
            raise ValueError(error_msg)
            
        game_name, tag_line = riot_id.split('#')
        account_url = f"{self.asia_url}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        
        try:
            async with session.get(account_url, headers=self.headers) as response:
                if response.status != 200:
                    error_msg = f"계정을 찾을 수 없습니다. (상태 코드: {response.status})"
                    logger.warning(f"계정 정보 요청 실패: {error_msg}")
                    raise ValueError(error_msg)
                
                account_data = await response.json()
                self.account_cache[riot_id] = (time.time(), account_data)
                logger.debug(f"계정 정보 요청 성공: {game_name}#{tag_line}")
                return account_data
        except aiohttp.ClientError as e:
            logger.error(f"계정 정보 요청 중 네트워크 오류: {e}")
            raise ValueError(f"네트워크 오류: {e}")
    
    async def get_match_history(self, session: aiohttp.ClientSession, puuid: str) -> List[Dict]:
        """플레이어의 최근 5게임 전적을 가져옵니다"""
        logger.info(f"발로란트 전적 정보 요청: {puuid}")
        
        try:
            # 매치 내역 가져오기
            matches_url = f"{self.val_url}/val/match/v1/matchlists/by-puuid/{puuid}"
            async with session.get(matches_url, headers=self.headers) as response:
                if response.status != 200:
                    logger.warning(f"발로란트 매치 내역 요청 실패: {response.status}")
                    raise ValueError(f"매치 내역을 가져올 수 없습니다. (상태 코드: {response.status})")
                
                matches_data = await response.json()
                if 'history' not in matches_data or not matches_data['history']:
                    logger.warning(f"발로란트 매치 내역 없음: {puuid}")
                    raise ValueError("최근 게임 기록이 없습니다.")
            
            # 최대 5개 매치 정보 가져오기
            formatted_matches = []
            for match in matches_data['history'][:5]:
                match_id = match['matchId']
                
                # 매치 상세 정보 가져오기
                match_detail_url = f"{self.val_url}/val/match/v1/matches/{match_id}"
                async with session.get(match_detail_url, headers=self.headers) as response:
                    if response.status != 200:
                        logger.warning(f"발로란트 매치 상세 정보 요청 실패: {match_id}, {response.status}")
                        continue
                    
                    match_data = await response.json()
                    
                    # 현재 플레이어 정보 찾기
                    player = next(p for p in match_data['players'] if p['puuid'] == puuid)
                    
                    # 전적 정보 포맷팅
                    kills = player['stats']['kills']
                    deaths = player['stats']['deaths']
                    assists = player['stats']['assists']
                    kda = "Perfect" if deaths == 0 else round((kills + assists) / deaths, 2)
                    
                    # 승패 여부 (팀 ID로 비교)
                    win_text = "승리" if player['team'] == match_data['teams'][0]['teamId'] else "패배"
                    
                    formatted_matches.append({
                        'name': f"[{win_text}] - {player['character']}, {match_data['metadata']['map']}",
                        'value': f"- **{kills}/{deaths}/{assists}** (KDA: {kda})\n- 점수: {player['stats']['score']}"
                    })
            
            return formatted_matches
                
        except Exception as e:
            logger.error(f"발로란트 전적 정보 요청 중 오류: {e}")
            raise ValueError(f"전적 정보를 가져오는 중 오류가 발생했습니다: {e}")
    
    async def get_rank_info(self, session: aiohttp.ClientSession, puuid: str) -> Tuple[Optional[Dict], str]:
        """플레이어의 랭크 티어 정보를 가져옵니다"""
        logger.info(f"발로란트 티어 정보 요청: {puuid}")
        
        try:
            rank_url = f"{self.val_url}/val/ranked/v1/by-puuid/{puuid}"
            async with session.get(rank_url, headers=self.headers) as response:
                if response.status != 200:
                    logger.warning(f"티어 정보 요청 실패: {response.status}")
                    return None, "UNRANKED"
                
                rank_data = await response.json()
                if not rank_data or not rank_data.get('currenttier'):
                    logger.info(f"티어 정보 없음: {puuid}")
                    return None, "UNRANKED"
                    
                tier = rank_data['currenttierpatched']
                logger.debug(f"티어 정보 요청 성공: {puuid}, {tier}")
                return rank_data, tier
                
        except Exception as e:
            logger.error(f"발로란트 티어 정보 요청 중 오류: {e}")
            return None, "UNRANKED" 