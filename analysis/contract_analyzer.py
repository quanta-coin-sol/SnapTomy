import logging

import aiohttp

logger = logging.getLogger(__name__)


class ContractAnalyzer:
    def __init__(self, config: dict):
        self.config = config

    async def analyze(self, address: str, chain: str) -> dict:
        result = {
            "is_verified": False,
            "has_mint_auth": False,
            "has_freeze_auth": False,
            "owner_balance_percent": 0.0,
            "is_honeypot": False,
            "has_blacklist": False,
            "has_pause": False,
            "is_upgradeable": False,
            "liquidity_locked": False,
            "liquidity_usd": 0.0,
            "score": 50,
            "issues": [],
        }
        dexscreener = await self._fetch_dexscreener(address)
        result["liquidity_usd"] = dexscreener.get("liquidity_usd", 0)
        if dexscreener.get("liquidity_usd", 0) >= 30000:
            result["score"] += 15
        else:
            result["issues"].append("Low liquidity")
        if dexscreener.get("volume_24h_usd", 0) > 0:
            result["score"] += 5
        return result

    async def _fetch_dexscreener(self, address: str) -> dict:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://api.dexscreener.com/latest/dex/tokens/{address}", timeout=10) as r:
                    if r.status != 200:
                        return {}
                    data = await r.json()
                    pairs = data.get("pairs", [])
                    if not pairs:
                        return {}
                    p = pairs[0]
                    return {
                        "price_usd": float(p.get("priceUsd", 0)),
                        "liquidity_usd": float(p.get("liquidity", {}).get("usd", 0)),
                        "volume_24h_usd": float(p.get("volume", {}).get("h24", 0)),
                        "market_cap": float(p.get("fdv", 0)),
                    }
        except Exception as e:
            logger.debug(f"DexScreener fetch error: {e}")
        return {}
