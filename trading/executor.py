import logging
import time
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6"


class TradeExecutor:
    def __init__(self, config: dict):
        self.config = config
        self.paper_mode = config.get("paper_trading", True)
        self.balance_usd = config.get("initial_balance_usd", 10000)
        self.positions_value = 0.0

    async def buy(self, address: str, chain: str, amount_usd: float) -> dict:
        if self.paper_mode:
            return await self._paper_buy(address, chain, amount_usd)
        return await self._live_buy(address, chain, amount_usd)

    async def sell(self, address: str, chain: str, amount_pct: float = 100.0) -> dict:
        if self.paper_mode:
            return await self._paper_sell(address, chain, amount_pct)
        return await self._live_sell(address, chain, amount_pct)

    async def get_price(self, address: str, chain: str) -> Optional[float]:
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=10) as r:
                    if r.status != 200:
                        return None
                    data = await r.json()
                    pairs = data.get("pairs", [])
                    if not pairs:
                        return None
                    return float(pairs[0].get("priceUsd", 0))
        except Exception as e:
            logger.debug(f"Price fetch error: {e}")
            return None

    async def _paper_buy(self, address: str, chain: str, amount_usd: float) -> dict:
        if amount_usd > self.balance_usd:
            return {"success": False, "error": "Insufficient paper balance"}
        price = await self.get_price(address, chain) or 0
        self.balance_usd -= amount_usd
        self.positions_value += amount_usd
        logger.info(f"[PAPER] BUY ${amount_usd} of {address[:8]}... on {chain} @ ${price:.8f}")
        return {"success": True, "tx": f"paper_{int(time.time())}", "amount_usd": amount_usd, "price": price, "paper": True}

    async def _paper_sell(self, address: str, chain: str, amount_pct: float) -> dict:
        price = await self.get_price(address, chain) or 0
        proceeds = self.positions_value * (amount_pct / 100)
        self.balance_usd += proceeds
        self.positions_value -= proceeds
        logger.info(f"[PAPER] SELL {amount_pct}% of {address[:8]}... on {chain} @ ${price:.8f}")
        return {"success": True, "tx": f"paper_{int(time.time())}", "amount_pct": amount_pct, "proceeds": proceeds, "price": price, "paper": True}

    async def _live_buy(self, address: str, chain: str, amount_usd: float) -> dict:
        return {"success": False, "error": "Live trading not yet implemented"}

    async def _live_sell(self, address: str, chain: str, amount_pct: float) -> dict:
        return {"success": False, "error": "Live trading not yet implemented"}
