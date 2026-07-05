import logging

import aiohttp

from .base import DiscoverySource, DiscoveredToken

logger = logging.getLogger(__name__)

BIRDEYE_API = "https://public-api.birdeye.so/defi"


class BirdeyeSource(DiscoverySource):
    def __init__(self, config: dict):
        super().__init__("birdeye", config)
        self.api_key = config.get("api_keys", {}).get("birdeye")

    async def fetch(self) -> list[DiscoveredToken]:
        if not self.api_key:
            logger.debug("Birdeye: no API key configured")
            return []
        tokens = []
        headers = {"x-api-key": self.api_key}
        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                url = f"{BIRDEYE_API}/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=20"
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        logger.debug(f"Birdeye: HTTP {resp.status}")
                        return []
                    data = await resp.json()
                    for item in data.get("data", {}).get("tokens", []):
                        tokens.append(DiscoveredToken(
                            address=item.get("address", ""),
                            chain="solana",
                            symbol=item.get("symbol", ""),
                            name=item.get("name", ""),
                            source="birdeye",
                            price_usd=float(item.get("price", 0)),
                            liquidity_usd=float(item.get("liquidity", 0)),
                            volume_24h_usd=float(item.get("v24hUSD", 0)),
                        ))
            except Exception as e:
                logger.debug(f"Birdeye error: {e}")
        return tokens
