import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class PositionManager:
    def __init__(self, config: dict):
        self.config = config
        self.positions_file = "positions.json"
        self.positions: list[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file) as f:
                    self.positions = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load positions: {e}")

    def _save(self):
        try:
            with open(self.positions_file, "w") as f:
                json.dump(self.positions, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save positions: {e}")

    def open_position(self, address: str, chain: str, symbol: str,
                      entry_price: float, amount_usd: float) -> dict:
        pos = {
            "address": address,
            "chain": chain,
            "symbol": symbol,
            "entry_price": entry_price,
            "amount_usd": amount_usd,
            "current_value_usd": amount_usd,
            "pnl_percent": 0.0,
            "opened_at": datetime.utcnow().isoformat(),
            "closed_at": None,
        }
        self.positions.append(pos)
        self._save()
        return pos

    def close_position(self, address: str) -> Optional[dict]:
        for pos in self.positions:
            if pos["address"] == address and pos["closed_at"] is None:
                pos["closed_at"] = datetime.utcnow().isoformat()
                self._save()
                return pos
        return None

    def get_open_positions(self) -> list[dict]:
        return [p for p in self.positions if p["closed_at"] is None]

    def get_position(self, address: str) -> Optional[dict]:
        for p in self.positions:
            if p["address"] == address:
                return p
        return None
