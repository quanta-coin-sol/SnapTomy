import json
import logging
import os
import time
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
                      entry_price: float, amount_usd: float, score: float,
                      tx: Optional[str] = None) -> dict:
        pos = {
            "address": address,
            "chain": chain,
            "symbol": symbol,
            "entry_price": entry_price,
            "amount_usd": amount_usd,
            "current_value_usd": amount_usd,
            "pnl_percent": 0.0,
            "pnl_usd": 0.0,
            "score": score,
            "highest_price": entry_price,
            "lowest_price": entry_price,
            "stop_loss": entry_price * (1 + self.config.get("trading", {}).get("exit", {}).get("stop_loss_percent", -15) / 100),
            "take_profit": entry_price * (1 + self.config.get("trading", {}).get("exit", {}).get("take_profit_percent", 50) / 100),
            "trailing_activated": False,
            "trailing_stop": None,
            "opened_at": time.time(),
            "closed_at": None,
            "exit_reason": None,
            "tx_open": tx,
            "tx_close": None,
        }
        self.positions.append(pos)
        self._save()
        return pos

    def update_price(self, address: str, price: float):
        for pos in self.positions:
            if pos["address"] == address and pos["closed_at"] is None:
                pos["current_value_usd"] = pos["amount_usd"] * (price / pos["entry_price"]) if pos["entry_price"] else 0
                pos["pnl_percent"] = ((price - pos["entry_price"]) / pos["entry_price"]) * 100 if pos["entry_price"] else 0
                pos["pnl_usd"] = pos["current_value_usd"] - pos["amount_usd"]
                if price > pos["highest_price"]:
                    pos["highest_price"] = price
                if price < pos["lowest_price"]:
                    pos["lowest_price"] = price
                self._check_trailing_stop(pos, price)
                return pos
        return None

    def _check_trailing_stop(self, pos: dict, price: float):
        entry = pos["entry_price"]
        pnl_pct = ((price - entry) / entry) * 100
        activation = self.config.get("trading", {}).get("exit", {}).get("trailing_stop_activation_percent", 20)
        distance = self.config.get("trading", {}).get("exit", {}).get("trailing_stop_distance_percent", 10)
        if not pos["trailing_activated"] and pnl_pct >= activation:
            pos["trailing_activated"] = True
            pos["trailing_stop"] = price * (1 - distance / 100)
            logger.info(f"Trailing stop activated for {pos['symbol']} at ${price:.8f}")
        if pos["trailing_activated"]:
            new_stop = price * (1 - distance / 100)
            if new_stop > pos["trailing_stop"]:
                pos["trailing_stop"] = new_stop

    def close_position(self, address: str, reason: str = None, tx: str = None) -> Optional[dict]:
        for pos in self.positions:
            if pos["address"] == address and pos["closed_at"] is None:
                pos["closed_at"] = time.time()
                pos["exit_reason"] = reason
                pos["tx_close"] = tx
                self._save()
                return pos
        return None

    def get_open_positions(self) -> list[dict]:
        return [p for p in self.positions if p["closed_at"] is None]

    def get_closed_positions(self) -> list[dict]:
        return [p for p in self.positions if p["closed_at"] is not None]

    def get_position(self, address: str) -> Optional[dict]:
        for p in self.positions:
            if p["address"] == address:
                return p
        return None

    def get_total_pnl(self) -> float:
        return sum(p.get("pnl_usd", 0) for p in self.positions if p["closed_at"] is not None)
