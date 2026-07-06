import logging
import time

import aiohttp

from .base import DiscoverySource, DiscoveredToken

logger = logging.getLogger(__name__)

PUMPFUN_API = "https://api.pump.fun"


class PumpFunSource(DiscoverySource):
    def __init__(self, config: dict):
        super().__init__("pump_fun", config)
        self._seen = set()

    async def fetch(self) -> list[DiscoveredToken]:
        tokens = []
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{PUMPFUN_API}/coins?offset=0&limit=50&sort=created"
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        logger.debug(f"PumpFun HTTP {resp.status}")
                        return []
                    data = await resp.json()
                    coins = data if isinstance(data, list) else data.get("coins", [])
                    now = time.time()
                    for item in coins:
                        mint = item.get("mint", item.get("address", ""))
                        if mint in self._seen:
                            continue
                        created_str = item.get("created", "")
                        created_ts = 0
                        if created_str:
                            try:
                                from datetime import datetime
                                created_ts = datetime.fromisoformat(created_str.replace("Z", "+00:00")).timestamp()
                            except Exception:
                                created_ts = now
                        age = now - created_ts
                        if age > 3600:
                            continue
                        self._seen.add(mint)
                        tokens.append(DiscoveredToken(
                            address=mint,
                            chain="solana",
                            symbol=item.get("symbol", ""),
                            name=item.get("name", ""),
                            source="pump_fun",
                            price_usd=float(item.get("price_usd", 0)),
                            liquidity_usd=float(item.get("liquidity", 0)),
                            volume_24h_usd=float(item.get("volume_24h", 0)),
                            created_at=created_ts,
                        ))
            except Exception as e:
                logger.debug(f"PumpFun error: {e}")
        return tokens
