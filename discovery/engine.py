import asyncio
import logging
from typing import AsyncGenerator, Callable, Optional

from .base import DiscoveredToken
from .dex_listings import DexListingsSource
from .dex_screener import DexScreenerSource
from .birdeye import BirdeyeSource
from .pump_fun import PumpFunSource
from .pump_fun_rpc import PumpFunRpcSource
from .raydium import RaydiumSource
from .rug_check import RugCheckSource
from .twitter_source import TwitterSource
from .telegram_source import TelegramSource

logger = logging.getLogger(__name__)


class DiscoveryEngine:
    def __init__(self, config: dict):
        self.config = config
        self.sources = [
            PumpFunRpcSource(config),
            RaydiumSource(config),
            DexScreenerSource(config),
            DexListingsSource("meteora", config),
            DexListingsSource("orca", config),
            DexListingsSource("uniswap", config),
            DexListingsSource("pancakeswap", config),
            DexListingsSource("aerodrome", config),
            BirdeyeSource(config),
            RugCheckSource(config),
            TwitterSource(config),
            TelegramSource(config),
        ]
        self._listeners: list[Callable] = []

    def on_token_discovered(self, callback: Callable):
        self._listeners.append(callback)

    async def run(self) -> AsyncGenerator[DiscoveredToken, None]:
        tasks = [source.start() for source in self.sources]
        async for batch in self._merge(tasks):
            for token in batch:
                logger.info(f"Discovered: {token.symbol} ({token.source}) on {token.chain}")
                for listener in self._listeners:
                    try:
                        await listener(token)
                    except Exception as e:
                        logger.error(f"Listener error: {e}")
                yield token

    async def _merge(self, gens):
        queues = [asyncio.Queue() for _ in gens]

        async def feeder(idx, gen):
            async for batch in gen:
                await queues[idx].put(batch)

        consumers = [asyncio.create_task(feeder(i, g)) for i, g in enumerate(gens)]
        try:
            while True:
                for q in queues:
                    if not q.empty():
                        yield await q.get()
                await asyncio.sleep(0.1)
        finally:
            for c in consumers:
                c.cancel()
