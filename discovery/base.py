import abc
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredToken:
    address: str
    chain: str
    symbol: str
    name: str
    source: str
    price_usd: float = 0.0
    liquidity_usd: float = 0.0
    volume_24h_usd: float = 0.0
    holders: int = 0
    created_at: Optional[datetime] = None
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    extra: dict = field(default_factory=dict)


class DiscoverySource(abc.ABC):
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self._running = False

    @abc.abstractmethod
    async def fetch(self) -> list[DiscoveredToken]:
        ...

    async def start(self):
        self._running = True
        import random
        await asyncio.sleep(random.uniform(0, self.config.get("poll_interval_seconds", 60)))
        while self._running:
            try:
                tokens = await self.fetch()
                if tokens:
                    logger.info(f"{self.name}: discovered {len(tokens)} tokens")
                yield tokens
            except Exception as e:
                logger.error(f"{self.name} error: {e}")
                yield []
            await asyncio.sleep(self.config.get("poll_interval_seconds", 60))

    def stop(self):
        self._running = False
