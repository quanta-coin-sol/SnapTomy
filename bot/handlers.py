import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


def setup_handlers(app, config, discovery, trading):
    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("status", _cmd_status))
    app.add_handler(CommandHandler("positions", _cmd_positions))
    app.add_handler(CommandHandler("stop", _cmd_stop))
    return app


async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("SnapTomy is running. Use /status to check bot health.")


async def _cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is operational.")


async def _cmd_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("No open positions.")


async def _cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Stop command received.")
