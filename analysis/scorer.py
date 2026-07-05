import logging

logger = logging.getLogger(__name__)


class Scorer:
    def __init__(self, config: dict):
        self.config = config
        trading = config.get("trading", {})
        self.min_score = trading.get("min_analysis_score", 70)
        self.entry = trading.get("entry", {})

    async def score(self, data: dict, contract: dict, wallets: dict, social: dict) -> dict:
        liquidity = contract.get("liquidity_usd", 0)
        volume = data.get("volume_24h_usd", 0)
        market_cap = data.get("market_cap", 0)

        liq_score = self._score_liquidity(liquidity)
        contract_score = contract.get("score", 50)
        wallet_score = wallets.get("score", 50)
        social_score = social.get("score", 50)
        momentum_score = self._score_momentum(volume, liquidity)

        overall = (
            liq_score * 0.20
            + contract_score * 0.30
            + wallet_score * 0.20
            + social_score * 0.10
            + momentum_score * 0.20
        )

        recommendation = self._get_recommendation(overall, liquidity, contract)

        return {
            "overall": round(overall, 1),
            "subscores": {
                "liquidity": liq_score,
                "contract_safety": contract_score,
                "holder_distribution": wallet_score,
                "community": social_score,
                "momentum": momentum_score,
            },
            "recommendation": recommendation,
        }

    def _score_liquidity(self, liquidity_usd: float) -> float:
        if liquidity_usd >= 100000:
            return 90
        elif liquidity_usd >= 50000:
            return 75
        elif liquidity_usd >= 30000:
            return 60
        elif liquidity_usd >= 10000:
            return 40
        else:
            return 20

    def _score_momentum(self, volume: float, liquidity: float) -> float:
        if liquidity == 0:
            return 30
        ratio = volume / liquidity
        if ratio >= 5:
            return 85
        elif ratio >= 2:
            return 70
        elif ratio >= 0.5:
            return 50
        else:
            return 30

    def _get_recommendation(self, score: float, liquidity: float, contract: dict) -> str:
        if score >= 90 and liquidity >= 50000:
            return "STRONG BUY"
        elif score >= 80 and liquidity >= 30000:
            return "BUY"
        elif score >= 70:
            return "BUY SMALL"
        elif score >= 50:
            return "WATCH"
        else:
            return "IGNORE"
