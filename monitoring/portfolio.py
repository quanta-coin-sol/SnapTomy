import logging
import time

logger = logging.getLogger(__name__)


class PortfolioTracker:
    def __init__(self, config: dict):
        self.config = config
        self.start_time = time.time()
        self.balance_usd = config.get("initial_balance_usd", 10000)
        self.peak_balance = self.balance_usd

    def update(self, positions: list[dict], balance: float):
        self.balance_usd = balance
        total_value = balance + sum(p.get("current_value_usd", 0) for p in positions if p["closed_at"] is None)
        if total_value > self.peak_balance:
            self.peak_balance = total_value

    def get_metrics(self, positions: list[dict]) -> dict:
        open_positions = [p for p in positions if p["closed_at"] is None]
        closed_positions = [p for p in positions if p["closed_at"] is not None]

        open_value = sum(p.get("current_value_usd", 0) for p in open_positions)
        total_value = self.balance_usd + open_value

        realized_pnl = sum(p.get("pnl_usd", 0) for p in closed_positions if p["pnl_usd"] is not None)
        unrealized_pnl = sum(p.get("pnl_usd", 0) for p in open_positions if p["pnl_usd"] is not None)

        wins = len([p for p in closed_positions if p.get("pnl_usd", 0) > 0])
        losses = len([p for p in closed_positions if p.get("pnl_usd", 0) <= 0])
        total_closed = wins + losses
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

        total_invested = sum(p.get("amount_usd", 0) for p in positions)
        roi = ((total_value - total_invested) / total_invested * 100) if total_invested > 0 else 0

        drawdown = ((self.peak_balance - total_value) / self.peak_balance * 100) if self.peak_balance > 0 else 0

        avg_hold = 0
        if closed_positions:
            holds = []
            for p in closed_positions:
                if p.get("opened_at") and p.get("closed_at"):
                    holds.append(p["closed_at"] - p["opened_at"])
            avg_hold = sum(holds) / len(holds) if holds else 0

        return {
            "balance_usd": round(self.balance_usd, 2),
            "open_value_usd": round(open_value, 2),
            "total_value_usd": round(total_value, 2),
            "realized_pnl_usd": round(realized_pnl, 2),
            "unrealized_pnl_usd": round(unrealized_pnl, 2),
            "win_rate_pct": round(win_rate, 1),
            "wins": wins,
            "losses": losses,
            "roi_pct": round(roi, 2),
            "max_drawdown_pct": round(drawdown, 2),
            "avg_hold_seconds": round(avg_hold),
            "open_positions": len(open_positions),
            "total_trades": total_closed,
        }
