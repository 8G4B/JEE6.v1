from typing import Optional, List
from src.domain.models.PeriodicClean import PeriodicClean
from src.repositories.Base import BaseRepository


class PeriodicCleanRepository(BaseRepository[PeriodicClean]):
    def __init__(self, model=PeriodicClean, db=None):
        super().__init__(model=model, db=db)

    def get_by_guild_and_channel(
        self, guild_id: int, channel_id: int
    ) -> Optional[PeriodicClean]:
        return (
            self.db.query(self.model)
            .filter(
                self.model.guild_id == guild_id, self.model.channel_id == channel_id
            )
            .first()
        )

    def find_by_channel_name(
        self, guild_id: int, channel_name: str
    ) -> List[PeriodicClean]:
        return (
            self.db.query(self.model)
            .filter(
                self.model.guild_id == guild_id,
                self.model.channel_name == channel_name,
                self.model.enabled,
            )
            .all()
        )

    def get_all_enabled(self) -> List[PeriodicClean]:
        return self.db.query(self.model).filter(self.model.enabled).all()

    def enable(
        self, guild_id: int, channel_id: int, channel_name: str, interval_seconds: int
    ):
        record = self.get_by_guild_and_channel(guild_id, channel_id)
        if record:
            record.enabled = True
            record.interval_seconds = interval_seconds
            record.channel_name = channel_name
        else:
            record = PeriodicClean(
                guild_id=guild_id,
                channel_id=channel_id,
                channel_name=channel_name,
                interval_seconds=interval_seconds,
                enabled=True,
            )
            self.db.add(record)
        self.db.commit()
        return record

    def update_channel_id(
        self, guild_id: int, old_channel_id: int, new_channel_id: int, channel_name: str
    ) -> Optional[PeriodicClean]:
        record = self.get_by_guild_and_channel(guild_id, old_channel_id)
        if record and record.enabled:
            record.channel_id = new_channel_id
            record.channel_name = channel_name
            self.db.commit()
            return record
        return None

    def disable(self, guild_id: int, channel_id: int):
        record = self.get_by_guild_and_channel(guild_id, channel_id)
        if record:
            record.enabled = False
            self.db.commit()
        return record

    def disable_by_name(self, guild_id: int, channel_name: str) -> List[PeriodicClean]:
        records = (
            self.db.query(self.model)
            .filter(
                self.model.guild_id == guild_id,
                self.model.channel_name == channel_name,
                self.model.enabled,
            )
            .all()
        )

        for record in records:
            record.enabled = False

        if records:
            self.db.commit()

        return records
