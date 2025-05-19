from dependency_injector import containers, providers
from src.infrastructure.database.connection import get_db
from src.repositories.user_balance_repository import UserBalanceRepository
from src.services.user_service import UserService
from src.services.time_service import TimeService
from src.services.channel_service import ChannelService
from src.domain.models.user_balance import UserBalance
from src.config.settings.base import BaseConfig

class Container(containers.DeclarativeContainer):
    config = providers.Singleton(BaseConfig)
    
    db = providers.Singleton(get_db)
    
    user_repository = providers.Factory(
        UserBalanceRepository,
        model=UserBalance
    )
    
    time_service = providers.Factory(TimeService)
    channel_service = providers.Factory(ChannelService)
    user_service = providers.Factory(
        UserService,
        user_repository=user_repository
    )
