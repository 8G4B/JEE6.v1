from dependency_injector import containers, providers
from src.infrastructure.database.connection import get_db
from src.repositories.user_repository import UserRepository
from src.services.user_service import UserService
from src.services.time_service import TimeService
from src.domain.models.user import User

class Container(containers.DeclarativeContainer):
    config = providers.Singleton(BaseConfig)
    
    db = providers.Singleton(get_db)
    
    user_repository = providers.Factory(
        UserRepository,
        model=User,
        db=db
    )
    
    time_service = providers.Factory(TimeService)
    user_service = providers.Factory(
        UserService,
        user_repository=user_repository
    )
