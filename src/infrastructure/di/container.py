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
from src.repositories.periodic_clean_repository import PeriodicCleanRepository
from src.domain.models.periodic_clean import PeriodicClean
from src.infrastructure.database.session import get_db_session

class Container(containers.DeclarativeContainer):
    config = providers.Singleton(BaseConfig)
    
    user_repository = providers.Factory(
        UserBalanceRepository,
        model=UserBalance
    )
    
    justice_repository = providers.Factory(
        JusticeRepository,
        get_connection=None  
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
    periodic_clean_repository = providers.Factory(
        PeriodicCleanRepository,
        model=PeriodicClean
    )
