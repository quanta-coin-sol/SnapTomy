import logging

import aiohttp

from .base import DiscoverySource, DiscoveredToken

logger = logging.getLogger(__name__)

PUMPFUN_API = "https://api.pump.fun"


class PumpFunSource(DiscoverySource):
    def __init__(self, config: dict):
        super().__init__("pump_fun", config)

    async def fetch(self) -> list[DiscoveredToken]:
        tokens = []
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{PUMPFUN_API}/coins?limit=20"
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        logger.debug(f"PumpFun: HTTP {resp.status}")
                        return []
                    data = await resp.json()
                    for item in data if isinstance(data, list) else data.get("coins", []):
                        tokens.append(DiscoveredToken(
                            address=item.get("mint", item.get("address", "")),
                            chain="solana",
                            symbol=item.get("symbol", ""),
                            name=item.get("name", ""),
                            source="pump_fun",
                            price_usd=float(item.get("price_usd", item.get("price", 0))),
                            liquidity_usd=float(item.get("liquidity", 0)),
                            volume_24h_usd=float(item.get("volume_24h", 0)),
                        ))
            except Exception as e:
                logger.debug(f"PumpFun error: {e}")
        return tokens
