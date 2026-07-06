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

    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()

    logger.info("SnapTomy starting (paper trading mode)" if config.get("paper_trading") else "SnapTomy starting (LIVE mode)")

    task = asyncio.create_task(trading.run())

    async for token in discovery.run():
        pass

    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    await tg_app.updater.stop()
    await tg_app.stop()
    await tg_app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
