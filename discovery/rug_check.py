import logging

import aiohttp

from .base import DiscoverySource, DiscoveredToken

logger = logging.getLogger(__name__)

RUGCHECK_API = "https://api.rugcheck.xyz/v1"


class RugCheckSource(DiscoverySource):
    def __init__(self, config: dict):
        super().__init__("rug_check", config)

    async def fetch(self) -> list[DiscoveredToken]:
        return []
