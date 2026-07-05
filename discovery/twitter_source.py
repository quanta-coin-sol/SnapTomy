import logging

from .base import DiscoverySource, DiscoveredToken

logger = logging.getLogger(__name__)


class TwitterSource(DiscoverySource):
    def __init__(self, config: dict):
        super().__init__("twitter", config)
        self.api_key = config.get("api_keys", {}).get("twitter")

    async def fetch(self) -> list[DiscoveredToken]:
        return []
