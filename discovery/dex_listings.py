import logging

import aiohttp

from .base import DiscoverySource, DiscoveredToken

logger = logging.getLogger(__name__)

DEX_QUERIES = {
    "meteora": "meteora",
    "orca": "orca",
    "uniswap": "uniswap",
    "pancakeswap": "pancakeswap",
    "aerodrome": "aerodrome",
}


class DexListingsSource(DiscoverySource):
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.query = DEX_QUERIES.get(name, name)
        self._seen = set()

    async def fetch(self) -> list[DiscoveredToken]:
        tokens = []
        url = f"https://api.dexscreener.com/latest/dex/search?q={self.query}"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=15) as r:
                    if r.status != 200:
                        return []
                    data = await r.json()
                    pairs = data.get("pairs", [])[:20]
                    for p in pairs:
                        address = p.get("baseToken", {}).get("address", "")
                        if address in self._seen or not address:
                            continue
                        self._seen.add(address)
                        tokens.append(DiscoveredToken(
                            address=address,
                            chain=p.get("chainId", "solana"),
                            symbol=p.get("baseToken", {}).get("symbol", ""),
                            name=p.get("baseToken", {}).get("name", ""),
                            source=self.name,
                            price_usd=float(p.get("priceUsd", 0)),
                            liquidity_usd=float(p.get("liquidity", {}).get("usd", 0)),
                            volume_24h_usd=float(p.get("volume", {}).get("h24", 0)),
                        ))
        except Exception as e:
            logger.debug(f"{self.name} error: {e}")
        return tokens
