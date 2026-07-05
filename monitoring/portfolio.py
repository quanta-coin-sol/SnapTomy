import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class PortfolioTracker:
    def __init__(self, config: dict):
        self.config = config
        self.total_invested = 0.0
        self.total_pnl = 0.0

    def update(self, positions: list[dict]):
        self.total_invested = sum(p.get("amount_usd", 0) for p in positions if p["closed_at"] is None)
        total_value = sum(p.get("current_value_usd", 0) for p in positions if p["closed_at"] is None)
        self.total_pnl = total_value - self.total_invested
