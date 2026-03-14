import random
import logging
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from src.config.settings.base import BaseConfig

logger = logging.getLogger(__name__)


class SpotifyService:
    def __init__(self):
        self._sp = self._create_client()

    def _create_client(self) -> spotipy.Spotify:
        if BaseConfig.SPOTIFY_REFRESH_TOKEN:
            auth_manager = SpotifyOAuth(
                client_id=BaseConfig.SPOTIFY_CLIENT_ID,
                client_secret=BaseConfig.SPOTIFY_CLIENT_SECRET,
                redirect_uri="http://localhost:8888/callback",
                scope="playlist-read-private playlist-read-collaborative",
            )
            auth_manager.refresh_access_token(BaseConfig.SPOTIFY_REFRESH_TOKEN)
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
            result = self._sp.playlist_tracks(playlist_id, limit=1, fields="total")
            total = result["total"]
            if total == 0:
                return None

            offset = random.randint(0, total - 1)
            result = self._sp.playlist_tracks(
                playlist_id,
                limit=1,
                offset=offset,
                fields="items(track(id,name,artists,album(name,images),external_urls,duration_ms))",
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

            return {
                "name": track["name"],
                "artists": artists,
                "album": track["album"]["name"],
                "url": track["external_urls"]["spotify"],
                "image": album_img,
                "duration": f"{minutes}:{seconds:02d}",
            }
        except Exception as e:
            logger.error(f"Spotify API 오류: {e}")
            return None
