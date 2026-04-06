import random
import logging
import asyncio
import time
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from spotipy.cache_handler import MemoryCacheHandler
from src.config.settings.base import BaseConfig

logger = logging.getLogger(__name__)


class SpotifyService:
    _playlist_total_cache: dict[str, tuple[float, int]] = {}
    _artist_genres_cache: dict[str, tuple[float, list]] = {}
    CACHE_TTL = 3600

    def __init__(self):
        self._sp = self._create_client()

    def _create_client(self) -> spotipy.Spotify:
        if BaseConfig.SPOTIFY_REFRESH_TOKEN:
            cache_handler = MemoryCacheHandler(token_info={
                "access_token": None,
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": BaseConfig.SPOTIFY_REFRESH_TOKEN,
                "scope": "playlist-read-private playlist-read-collaborative",
                "expires_at": 0,
            })
            auth_manager = SpotifyOAuth(
                client_id=BaseConfig.SPOTIFY_CLIENT_ID,
                client_secret=BaseConfig.SPOTIFY_CLIENT_SECRET,
                redirect_uri="http://127.0.0.1:8888/callback",
                scope="playlist-read-private playlist-read-collaborative",
                cache_handler=cache_handler,
                open_browser=False,
            )
            return spotipy.Spotify(auth_manager=auth_manager)

        return spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=BaseConfig.SPOTIFY_CLIENT_ID,
                client_secret=BaseConfig.SPOTIFY_CLIENT_SECRET,
            )
        )

    async def get_random_track(self, playlist_id: str) -> dict | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_random_track, playlist_id)

    def _fetch_random_track(self, playlist_id: str) -> dict | None:
        try:
            now = time.time()
            if playlist_id in SpotifyService._playlist_total_cache:
                cache_time, cached_total = SpotifyService._playlist_total_cache[playlist_id]
                if now - cache_time < SpotifyService.CACHE_TTL:
                    total = cached_total
                else:
                    result = self._sp.playlist_tracks(playlist_id, limit=1, fields="total")
                    total = result["total"]
                    SpotifyService._playlist_total_cache[playlist_id] = (now, total)
            else:
                result = self._sp.playlist_tracks(playlist_id, limit=1, fields="total")
                total = result["total"]
                SpotifyService._playlist_total_cache[playlist_id] = (now, total)

            if total == 0:
                return None

            offset = random.randint(0, total - 1)
            result = self._sp.playlist_tracks(
                playlist_id,
                limit=1,
                offset=offset,
                fields="items(track(id,name,artists(id,name),album(name,images),external_urls,duration_ms))",
            )

            items = result.get("items", [])
            if not items or not items[0].get("track"):
                return None

            track = items[0]["track"]
            artists = ", ".join(a["name"] for a in track["artists"])
            album_img = (
                track["album"]["images"][0]["url"]
                if track["album"]["images"]
                else None
            )
            duration_ms = track.get("duration_ms", 0)
            minutes, seconds = divmod(duration_ms // 1000, 60)

            genres = []
            if track["artists"]:
                artist_id = track["artists"][0]["id"]
                if artist_id in SpotifyService._artist_genres_cache:
                    cache_time, cached_genres = SpotifyService._artist_genres_cache[artist_id]
                    if time.time() - cache_time < SpotifyService.CACHE_TTL:
                        genres = cached_genres
                    else:
                        artist_info = self._sp.artist(artist_id)
                        genres = artist_info.get("genres", [])
                        SpotifyService._artist_genres_cache[artist_id] = (time.time(), genres)
                else:
                    artist_info = self._sp.artist(artist_id)
                    genres = artist_info.get("genres", [])
                    SpotifyService._artist_genres_cache[artist_id] = (time.time(), genres)

            return {
                "name": track["name"],
                "artists": artists,
                "album": track["album"]["name"],
                "url": track["external_urls"]["spotify"],
                "image": album_img,
                "duration": f"{minutes}:{seconds:02d}",
                "genres": genres,
            }
        except Exception as e:
            logger.error(f"Spotify API 오류: {e}")
            return None
