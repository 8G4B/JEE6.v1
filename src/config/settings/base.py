import os
from pathlib import Path


class BaseConfig:
    BASE_DIR = Path(__file__).parent.parent.parent

    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "jee6_bot")

    DATABASE_URL = (
        f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        "?charset=utf8mb4&collation=utf8mb4_general_ci"
    )

    RIOT_API_KEY = os.getenv("RIOT_API_KEY")
    GPT_API_KEY = os.getenv("GPT_API_KEY")

    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
    SPOTIFY_PLAYLIST_ID = [
        pid.strip()
        for pid in os.getenv("SPOTIFY_PLAYLIST_ID", "").split(",")
        if pid.strip()
    ]
    SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

    EXTERNAL_API_BASE_URL = os.getenv("FLOODING_API_BASE_URL", "")
    EXTERNAL_API_TIMEOUT = float(os.getenv("FLOODING_API_TIMEOUT", "10.0"))
    EXTERNAL_API_MAX_RETRIES = int(os.getenv("FLOODING_API_MAX_RETRIES", "3"))

    EXTERNAL_AUTH_TYPE = os.getenv("FLOODING_AUTH_TYPE", "bearer")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    ENABLE_MANAGEMENT_COMMANDS = os.getenv("M", "True").lower() in ("true", "1", "yes")
    ENABLE_GAMBLING_COMMANDS = os.getenv("G", "True").lower() in ("true", "1", "yes")

    PREFIX = "!"
