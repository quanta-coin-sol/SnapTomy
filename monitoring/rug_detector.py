import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RugDetector:
    def __init__(self, config: dict):
        self.config = config
        self.max_rug_risk = config.get("risk", {}).get("max_rug_risk_percent", 70)

    async def check(self, position: dict) -> dict:
        issues = []
        risk_pct = 0
        return {"risk_percent": risk_pct, "issues": issues, "is_rug": risk_pct >= self.max_rug_risk}
