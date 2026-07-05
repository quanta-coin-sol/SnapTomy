import logging
import time

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(self, config: dict):
        self.config = config
        risk = config.get("risk", {})
        self.max_rug_risk = risk.get("max_rug_risk_percent", 60)
        self.max_wallet_conc = risk.get("max_wallet_concentration_percent", 20)
        self.min_holders = risk.get("min_holder_count", 50)
        self.max_owner_balance = risk.get("max_owner_balance_percent", 5)
        self.daily_loss_limit = risk.get("daily_loss_limit_usd", 500)
        self.max_chain_exposure = risk.get("max_chain_exposure_percent", 40)
        self.circuit_breaker = risk.get("circuit_breaker_pnl_percent", -30)
        self._daily_loss = 0.0
        self._last_reset = time.time()

    def _reset_daily(self):
        if time.time() - self._last_reset > 86400:
            self._daily_loss = 0.0
            self._last_reset = time.time()

    async def assess(self, contract: dict, wallets: dict, score: float) -> dict:
        issues = []
        if wallets.get("top_holder_concentration", 0) > self.max_wallet_conc:
            issues.append(f"Top holder concentration {wallets['top_holder_concentration']:.1f}% > {self.max_wallet_conc}%")
        if contract.get("owner_balance_percent", 0) > self.max_owner_balance:
            issues.append(f"Owner balance {contract['owner_balance_percent']:.1f}% > {self.max_owner_balance}%")
        if contract.get("has_mint_auth"):
            issues.append("Mint authority not renounced")
        if contract.get("has_freeze_auth"):
            issues.append("Freeze authority not renounced")
        if contract.get("is_honeypot"):
            issues.append("Honeypot detected")
        if contract.get("has_blacklist"):
            issues.append("Blacklist function exists")
        if contract.get("has_pause"):
            issues.append("Trading pause function exists")
        if contract.get("is_upgradeable"):
            issues.append("Contract is upgradeable")
        if not contract.get("liquidity_locked") and contract.get("liquidity_usd", 0) > 0:
            issues.append("Liquidity not locked")
        risk_pct = min(100, len(issues) * 12)
        if score > 80:
            risk_pct = max(0, risk_pct - 15)
        elif score > 60:
            risk_pct = max(0, risk_pct - 5)
        return {"risk_percent": risk_pct, "issues": issues, "approved": risk_pct < self.max_rug_risk}
