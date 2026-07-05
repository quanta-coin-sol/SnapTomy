import logging

logger = logging.getLogger(__name__)


class TradeExecutor:
    def __init__(self, config: dict):
        self.config = config

    async def buy(self, address: str, chain: str, amount_usd: float) -> dict:
        logger.info(f"BUY {address[:8]}... on {chain} for ${amount_usd}")
        return {"success": True, "tx": None, "amount_usd": amount_usd}

    async def sell(self, address: str, chain: str, amount_pct: float = 100.0) -> dict:
        logger.info(f"SELL {address[:8]}... on {chain} ({amount_pct}%)")
        return {"success": True, "tx": None, "amount_pct": amount_pct}
