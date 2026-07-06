import logging

import aiohttp

from .base import DiscoverySource, DiscoveredToken

logger = logging.getLogger(__name__)

PUMPFUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"
METADATA_PROGRAM = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"


class PumpFunRpcSource(DiscoverySource):
    def __init__(self, config: dict):
        super().__init__("pump_fun_rpc", config)
        self.rpc_url = config.get("rpc", {}).get("solana", SOLANA_RPC)
        self._seen_sigs: set[str] = set()
        self._seen_mints: set[str] = set()

    async def fetch(self) -> list[DiscoveredToken]:
        sigs = await self._get_recent_signatures()
        tokens = []
        for sig in sigs:
            if sig in self._seen_sigs:
                continue
            self._seen_sigs.add(sig)
            mints = await self._parse_new_mints(sig)
            for mint in mints:
                if mint in self._seen_mints:
                    continue
                self._seen_mints.add(mint)
                info = await self._get_token_info(mint)
                tokens.append(DiscoveredToken(
                    address=mint,
                    chain="solana",
                    symbol=info.get("symbol", "NEW"),
                    name=info.get("name", "New Token"),
                    source="pump_fun_rpc",
                    liquidity_usd=0,
                    volume_24h_usd=0,
                    extra={"rpc_discovered": True},
                ))
        return tokens

    async def _get_recent_signatures(self) -> list[str]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [PUMPFUN_PROGRAM, {"limit": 15}],
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(self.rpc_url, json=payload, timeout=10) as r:
                    if r.status != 200:
                        return []
                    data = await r.json()
                    return [item["signature"] for item in data.get("result", []) if "signature" in item]
        except Exception as e:
            logger.debug(f"getSignaturesForAddress error: {e}")
            return []

    async def _parse_new_mints(self, sig: str) -> list[str]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(self.rpc_url, json=payload, timeout=10) as r:
                    if r.status != 200:
                        return []
                    data = await r.json()
                    tx = data.get("result")
                    if not tx:
                        return []
                    meta = tx.get("meta", {})
                    if meta.get("err"):
                        return []
                    mints = set()
                    pre_mints = set()
                    for balance in meta.get("preTokenBalances", []):
                        if balance.get("mint"):
                            pre_mints.add(balance["mint"])
                    for balance in meta.get("postTokenBalances", []):
                        mint = balance.get("mint")
                        if mint and mint not in pre_mints:
                            mints.add(mint)
                    logs = meta.get("logMessages", [])
                    for log in logs:
                        if "initializeMint" in log or "Create" in log:
                            pass
                    return list(mints)
        except Exception as e:
            logger.debug(f"getTransaction error: {e}")
            return []

    async def _get_token_info(self, mint: str) -> dict:
        result = {"symbol": "?", "name": "?"}
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [mint, {"encoding": "jsonParsed"}],
            }
            async with aiohttp.ClientSession() as s:
                async with s.post(self.rpc_url, json=payload, timeout=10) as r:
                    if r.status != 200:
                        return result
                    data = await r.json()
                    value = data.get("result", {}).get("value")
                    if not value:
                        return result
                    parsed = value.get("data", {}).get("parsed", {})
                    info = parsed.get("info", {})
                    if parsed.get("type") == "mint":
                        supply = int(info.get("supply", "0"))
                        decimals = info.get("decimals", 0)
                        result["decimals"] = decimals
                        result["supply"] = supply
        except Exception:
            pass
        return result
