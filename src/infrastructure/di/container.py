from dependency_injector import containers, providers
from src.infrastructure.database.connection import get_db
from src.services.time_service import TimeService

class Container(containers.DeclarativeContainer):
    db = providers.Singleton(get_db)
    time_service = providers.Factory(TimeService)
