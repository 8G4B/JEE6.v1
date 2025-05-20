from src.interfaces.commands.base import BaseCommand
import logging
from src.interfaces.commands.channel.CleanCommand import CleanCommand
from src.interfaces.commands.channel.PeriodicCleanCommand import PeriodicCleanCommand

logger = logging.getLogger(__name__)


class ChannelCommands(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)


__all__ = ['ChannelCommands', 'CleanCommand', 'PeriodicCleanCommand']
