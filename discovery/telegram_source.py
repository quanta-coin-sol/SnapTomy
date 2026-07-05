import logging

from .base import DiscoverySource, DiscoveredToken

logger = logging.getLogger(__name__)


class TelegramSource(DiscoverySource):
    def __init__(self, config: dict):
        super().__init__("telegram", config)

    async def fetch(self) -> list[DiscoveredToken]:
        return []
