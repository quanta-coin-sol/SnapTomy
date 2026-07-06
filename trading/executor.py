import logging
import time
from decimal import Decimal

import aiohttp
from solana.rpc.api import Client as SolanaClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from dex.jupiter import JupiterDEX
from wallets.solana import SolanaWallet

logger = logging.getLogger(__name__)

SOLANA_RPC = "https://api.mainnet-beta.solana.com"
WSOL_MINT = "So11111111111111111111111111111111111111112"
LAMPORTS_PER_SOL = 1_000_000_000


class TradeExecutor:
    def __init__(self, config: dict):
        self.config = config
        self.paper_mode = config.get("paper_trading", True)
        self.balance_usd = config.get("initial_balance_usd", 10000)
        self.positions_value = 0.0
        self.wallet: Keypair = None
        self.jupiter: JupiterDEX = None
        priv_key = config.get("wallet", {}).get("solana_private_key")
        if priv_key and not self.paper_mode:
            sw = SolanaWallet(priv_key)
            self.wallet = sw.keypair
            self.jupiter = JupiterDEX(config, self.wallet)
            logger.info(f"Live wallet: {self.wallet.pubkey()}")

    async def buy(self, address: str, chain: str, amount_usd: float) -> dict:
        if self.paper_mode:
            return await self._paper_buy(address, chain, amount_usd)
        return await self._live_buy(address, chain, amount_usd)

    async def sell(self, address: str, chain: str, amount_pct: float = 100.0) -> dict:
        if self.paper_mode:
            return await self._paper_sell(address, chain, amount_pct)
        return await self._live_sell(address, chain, amount_pct)

    async def get_price(self, address: str) -> float:
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
            logger.debug(f"Price fetch: {e}")
            return None

    async def get_balance(self, mint: str = None) -> float:
        if not self.wallet:
            return self.balance_usd
        client = SolanaClient(self.config.get("rpc", {}).get("solana", SOLANA_RPC))
        if mint and mint != WSOL_MINT:
            try:
                resp = client.get_token_account_balance_by_mint(self.wallet.pubkey(), Pubkey.from_string(mint))
                if resp.value:
                    return float(resp.value.ui_amount) if resp.value.ui_amount else 0
            except Exception:
                pass
            return 0
        resp = client.get_balance(self.wallet.pubkey())
        return (resp.value / LAMPORTS_PER_SOL) if resp.value else 0

    async def _paper_buy(self, address: str, chain: str, amount_usd: float) -> dict:
        if amount_usd > self.balance_usd:
            return {"success": False, "error": "Insufficient paper balance"}
        price = await self.get_price(address) or 0
        self.balance_usd -= amount_usd
        self.positions_value += amount_usd
        logger.info(f"[PAPER] BUY ${amount_usd:.2f} {address[:8]}... @ ${price:.8f}")
        return {"success": True, "tx": f"paper_{int(time.time())}", "amount_usd": amount_usd, "price": price, "paper": True}

    async def _paper_sell(self, address: str, chain: str, amount_pct: float) -> dict:
        price = await self.get_price(address) or 0
        proceeds = self.positions_value * (amount_pct / 100)
        self.balance_usd += proceeds
        self.positions_value -= proceeds
        logger.info(f"[PAPER] SELL {amount_pct}% {address[:8]}... @ ${price:.8f}")
        return {"success": True, "tx": f"paper_{int(time.time())}", "proceeds": proceeds, "price": price, "paper": True}

    async def _live_buy(self, address: str, chain: str, amount_usd: float) -> dict:
        if not self.wallet:
            return {"success": False, "error": "No wallet configured"}
        sol_balance = await self.get_balance()
        sol_needed = amount_usd / 150
        if sol_balance < sol_needed:
            return {"success": False, "error": f"Insufficient SOL ({sol_balance:.3f} < {sol_needed:.3f})"}
        lamports = int(sol_needed * LAMPORTS_PER_SOL)
        quote = await self.jupiter.get_quote(WSOL_MINT, address, lamports)
        if not quote:
            return {"success": False, "error": "Jupiter quote failed"}
        swap_data = await self.jupiter.swap(quote, str(self.wallet.pubkey()))
        if not swap_data:
            return {"success": False, "error": "Jupiter swap failed"}
        return {"success": True, "quote": quote, "swap": swap_data, "amount_usd": amount_usd}

    async def _live_sell(self, address: str, chain: str, amount_pct: float) -> dict:
        if not self.wallet:
            return {"success": False, "error": "No wallet configured"}
        return {"success": False, "error": "Live sell NYI"}
