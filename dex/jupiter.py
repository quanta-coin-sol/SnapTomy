import logging

import aiohttp
from solana.rpc.api import Client as SolanaClient
from solders.commitment_config import CommitmentLevel
from solders.keypair import Keypair

logger = logging.getLogger(__name__)

JUPITER_QUOTE = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP = "https://quote-api.jup.ag/v6/swap"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
WSOL_MINT = "So11111111111111111111111111111111111111112"


class JupiterDEX:
    def __init__(self, config: dict, wallet: Keypair = None):
        self.config = config
        self.wallet = wallet
        self.rpc = config.get("rpc", {}).get("solana", SOLANA_RPC)
        self.client = SolanaClient(self.rpc)

    async def get_quote(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int = 500) -> dict:
        url = f"{JUPITER_QUOTE}?inputMint={input_mint}&outputMint={output_mint}&amount={amount}&slippageBps={slippage_bps}"
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=15) as r:
                if r.status != 200:
                    logger.error(f"Jupiter quote error: {r.status}")
                    return None
                return await r.json()

    async def swap(self, quote_response: dict, user_pubkey: str) -> dict:
        payload = {
            "quoteResponse": quote_response,
            "userPublicKey": user_pubkey,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(JUPITER_SWAP, json=payload, timeout=15) as r:
                if r.status != 200:
                    logger.error(f"Jupiter swap error: {r.status}")
                    return None
                return await r.json()

    async def buy(self, mint: str, amount_sol: int, wallet: Keypair) -> dict:
        quote = await self.get_quote(WSOL_MINT, mint, amount_sol)
        if not quote:
            return {"success": False, "error": "No quote"}
        swap_data = await self.swap(quote, str(wallet.pubkey()))
        if not swap_data:
            return {"success": False, "error": "No swap tx"}
        return {"success": True, "quote": quote, "swap": swap_data}

    async def sell(self, mint: str, amount_tokens: int, wallet: Keypair) -> dict:
        quote = await self.get_quote(mint, WSOL_MINT, amount_tokens)
        if not quote:
            return {"success": False, "error": "No quote"}
        swap_data = await self.swap(quote, str(wallet.pubkey()))
        if not swap_data:
            return {"success": False, "error": "No swap tx"}
        return {"success": True, "quote": quote, "swap": swap_data}
