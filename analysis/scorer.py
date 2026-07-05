import logging

logger = logging.getLogger(__name__)


class Scorer:
    def __init__(self, config: dict):
        self.config = config
        self.min_score = config.get("trading", {}).get("min_analysis_score", 60)

    async def score(self, contract: dict, wallets: dict, social: dict) -> float:
        weights = {"contract": 0.4, "wallets": 0.35, "social": 0.25}
        contract_score = contract.get("score", 50)
        wallet_score = wallets.get("score", 50)
        social_score = social.get("score", 50)
        total = (
            contract_score * weights["contract"]
            + wallet_score * weights["wallets"]
            + social_score * weights["social"]
        )
        return round(total, 1)
