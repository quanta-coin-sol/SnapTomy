import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class DataCollector:
    def __init__(self, config: dict):
        self.config = config
        self.rpc = config.get("rpc", {})

    async def collect(self, address: str, chain: str) -> dict:
        data = {
            "address": address,
            "chain": chain,
            "holders": 0,
            "liquidity_usd": 0.0,
            "volume_24h_usd": 0.0,
            "price_usd": 0.0,
            "market_cap": 0.0,
            "owner_balance_percent": 0.0,
            "top_holder_concentration": 0.0,
            "has_mint_auth": False,
            "has_freeze_auth": False,
            "is_renounced": False,
            "socials": {},
        }
        dexscreener = await self._fetch_dexscreener(address, chain)
        data.update(dexscreener)
        return data

    async def _fetch_dexscreener(self, address: str, chain: str) -> dict:
        try:
            chain_map = {"solana": "solana", "bsc": "bsc", "ethereum": "ethereum"}
            url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=10) as r:
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
            logger.debug(f"DataCollector dexscreener: {e}")
        return {}
