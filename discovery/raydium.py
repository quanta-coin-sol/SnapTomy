import logging

import aiohttp

from .base import DiscoverySource, DiscoveredToken

logger = logging.getLogger(__name__)

RAYDIUM_API = "https://api.raydium.io/v2/main/pairs"
RAYDIUM_NEW = "https://api-v3.raydium.io/pools/info/list"


class RaydiumSource(DiscoverySource):
    def __init__(self, config: dict):
        super().__init__("raydium", config)
        self._seen = set()

    async def fetch(self) -> list[DiscoveredToken]:
        tokens = []
        async with aiohttp.ClientSession() as session:
            try:
                url = "https://api.dexscreener.com/latest/dex/search?q=raydium"
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    pairs = data.get("pairs", [])[:30]
                    for p in pairs:
                        address = p.get("baseToken", {}).get("address", "")
                        if address in self._seen or not address:
                            continue
                        self._seen.add(address)
                        tokens.append(DiscoveredToken(
                            address=address,
                            chain="solana",
                            symbol=p.get("baseToken", {}).get("symbol", ""),
                            name=p.get("baseToken", {}).get("name", ""),
                            source="raydium",
                            price_usd=float(p.get("priceUsd", 0)),
                            liquidity_usd=float(p.get("liquidity", {}).get("usd", 0)),
                            volume_24h_usd=float(p.get("volume", {}).get("h24", 0)),
                        ))
            except Exception as e:
                logger.debug(f"Raydium error: {e}")
        return tokens
