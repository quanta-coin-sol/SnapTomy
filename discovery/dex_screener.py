import logging
from datetime import datetime

import aiohttp

from .base import DiscoverySource, DiscoveredToken

logger = logging.getLogger(__name__)

DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"


class DexScreenerSource(DiscoverySource):
    def __init__(self, config: dict):
        super().__init__("dex_screener", config)

    async def fetch(self) -> list[DiscoveredToken]:
        chains = ["solana", "bsc", "ethereum", "base"]
        tokens = []
        async with aiohttp.ClientSession() as session:
            for chain in chains:
                try:
                    url = f"{DEXSCREENER_API}/search?q={chain}"
                    async with session.get(url, timeout=10) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                        pairs = data.get("pairs", [])[:15]
                        for p in pairs:
                            if float(p.get("fdv", 0)) == 0:
                                continue
                            tokens.append(DiscoveredToken(
                                address=p.get("baseToken", {}).get("address", ""),
                                chain=chain,
                                symbol=p.get("baseToken", {}).get("symbol", ""),
                                name=p.get("baseToken", {}).get("name", ""),
                                source="dex_screener",
                                price_usd=float(p.get("priceUsd", 0)),
                                liquidity_usd=float(p.get("liquidity", {}).get("usd", 0)),
                                volume_24h_usd=float(p.get("volume", {}).get("h24", 0)),
                            ))
                except Exception as e:
                    logger.debug(f"DexScreener {chain}: {e}")
        return tokens
