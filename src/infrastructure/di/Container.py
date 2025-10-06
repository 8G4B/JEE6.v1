from dependency_injector import containers, providers
from src.repositories.UserBalanceRepository import UserBalanceRepository
from src.repositories.JusticeRepository import JusticeRepository
from src.services.UserService import UserService
from src.services.TimeService import TimeService
from src.services.ChannelService import ChannelService
from src.services.JusticeService import JusticeService
from src.domain.models.UserBalance import UserBalance
from src.config.settings.Base import BaseConfig
from src.repositories.PeriodicCleanRepository import PeriodicCleanRepository
from src.domain.models.PeriodicClean import PeriodicClean
from src.interfaces.commands.channel import ChannelCommands
from src.interfaces.commands.information.TimeCommand import TimeCommands
from src.interfaces.commands.information.InformationCommand import InformationCommands
from src.interfaces.commands.meal.MealCommand import MealCommands
from src.interfaces.commands.riot.LolCommand import LolCommands
from src.interfaces.commands.riot.ValoCommand import ValoCommands
from src.interfaces.commands.gambling.GamblingCommand import GamblingCommands
from src.interfaces.commands.gambling.GamblingGames import GamblingGames
from src.interfaces.commands.gambling.GamblingCardGames import GamblingCardGames


class Container(containers.DeclarativeContainer):
    config = providers.Singleton(BaseConfig)
    bot = providers.Dependency()

    user_repository = providers.Factory(UserBalanceRepository, model=UserBalance)

    justice_repository = providers.Factory(JusticeRepository)

    time_service = providers.Factory(TimeService)
    channel_service = providers.Factory(ChannelService)
    justice_service = providers.Factory(
        JusticeService, justice_repository=justice_repository
    )
    user_service = providers.Factory(UserService, user_repository=user_repository)
    periodic_clean_repository = providers.Factory(
        PeriodicCleanRepository, model=PeriodicClean
    )

    channel_command = providers.Factory(
        ChannelCommands, bot=bot, container=providers.Self()
    )

    timeout_command = providers.Factory(
        TimeCommands, bot=bot, container=providers.Self()
    )

    information_command = providers.Factory(
        InformationCommands, bot=bot, container=providers.Self()
    )

    meal_command = providers.Factory(MealCommands, bot=bot, container=providers.Self())

    lol_command = providers.Factory(LolCommands, bot=bot, container=providers.Self())

    valo_command = providers.Factory(ValoCommands, bot=bot, container=providers.Self())

    gambling_command = providers.Factory(
        GamblingCommands, bot=bot, container=providers.Self()
    )

    gambling_games = providers.Factory(
        GamblingGames, bot=bot, container=providers.Self()
    )

    gambling_card_games = providers.Factory(
        GamblingCardGames, bot=bot, container=providers.Self()
    )
