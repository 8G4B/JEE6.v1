import os
from pathlib import Path

class BaseConfig:
    BASE_DIR = Path(__file__).parent.parent.parent
    
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    RIOT_API_KEY = os.getenv('RIOT_API_KEY')
    GPT_API_KEY = os.getenv('GPT_API_KEY')
