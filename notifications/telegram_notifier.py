import logging

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, config: dict, bot=None):
        self.config = config
        self.bot = bot
        self.admin_ids = config.get("admin_ids", [])

    async def send(self, message: str):
        if not self.bot or not self.admin_ids:
            logger.debug(f"Telegram: {message}")
            return
        for uid in self.admin_ids:
            try:
                await self.bot.send_message(chat_id=uid, text=message)
            except Exception as e:
                logger.error(f"Telegram send to {uid}: {e}")
