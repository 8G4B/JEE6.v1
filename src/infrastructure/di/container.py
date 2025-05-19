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
from src.interfaces.commands.base_command import BaseCommand
from src.interfaces.commands.channel_command import ChannelCommands
from src.interfaces.commands.time_command import TimeCommands
from src.interfaces.commands.information_command import InformationCommands
from src.interfaces.commands.meal_command import MealCommands
from src.interfaces.commands.lol_command import LolCommands
from src.interfaces.commands.valo_command import ValoCommands
from src.interfaces.commands.gambling_command import GamblingCommands
from src.interfaces.commands.gambling_games import GamblingGames
from src.interfaces.commands.gambling_card_games import GamblingCardGames

class Container(containers.DeclarativeContainer):
    config = providers.Singleton(BaseConfig)
    bot = providers.Dependency()
    
    user_repository = providers.Factory(
        UserBalanceRepository,
        model=UserBalance
    )
    
    justice_repository = providers.Factory(
        JusticeRepository
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

    channel_command = providers.Factory(
        ChannelCommands,
        bot=bot
    )
    
    timeout_command = providers.Factory(
        TimeCommands,
        bot=bot
    )
    
    information_command = providers.Factory(
        InformationCommands,
        bot=bot
    )
    
    meal_command = providers.Factory(
        MealCommands,
        bot=bot
    )
    
    lol_command = providers.Factory(
        LolCommands,
        bot=bot
    )
    
    valo_command = providers.Factory(
        ValoCommands,
        bot=bot
    )
    
    gambling_command = providers.Factory(
        GamblingCommands,
        bot=bot
    )
    
    gambling_games = providers.Factory(
        GamblingGames,
        bot=bot
    )
    
    gambling_card_games = providers.Factory(
        GamblingCardGames,
        bot=bot
    )
