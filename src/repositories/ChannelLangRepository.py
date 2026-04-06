from typing import Optional, Set
from src.domain.models.ChannelLang import ChannelLang
from src.repositories.Base import BaseRepository


class ChannelLangRepository(BaseRepository[ChannelLang]):
    def __init__(self, model=ChannelLang, db=None):
        super().__init__(model=model, db=db)

    def is_enabled(self, channel_id: int) -> bool:
        record = (
            self.db.query(self.model)
            .filter(self.model.channel_id == channel_id, self.model.enabled)
            .first()
        )
        return record is not None

    def toggle(self, guild_id: int, channel_id: int) -> bool:
        record = (
            self.db.query(self.model)
            .filter(self.model.channel_id == channel_id)
            .first()
        )
        if record:
            record.enabled = not record.enabled
            self.db.commit()
            return record.enabled
        else:
            record = ChannelLang(
                guild_id=guild_id,
                channel_id=channel_id,
                enabled=True,
            )
            self.db.add(record)
            self.db.commit()
            return True

    def get_all_enabled_channel_ids(self) -> Set[int]:
        records = self.db.query(self.model).filter(self.model.enabled).all()
        return {r.channel_id for r in records}
