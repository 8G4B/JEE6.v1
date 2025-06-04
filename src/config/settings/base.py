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

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    ENABLE_MANAGEMENT_COMMANDS = os.getenv("M", "True").lower() in ("true", "1", "yes")
    ENABLE_GAMBLING_COMMANDS = os.getenv("G", "True").lower() in ("true", "1", "yes")

    PREFIX = "!"
