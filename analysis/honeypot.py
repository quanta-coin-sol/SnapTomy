import logging

logger = logging.getLogger(__name__)


class HoneypotDetector:
    def __init__(self, config: dict):
        self.config = config

    async def check(self, address: str, chain: str) -> dict:
        return {"is_honeypot": False, "can_sell": True, "buy_tax": 0, "sell_tax": 0, "issues": []}
