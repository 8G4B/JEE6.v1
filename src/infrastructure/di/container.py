from dependency_injector import containers, providers
from src.infrastructure.database.connection import get_connection
from src.repositories.user_balance_repository import UserBalanceRepository
from src.repositories.justice_repository import JusticeRepository
from src.services.user_service import UserService
from src.services.time_service import TimeService
from src.services.channel_service import ChannelService
from src.services.justice_service import JusticeService
from src.domain.models.user_balance import UserBalance
from src.config.settings.base import BaseConfig

class Container(containers.DeclarativeContainer):
    config = providers.Singleton(BaseConfig)
    
    db = providers.Factory(get_connection)
    
    user_repository = providers.Factory(
        UserBalanceRepository,
        model=UserBalance
    )
    
    justice_repository = providers.Factory(
        JusticeRepository,
        get_connection=db
    )
    
    time_service = providers.Factory(TimeService)
    channel_service = providers.Factory(ChannelService)
    justice_service = providers.Factory(
        JusticeService,
        justice_repository=justice_repository
    )
    user_service = providers.Factory(
        UserService,
        user_repository=user_repository
    )
