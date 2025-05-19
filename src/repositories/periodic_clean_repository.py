from typing import Optional, List
from sqlalchemy.orm import Session
from src.domain.models.periodic_clean import PeriodicClean
from src.repositories.base_repository import BaseRepository

class PeriodicCleanRepository(BaseRepository[PeriodicClean]):
    def get_by_guild_and_channel(self, db: Session, guild_id: int, channel_id: int) -> Optional[PeriodicClean]:
        return db.query(self.model).filter(
            self.model.guild_id == guild_id,
            self.model.channel_id == channel_id
        ).first()

    def get_all_enabled(self, db: Session) -> List[PeriodicClean]:
        return db.query(self.model).filter(self.model.enabled == True).all()

    def enable(self, db: Session, guild_id: int, channel_id: int, interval_seconds: int):
        record = self.get_by_guild_and_channel(db, guild_id, channel_id)
        if record:
            record.enabled = True
            record.interval_seconds = interval_seconds
        else:
            record = PeriodicClean(
                guild_id=guild_id,
                channel_id=channel_id,
                interval_seconds=interval_seconds,
                enabled=True
            )
            db.add(record)
        db.commit()
        return record

    def disable(self, db: Session, guild_id: int, channel_id: int):
        record = self.get_by_guild_and_channel(db, guild_id, channel_id)
        if record:
            record.enabled = False
            db.commit()
        return record 