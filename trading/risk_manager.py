import logging

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(self, config: dict):
        self.config = config
        self.max_rug_risk = config.get("risk", {}).get("max_rug_risk_percent", 70)
        self.max_wallet_conc = config.get("risk", {}).get("max_wallet_concentration_percent", 30)
        self.min_holders = config.get("risk", {}).get("min_holder_count", 50)
        self.max_owner_balance = config.get("risk", {}).get("max_owner_balance_percent", 5)

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
        risk_pct = min(100, len(issues) * 20)
        if score > 80:
            risk_pct = max(0, risk_pct - 15)
        return {"risk_percent": risk_pct, "issues": issues, "approved": risk_pct < self.max_rug_risk}
