import asyncio
import logging

from telegram.ext import ApplicationBuilder

from bot.handlers import setup_handlers
from config import load_config
from discovery.engine import DiscoveryEngine
from notifications.manager import NotificationManager
from trading.engine import TradingEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    config = load_config()
    tg_token = config["bot_token"]
    tg_app = ApplicationBuilder().token(tg_token).build()
    notification_mgr = NotificationManager(config, tg_app.bot if config.get("notification", {}).get("telegram_enabled") else None)
    discovery = DiscoveryEngine(config)
    trading = TradingEngine(config, notification_mgr)
    discovery.on_token_discovered(trading.enqueue_for_analysis)
    setup_handlers(tg_app, config, discovery, trading)

    async def run_discovery():
        async for token in discovery.run():
            pass

    async def run_trading():
        await trading.run()

    async def run_telegram():
        await tg_app.run_polling(drop_pending_updates=True)

    logger.info("SnapTomy starting (paper trading mode)" if config.get("paper_trading") else "SnapTomy starting (LIVE mode)")
    await asyncio.gather(run_discovery(), run_trading(), run_telegram())


if __name__ == "__main__":
    asyncio.run(main())
