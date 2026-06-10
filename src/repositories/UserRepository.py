from src.domain.models.user import User
from src.repositories.base import BaseRepository
from typing import Optional


class UserRepository(BaseRepository[User]):
    def get_by_discord_id(self, discord_id: str) -> Optional[User]:
        return (
            self.db.query(self.model)
            .filter(self.model.discord_id == discord_id)
            .first()
        )

    def update_points(self, discord_id: str, points: int) -> Optional[User]:
        user = self.get_by_discord_id(discord_id)
        if user:
            user.points = points
            self.db.commit()
            self.db.refresh(user)
        return user
