import logging

logger = logging.getLogger(__name__)

JUPITER_API = "https://quote-api.jup.ag/v6"


class JupiterDEX:
    def __init__(self, config: dict):
        self.config = config

    async def quote(self, input_mint: str, output_mint: str, amount: int) -> dict:
        return {}

    async def swap(self, quote: dict, wallet_pk: str) -> dict:
        return {"success": True, "tx": None}
