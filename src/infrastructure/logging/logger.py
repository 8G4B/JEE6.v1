import logging
from src.config.settings.base import BaseConfig


def setup_logger():
    logging.basicConfig(
        filename=f"{BaseConfig.BASE_DIR}/logs/app.log", level=logging.INFO
    )
