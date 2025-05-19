import discord
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ChannelService:
    def __init__(self, periodic_clean_repository=None, db: Session = None):
        self.periodic_clean_repository = periodic_clean_repository
        self.db = db

    async def clean_channel(
        self,
        guild: discord.Guild,
        channel_to_clean: discord.TextChannel,
        channel_name: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[discord.TextChannel]]:
        try:
            if channel_name:
                found_channel = discord.utils.get(
                    guild.text_channels, name=channel_name
                )
                if not found_channel:
                    return False, f"'{channel_name}' 이런 채널 없는데요", None
                channel_to_clean = found_channel

            old_channel_id = channel_to_clean.id
            channel_name = channel_to_clean.name

            category = channel_to_clean.category
            position = channel_to_clean.position
            topic = channel_to_clean.topic
            slowmode_delay = channel_to_clean.slowmode_delay
            nsfw = channel_to_clean.is_nsfw()
            overwrites = channel_to_clean.overwrites

            await channel_to_clean.delete(reason="채널 청소")

            new_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                topic=topic,
                slowmode_delay=slowmode_delay,
                nsfw=nsfw,
                overwrites=overwrites,
                position=position,
                reason="채널 청소",
            )

            if self.periodic_clean_repository and self.db:
                try:
                    self.periodic_clean_repository.update_channel_id(
                        guild.id, old_channel_id, new_channel.id, channel_name
                    )
                except Exception as e:
                    logger.error(f"Failed to update channel ID in database: {e}")

            return True, "채널이 성공적으로 청소되었습니다.", new_channel

        except discord.Forbidden:
            return False, "권한이 부족합니다.", None
        except Exception as e:
            logger.error(f"Channel cleaning error: {str(e)}")
            return False, str(e), None

    def enable_periodic_clean(self, guild_id, channel_id, interval_seconds):
        if self.periodic_clean_repository and self.db:
            return self.periodic_clean_repository.enable(
                self.db, guild_id, channel_id, interval_seconds
            )

    def disable_periodic_clean(self, guild_id, channel_id):
        if self.periodic_clean_repository and self.db:
            return self.periodic_clean_repository.disable(self.db, guild_id, channel_id)

    def get_all_enabled_periodic_cleans(self):
        if self.periodic_clean_repository and self.db:
            return self.periodic_clean_repository.get_all_enabled(self.db)
        return []
