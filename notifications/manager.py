import logging
from typing import Optional

from .telegram_notifier import TelegramNotifier
from .webhook_notifier import WebhookNotifier

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self, config: dict, bot=None):
        self.config = config
        self.telegram = TelegramNotifier(config, bot) if config.get("notification", {}).get("telegram_enabled") else None
        self.webhook = WebhookNotifier(config) if config.get("notification", {}).get("webhook_enabled") else None

    async def send_buy_alert(self, token: dict, score: float, tx: Optional[str] = None):
        msg = f"BUY: {token.get('symbol', '?')} | Score: {score} | ${token.get('amount_usd', 0)}"
        if self.telegram:
            await self.telegram.send(msg)
        if self.webhook:
            await self.webhook.send("buy", token, score, tx)

    async def send_sell_alert(self, position: dict, pnl: float, tx: Optional[str] = None):
        msg = f"SELL: {position.get('symbol', '?')} | PnL: {pnl:+.2f}%"
        if self.telegram:
            await self.telegram.send(msg)
        if self.webhook:
            await self.webhook.send("sell", position, pnl, tx)

    async def send_rug_alert(self, position: dict, issues: list[str]):
        msg = f"RUG DETECTED: {position.get('symbol', '?')} | {', '.join(issues)}"
        if self.telegram:
            await self.telegram.send(msg)
