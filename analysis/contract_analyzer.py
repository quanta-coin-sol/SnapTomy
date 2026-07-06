import logging

import aiohttp
from solders.pubkey import Pubkey

logger = logging.getLogger(__name__)

SOLANA_RPC = "https://api.mainnet-beta.solana.com"


class ContractAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self.rpc_url = config.get("rpc", {}).get("solana", SOLANA_RPC)

    async def analyze(self, address: str, chain: str) -> dict:
        result = {
            "has_mint_auth": False,
            "has_freeze_auth": False,
            "is_honeypot": False,
            "liquidity_usd": 0.0,
            "supply": 0,
            "decimals": 0,
            "score": 50,
            "issues": [],
        }
        if chain == "solana":
            onchain = await self._analyze_solana(address)
            result.update(onchain)
        liq = await self._get_liquidity(address)
        result["liquidity_usd"] = liq
        if liq >= 30000:
            result["score"] = min(100, result["score"] + 15)
        else:
            result["issues"].append(f"Low liquidity (${liq:.0f})")
        return result

    async def _analyze_solana(self, address: str) -> dict:
        result = {"score": 50, "issues": []}
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [address, {"encoding": "jsonParsed"}],
            }
            async with aiohttp.ClientSession() as s:
                async with s.post(self.rpc_url, json=payload, timeout=15) as r:
                    if r.status != 200:
                        result["issues"].append("RPC error")
                        return result
                    data = await r.json()
                    value = data.get("result", {}).get("value")
                    if not value:
                        result["issues"].append("Token not found on chain")
                        result["score"] = 0
                        return result
                    parsed = value.get("data", {}).get("parsed", {})
                    info = parsed.get("info", {})
                    if parsed.get("type") == "mint":
                        result["supply"] = int(info.get("supply", "0"))
                        result["decimals"] = info.get("decimals", 0)
                        mint_authority = info.get("mintAuthority")
                        freeze_authority = info.get("freezeAuthority")
                        result["has_mint_auth"] = mint_authority is not None
                        result["has_freeze_auth"] = freeze_authority is not None
                        result["is_renounced"] = mint_authority is None
                        if result["has_mint_auth"]:
                            result["issues"].append("Mint authority present")
                            result["score"] -= 20
                        if result["has_freeze_auth"]:
                            result["issues"].append("Freeze authority present")
                            result["score"] -= 15
                        if result["is_renounced"]:
                            result["score"] += 20
        except Exception as e:
            logger.debug(f"Solana RPC error: {e}")
            result["issues"].append(f"RPC error")
            result["score"] = 20
        return result

    async def _get_liquidity(self, address: str) -> float:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://api.dexscreener.com/latest/dex/tokens/{address}", timeout=10) as r:
                    if r.status != 200:
                        return 0
                    data = await r.json()
                    pairs = data.get("pairs", [])
                    if not pairs:
                        return 0
                    return float(pairs[0].get("liquidity", {}).get("usd", 0))
        except Exception:
            return 0
