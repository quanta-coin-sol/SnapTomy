import logging

import aiohttp
from solana.rpc.api import Client as SolanaClient
from solders.pubkey import Pubkey

logger = logging.getLogger(__name__)
SOLANA_RPC = "https://api.mainnet-beta.solana.com"


MINT_LAYOUT_SIZE = 82


async def parse_mint_account(data: bytes) -> dict:
    if len(data) < MINT_LAYOUT_SIZE:
        return {"is_initialized": False}
    try:
        mint_authority_present = data[0] == 1 if len(data) > 0 else False
        mint_authority = None
        if mint_authority_present and len(data) >= 36:
            mint_authority = str(Pubkey.from_bytes(data[4:36]))
        supply = int.from_bytes(data[36:44], "little")
        decimals = data[44]
        is_initialized = data[45] == 1
        freeze_authority_present = data[46] == 1 if len(data) > 46 else False
        freeze_authority = None
        if freeze_authority_present and len(data) >= 82:
            freeze_authority = str(Pubkey.from_bytes(data[50:82]))
        return {
            "is_initialized": is_initialized,
            "supply": supply,
            "decimals": decimals,
            "mint_authority": mint_authority,
            "has_mint_auth": mint_authority_present and mint_authority is not None,
            "freeze_authority": freeze_authority,
            "has_freeze_auth": freeze_authority_present and freeze_authority is not None,
            "is_renounced": not mint_authority_present,
        }
    except Exception as e:
        logger.debug(f"Parse mint error: {e}")
        return {"is_initialized": False, "error": str(e)}


class ContractAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        rpc_url = config.get("rpc", {}).get("solana", SOLANA_RPC)
        self.client = SolanaClient(rpc_url)

    async def analyze(self, address: str, chain: str) -> dict:
        result = {
            "is_verified": False,
            "has_mint_auth": False,
            "has_freeze_auth": False,
            "owner_balance_percent": 0.0,
            "is_honeypot": False,
            "has_blacklist": False,
            "has_pause": False,
            "is_upgradeable": False,
            "liquidity_locked": False,
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
            pubkey = Pubkey.from_string(address)
            resp = self.client.get_account_info(pubkey)
            if resp.value and resp.value.data:
                parsed = await parse_mint_account(bytes(resp.value.data))
                if not parsed.get("is_initialized"):
                    result["issues"].append("Token not initialized")
                    result["score"] = 0
                    return result
                result["has_mint_auth"] = parsed.get("has_mint_auth", False)
                result["has_freeze_auth"] = parsed.get("has_freeze_auth", False)
                result["supply"] = parsed.get("supply", 0)
                result["decimals"] = parsed.get("decimals", 0)
                result["is_renounced"] = parsed.get("is_renounced", False)
                if result["has_mint_auth"]:
                    result["issues"].append("Mint authority present")
                    result["score"] -= 20
                if result["has_freeze_auth"]:
                    result["issues"].append("Freeze authority present")
                    result["score"] -= 15
                if result["is_renounced"]:
                    result["score"] += 20
                if result["supply"] == 0:
                    result["issues"].append("Zero supply")
                    result["score"] = 0
            else:
                result["issues"].append("Cannot fetch token account")
                result["score"] = 20
        except Exception as e:
            logger.debug(f"Solana analysis error: {e}")
            result["issues"].append(f"RPC error: {str(e)[:30]}")
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
