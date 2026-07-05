import logging
from typing import Optional

from .telegram_notifier import TelegramNotifier
from .webhook_notifier import WebhookNotifier

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self, config: dict, bot=None):
        self.config = config
        notif_cfg = config.get("notification", {})
        self.telegram = TelegramNotifier(config, bot) if notif_cfg.get("telegram_enabled") else None
        self.webhook = WebhookNotifier(config) if notif_cfg.get("webhook_enabled") else None
        self.alert_on_buy = notif_cfg.get("alert_on_buy", True)
        self.alert_on_sell = notif_cfg.get("alert_on_sell", True)
        self.alert_on_rug = notif_cfg.get("alert_on_rug", True)

    async def send_buy_alert(self, token: dict, score: float, tx: Optional[str] = None):
        if not self.alert_on_buy:
            return
        msg = (
            f"BUY: {token.get('symbol', '?')} | Score: {score}\n"
            f"Amount: ${token.get('amount_usd', 0):.2f}\n"
            f"Address: {token.get('address', '?')[:12]}..."
        )
        await self._send(msg)

    async def send_sell_alert(self, position: dict, pnl: float, tx: Optional[str] = None):
        if not self.alert_on_sell:
            return
        reason = position.get("exit_reason", "manual")
        msg = (
            f"SELL: {position.get('symbol', '?')} | PnL: {pnl:+.2f}%\n"
            f"Reason: {reason}\n"
            f"Address: {position.get('address', '?')[:12]}..."
        )
        await self._send(msg)

    async def send_rug_alert(self, position: dict, issues: list[str]):
        if not self.alert_on_rug:
            return
        msg = (
            f"RUG DETECTED: {position.get('symbol', '?')}\n"
            f"Issues: {', '.join(issues)}\n"
            f"Address: {position.get('address', '?')[:12]}..."
        )
        await self._send(msg)

    async def _send(self, message: str):
        if self.telegram:
            await self.telegram.send(message)
        if self.webhook:
            await self.webhook.send("alert", {"message": message})
