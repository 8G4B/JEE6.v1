import logging
import aiohttp
import asyncio
import requests
import time
from typing import Dict, List, Tuple, Optional
from src.config.settings.riot_settings import (
    LOL_BASE_URL,
    LOL_ASIA_URL,
    RIOT_HEADERS,
    LOL_GAME_MODES,
)

logger = logging.getLogger(__name__)


class LolService:
    def __init__(self):
        self.headers = RIOT_HEADERS
        self.base_url = LOL_BASE_URL
        self.asia_url = LOL_ASIA_URL
        self.champions_data = self._get_champion_data()
        self.game_mode_kr = LOL_GAME_MODES
        self.account_cache = {}
        self.tier_cache = {}
        self.match_cache = {}
        self.cache_timeout = 600

    def _get_champion_data(self) -> Dict:
        try:
            ddragon_version_url = (
                "https://ddragon.leagueoflegends.com/api/versions.json"
            )
            version_response = requests.get(ddragon_version_url)
            latest_version = version_response.json()[0]
            champions_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ko_KR/champion.json"
            champions_response = requests.get(champions_url)
            logger.info(f"롤 챔피언 데이터 로드 완료 (버전: {latest_version})")
            return champions_response.json()
        except Exception as e:
            logger.error(f"롤 챔피언 데이터 로드 실패: {e}")
            return {"data": {}}

    def _get_champion_name_kr(self, champion_id: str) -> str:
        return next(
            (
                champ_info["name"]
                for champ_name, champ_info in self.champions_data["data"].items()
                if champ_name == champion_id
            ),
            champion_id,
        )

    async def get_account_info(
        self, session: aiohttp.ClientSession, riot_id: str
    ) -> Dict:
        logger.info(f"롤 계정 정보 요청: {riot_id}")
        if riot_id in self.account_cache:
            cache_time, cached_data = self.account_cache[riot_id]
            if time.time() - cache_time < self.cache_timeout:
                logger.debug(f"롤 계정 정보 캐시 사용: {riot_id}")
                return cached_data
        if "#" not in riot_id:
            error_msg = "닉넴#태그 형식으로 입력하세요"
            logger.warning(f"잘못된 라이엇 ID 형식: {riot_id}, {error_msg}")
            raise ValueError(error_msg)
        game_name, tag_line = riot_id.split("#")
        account_url = f"{self.asia_url}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        try:
            async with session.get(account_url, headers=self.headers) as response:
                if response.status != 200:
                    error_msg = (
                        f"계정을 찾을 수 없습니다. (상태 코드: {response.status})"
                    )
                    logger.warning(f"계정 정보 요청 실패: {error_msg}")
                    raise ValueError(error_msg)
                account_data = await response.json()
                self.account_cache[riot_id] = (time.time(), account_data)
                logger.debug(f"계정 정보 요청 성공: {game_name}#{tag_line}")
                return account_data
        except aiohttp.ClientError as e:
            logger.error(f"계정 정보 요청 중 네트워크 오류: {e}")
            raise ValueError(f"네트워크 오류: {e}")

    async def get_tier_info(
        self, session: aiohttp.ClientSession, puuid: str
    ) -> Tuple[Optional[Dict], str]:
        logger.info(f"롤 티어 정보 요청: {puuid}")
        if puuid in self.tier_cache:
            cache_time, cached_data = self.tier_cache[puuid]
            if time.time() - cache_time < self.cache_timeout:
                logger.debug(f"티어 정보 캐시 사용: {puuid}")
                return cached_data
        try:
            summoner_url = f"{self.base_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"
            async with session.get(summoner_url, headers=self.headers) as response:
                if response.status != 200:
                    logger.warning(f"소환사 정보 요청 실패: {response.status}")
                    return None, "UNRANKED"
                summoner_data = await response.json()
            ranked_url = f"{self.base_url}/lol/league/v4/entries/by-summoner/{summoner_data['id']}"
            async with session.get(ranked_url, headers=self.headers) as response:
                if response.status != 200:
                    logger.warning(f"랭크 정보 요청 실패: {response.status}")
                    return None, "UNRANKED"
                ranked_data = await response.json()
            tier = "UNRANKED"
            solo_rank = None
            if ranked_data:
                solo_rank = next(
                    (
                        queue
                        for queue in ranked_data
                        if queue["queueType"] == "RANKED_SOLO_5x5"
                    ),
                    None,
                )
                if solo_rank:
                    tier = solo_rank["tier"]
            self.tier_cache[puuid] = (time.time(), (solo_rank, tier))
            return solo_rank, tier
        except Exception as e:
            logger.error(f"티어 정보 요청 중 오류: {e}")
            return None, "UNRANKED"

    async def get_match_history(
        self, session: aiohttp.ClientSession, puuid: str
    ) -> List[Dict]:
        logger.info(f"롤 전적 정보 요청: {puuid}")
        try:
            matches_url = f"{self.asia_url}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"
            async with session.get(matches_url, headers=self.headers) as response:
                if response.status != 200:
                    logger.warning(f"매치 ID 목록 요청 실패: {response.status}")
                    raise ValueError("최근 게임 기록을 가져올 수 없습니다.")
                match_ids = await response.json()
            if not match_ids:
                logger.warning(f"최근 게임 기록 없음: {puuid}")
                raise ValueError("최근 게임 기록이 없습니다.")
            tasks = []
            for match_id in match_ids:
                if match_id in self.match_cache:
                    cache_time, data = self.match_cache[match_id]
                    if time.time() - cache_time < self.cache_timeout:
                        logger.debug(f"매치 정보 캐시 사용: {match_id}")
                        tasks.append(asyncio.create_task(asyncio.sleep(0, result=data)))
                        continue
                url = f"{self.asia_url}/lol/match/v5/matches/{match_id}"
                tasks.append(self._fetch_match_data(session, url, match_id))
            match_data_list = await asyncio.gather(*tasks, return_exceptions=True)
            match_data_list = [
                data
                for data in match_data_list
                if data is not None and not isinstance(data, Exception)
            ]
            if not match_data_list:
                logger.warning(f"유효한 매치 정보 없음: {puuid}")
                raise ValueError("최근 게임 기록을 가져올 수 없습니다.")
            formatted_matches = []
            for match_data in match_data_list:
                participant = next(
                    p for p in match_data["info"]["participants"] if p["puuid"] == puuid
                )
                champion_id = participant["championName"]
                champion_name = self._get_champion_name_kr(champion_id)
                kills = participant["kills"]
                deaths = participant["deaths"]
                assists = participant["assists"]
                kda = "Perfect" if deaths == 0 else round((kills + assists) / deaths, 2)
                win = participant["win"]
                minutes = match_data["info"]["gameDuration"] // 60
                seconds = match_data["info"]["gameDuration"] % 60
                game_mode = match_data["info"]["gameMode"]
                kr_mode = self.game_mode_kr.get(game_mode, game_mode)
                formatted_matches.append(
                    {
                        "name": f"[{'승리' if win else '패배'}] - {champion_name}, {kr_mode}",
                        "value": f"- **{kills}/{deaths}/{assists}** ({kda})\n- {minutes}분 {seconds}초",
                    }
                )
            return formatted_matches
        except Exception as e:
            logger.error(f"전적 정보 요청 중 오류: {e}")
            raise ValueError(f"전적 정보를 가져오는 중 오류가 발생했습니다: {e}")

    async def _fetch_match_data(self, session, url, match_id):
        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.match_cache[match_id] = (time.time(), data)
                    return data
                logger.warning(
                    f"매치 정보 요청 실패: {match_id}, 상태 코드: {response.status}"
                )
                return None
        except Exception as e:
            logger.error(f"매치 정보 요청 중 오류: {match_id}, {e}")
            return None

    async def get_rotation(self, session: aiohttp.ClientSession) -> List[Dict]:
        logger.info("롤 로테이션 정보 요청")
        try:
            rotation_url = f"{self.base_url}/lol/platform/v3/champion-rotations"
            async with session.get(rotation_url, headers=self.headers) as response:
                if response.status != 200:
                    logger.warning(f"로테이션 정보 요청 실패: {response.status}")
                    raise ValueError("로테이션 정보를 가져올 수 없습니다.")
                rotation_data = await response.json()
            champion_info = []
            for champ_id in rotation_data["freeChampionIds"]:
                for champ_name, champ_info in self.champions_data["data"].items():
                    if int(champ_info["key"]) == champ_id:
                        champion_info.append(
                            {"kr_name": champ_info["name"], "en_name": champ_name}
                        )
                        break
            return champion_info
        except Exception as e:
            logger.error(f"로테이션 정보 요청 중 오류: {e}")
            raise ValueError(f"로테이션 정보를 가져오는 중 오류가 발생했습니다: {e}")
