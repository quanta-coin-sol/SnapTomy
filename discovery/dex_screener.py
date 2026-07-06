import logging

import aiohttp

from .base import DiscoverySource, DiscoveredToken

logger = logging.getLogger(__name__)

NEW_PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
NEW_PAIRS_URL = "https://api.dexscreener.com/pairs/latest/v1"
CHAIN_MAP = {
    "solana": "solana", "ethereum": "ethereum", "bsc": "bsc",
    "base": "base", "arbitrum": "arbitrum", "polygon": "polygon",
    "avalanche": "avalanche", "optimism": "optimism",
}


class DexScreenerSource(DiscoverySource):
    def __init__(self, config: dict):
        super().__init__("dex_screener", config)
        self._seen = set()

    async def fetch(self) -> list[DiscoveredToken]:
        tokens = []
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(NEW_PROFILES_URL, timeout=15) as resp:
                    if resp.status != 200:
                        return []
                    profiles = await resp.json()
                    for p in profiles[:30]:
                        token = p.get("token", {})
                        address = token.get("address", "")
                        chain = p.get("chainId", "solana")
                        if address in self._seen or not address:
                            continue
                        self._seen.add(address)
                        if chain not in CHAIN_MAP:
                            continue
                        tokens.append(DiscoveredToken(
                            address=address,
                            chain=chain,
                            symbol=token.get("symbol", ""),
                            name=token.get("name", ""),
                            source="dex_screener",
                        ))
            except Exception as e:
                logger.debug(f"DexScreener profiles error: {e}")

            try:
                for chain in list(CHAIN_MAP.keys())[:3]:
                    url = f"{NEW_PAIRS_URL}/{chain}"
                    async with session.get(url, timeout=10) as resp:
                        if resp.status != 200:
                            continue
                        pairs = await resp.json()
                        for p in pairs[:20] if isinstance(pairs, list) else []:
                            address = p.get("baseToken", {}).get("address", "")
                            if address in self._seen or not address:
                                continue
                            self._seen.add(address)
                            tokens.append(DiscoveredToken(
                                address=address,
                                chain=chain,
                                symbol=p.get("baseToken", {}).get("symbol", ""),
                                name=p.get("baseToken", {}).get("name", ""),
                                source="dex_screener",
                                price_usd=float(p.get("priceUsd", 0)),
                                liquidity_usd=float(p.get("liquidity", {}).get("usd", 0)),
                                volume_24h_usd=float(p.get("volume", {}).get("h24", 0)),
                            ))
            except Exception as e:
                logger.debug(f"DexScreener pairs error: {e}")
        return tokens
