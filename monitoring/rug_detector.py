import logging
import time

import aiohttp

logger = logging.getLogger(__name__)


class RugDetector:
    def __init__(self, config: dict):
        self.config = config
        risk = config.get("risk", {})
        self.max_rug_risk = risk.get("max_rug_risk_percent", 60)

    async def check(self, position: dict) -> dict:
        issues = []
        address = position["address"]
        chain = position["chain"]

        current_price = await self._fetch_price(address)
        if current_price is None:
            issues.append("Price fetch failed")
            risk_pct = 50
            return {"risk_percent": risk_pct, "issues": issues, "is_rug": risk_pct >= self.max_rug_risk, "price": None}

        entry_price = position["entry_price"]
        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0
        price_drop_pct = ((position["highest_price"] - current_price) / position["highest_price"]) * 100 if position["highest_price"] else 0

        if pnl_pct <= -50:
            issues.append(f"Price crashed {pnl_pct:.1f}% from entry")
        if price_drop_pct >= 80:
            issues.append(f"Price dropped {price_drop_pct:.1f}% from high")
        if current_price <= 0:
            issues.append("Token price effectively zero")

        liquidity = await self._fetch_liquidity(address)
        if liquidity is not None and liquidity < 100:
            issues.append(f"Liquidity near zero (${liquidity:.2f})")

        risk_pct = min(100, len(issues) * 30)
        if position.get("pnl_percent", 0) < 0:
            risk_pct = min(100, risk_pct + 10)

        return {
            "risk_percent": risk_pct,
            "issues": issues,
            "is_rug": risk_pct >= self.max_rug_risk,
            "price": current_price,
            "pnl_pct": pnl_pct,
        }

    async def _fetch_price(self, address: str) -> float:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://api.dexscreener.com/latest/dex/tokens/{address}", timeout=10) as r:
                    if r.status != 200:
                        return None
                    data = await r.json()
                    pairs = data.get("pairs", [])
                    if not pairs:
                        return None
                    return float(pairs[0].get("priceUsd", 0))
        except Exception as e:
            logger.debug(f"RugDetector price fetch: {e}")
            return None

    async def _fetch_liquidity(self, address: str) -> float:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://api.dexscreener.com/latest/dex/tokens/{address}", timeout=10) as r:
                    if r.status != 200:
                        return None
                    data = await r.json()
                    pairs = data.get("pairs", [])
                    if not pairs:
                        return None
                    return float(pairs[0].get("liquidity", {}).get("usd", 0))
        except Exception as e:
            logger.debug(f"RugDetector liquidity fetch: {e}")
            return None
