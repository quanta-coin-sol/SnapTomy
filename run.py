import asyncio
import logging
import os

import uvicorn
from telegram.ext import ApplicationBuilder

from api.server import app
from bot.handlers import setup_handlers
from config import load_config
from discovery.engine import DiscoveryEngine
from trading.engine import TradingEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    config = load_config()
    discovery = DiscoveryEngine(config)
    trading = TradingEngine(config)
    discovery.on_token_discovered(trading.enqueue_for_analysis)

    tg_token = config["bot_token"]
    tg_app = ApplicationBuilder().token(tg_token).build()
    setup_handlers(tg_app, config, discovery, trading)

    async def run_discovery():
        async for token in discovery.run():
            pass

    async def run_trading():
        await trading.run()

    async def run_telegram():
        await tg_app.run_polling(drop_pending_updates=True)

    async def run_api():
        uvicorn.run(app, host=config.get("api_host", "0.0.0.0"), port=config.get("api_port", 8002))

    await asyncio.gather(run_discovery(), run_trading(), run_telegram(), run_api())


if __name__ == "__main__":
    asyncio.run(main())
