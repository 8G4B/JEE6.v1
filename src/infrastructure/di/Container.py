from dependency_injector import containers, providers
from src.repositories.UserBalanceRepository import UserBalanceRepository
from src.repositories.JusticeRepository import JusticeRepository
from src.repositories.PeriodicCleanRepository import PeriodicCleanRepository
from src.repositories.ChannelSlowModeRepository import ChannelSlowModeRepository
from src.repositories.UserLinkRepository import UserLinkRepository
from src.services.UserService import UserService
from src.services.TimeService import TimeService
from src.services.ChannelService import ChannelService
from src.services.JusticeService import JusticeService
from src.services.SlowModeService import SlowModeService
from src.services.FloodingAuthService import FloodingAuthService
from src.services.FloodingApiService import FloodingApiService
from src.clients.FloodingApiClient import BaseApiClient, AuthenticatedApiClient
from src.domain.models.UserBalance import UserBalance
from src.domain.models.PeriodicClean import PeriodicClean
from src.domain.models.ChannelSlowMode import ChannelSlowMode
from src.domain.models.UserLink import UserLink
from src.config.settings.Base import BaseConfig
from src.interfaces.commands.channel import ChannelCommands
from src.interfaces.commands.information.TimeCommand import TimeCommands
from src.interfaces.commands.information.InformationCommand import InformationCommands
from src.interfaces.commands.meal.MealCommand import MealCommands
from src.interfaces.commands.riot.LolCommand import LolCommands
from src.interfaces.commands.riot.ValoCommand import ValoCommands
from src.interfaces.commands.gambling.GamblingCommand import GamblingCommands
from src.interfaces.commands.gambling.GamblingGames import GamblingGames
from src.interfaces.commands.gambling.GamblingCardGames import GamblingCardGames
from src.interfaces.commands.channel.SlowModeCommand import SlowModeCommand
from src.interfaces.commands.flooding.FloodingAuthCommand import FloodingAuthCommand
from src.interfaces.commands.flooding.FloodingCommand import FloodingCommand


class Container(containers.DeclarativeContainer):
    config = providers.Singleton(BaseConfig)
    bot = providers.Dependency()

    user_repository = providers.Factory(UserBalanceRepository, model=UserBalance)

    justice_repository = providers.Factory(JusticeRepository)

    periodic_clean_repository = providers.Factory(
        PeriodicCleanRepository, model=PeriodicClean
    )

    slow_mode_repository = providers.Factory(
        ChannelSlowModeRepository, model=ChannelSlowMode
    )

    time_service = providers.Factory(TimeService)
    channel_service = providers.Factory(ChannelService)
    justice_service = providers.Factory(
        JusticeService, justice_repository=justice_repository
    )
    user_service = providers.Factory(UserService, user_repository=user_repository)
    slow_mode_service = providers.Factory(SlowModeService)

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

    slow_mode_command = providers.Factory(
        SlowModeCommand, bot=bot, container=providers.Self()
    )

    user_link_repository = providers.Factory(UserLinkRepository, model=UserLink)

    flooding_base_client = providers.Singleton(
        BaseApiClient,
        base_url=BaseConfig.EXTERNAL_API_BASE_URL,
        timeout=BaseConfig.EXTERNAL_API_TIMEOUT,
        max_retries=BaseConfig.EXTERNAL_API_MAX_RETRIES,
    )

    flooding_auth_client = providers.Singleton(
        AuthenticatedApiClient,
        base_url=BaseConfig.EXTERNAL_API_BASE_URL,
        timeout=BaseConfig.EXTERNAL_API_TIMEOUT,
        max_retries=BaseConfig.EXTERNAL_API_MAX_RETRIES,
    )

    flooding_auth_service = providers.Factory(
        FloodingAuthService,
        client=flooding_base_client,
        user_link_repo=user_link_repository,
        auth_type=BaseConfig.EXTERNAL_AUTH_TYPE,
    )

    flooding_api_service = providers.Factory(
        FloodingApiService,
        client=flooding_auth_client,
        auth_service=flooding_auth_service,
    )

    flooding_auth_command = providers.Factory(
        FloodingAuthCommand,
        bot=bot,
        auth_service=flooding_auth_service,
    )

    flooding_command = providers.Factory(
        FloodingCommand,
        bot=bot,
        api_service=flooding_api_service,
    )
