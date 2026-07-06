import json
import logging
import os
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

AWAIT_BUY_ADDRESS, AWAIT_BUY_AMOUNT, AWAIT_SELL_ADDRESS, AWAIT_SELL_PCT = range(4)

_trading = None
_discovery = None
_config = None
_admin_ids: set[int] = set()


def setup_handlers(app, config, discovery, trading):
    global _trading, _discovery, _config
    _trading = trading
    _discovery = discovery
    _config = config
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("positions", cmd_positions))
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("buy", buy_start))
    app.add_handler(CommandHandler("sell", sell_start))
    app.add_handler(CommandHandler("cancel", cancel))
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(buy_start, pattern="^buy$")],
        states={
            AWAIT_BUY_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_address)],
            AWAIT_BUY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    conv2 = ConversationHandler(
        entry_points=[CallbackQueryHandler(sell_start, pattern="^sell$")],
        states={
            AWAIT_SELL_ADDRESS: [CallbackQueryHandler(sell_address, pattern="^sell_")],
            AWAIT_SELL_PCT: [CallbackQueryHandler(sell_percent, pattern="^sellpct_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv2)
    for pattern, handler_fn in [
        ("^menu$", cmd_menu),
        ("^portfolio$", _show_portfolio),
        ("^positions$", _show_positions),
        ("^settings$", _show_settings),
        ("^help$", cmd_help),
        ("^trading_toggle$", _toggle_trading),
        ("^mode_toggle$", _toggle_mode),
    ]:
        app.add_handler(CallbackQueryHandler(handler_fn, pattern=pattern))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_menu))
    return app


def _is_admin(uid: int) -> bool:
    admin_list = _config.get("admin_ids", [])
    return uid in _admin_ids or uid in admin_list


def _save_admin(uid: int):
    _admin_ids.add(uid)
    existing = _config.get("admin_ids", [])
    if uid not in existing:
        existing.append(uid)
        _config["admin_ids"] = existing
        path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        try:
            with open(path, "w") as f:
                json.dump(_config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save admin_ids: {e}")


async def _ensure_admin(update: Update):
    uid = update.effective_user.id
    if not _is_admin(uid):
        _save_admin(uid)
        await update.effective_message.reply_text(
            f"You've been registered as admin (ID: {uid}). You'll now receive alerts."
        )


async def main_menu(update: Update, text: str = None):
    keyboard = [
        [InlineKeyboardButton("Portfolio", callback_data="portfolio"),
         InlineKeyboardButton("Positions", callback_data="positions")],
        [InlineKeyboardButton("Buy Token", callback_data="buy"),
         InlineKeyboardButton("Sell Token", callback_data="sell")],
        [InlineKeyboardButton("Settings", callback_data="settings"),
         InlineKeyboardButton("Help", callback_data="help")],
    ]
    reply = InlineKeyboardMarkup(keyboard)
    msg = text or "SnapTomy Trading Bot"
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply)
    else:
        await update.effective_message.reply_text(msg, reply_markup=reply)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _ensure_admin(update)
    await cmd_menu(update, context)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    await _ensure_admin(update)
    mode = "Paper" if _config.get("paper_trading") else "LIVE"
    bal = _trading.executor.balance_usd if _trading else 0
    text = f"SnapTomy Bot | Mode: {mode}\nBalance: ${bal:.2f}"
    keyboard = [
        [InlineKeyboardButton("Portfolio", callback_data="portfolio"),
         InlineKeyboardButton("Positions", callback_data="positions")],
        [InlineKeyboardButton("Buy Token", callback_data="buy"),
         InlineKeyboardButton("Sell Token", callback_data="sell")],
        [InlineKeyboardButton("Settings", callback_data="settings"),
         InlineKeyboardButton("Help", callback_data="help")],
    ]
    reply = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply)
    else:
        await update.effective_message.reply_text(text, reply_markup=reply)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _ensure_admin(update)
    text = (
        "SnapTomy Commands:\n"
        "/menu - Show main menu\n"
        "/status - Bot health\n"
        "/portfolio - Portfolio overview\n"
        "/positions - Open positions\n"
        "/buy <address> <usd> - Buy token\n"
        "/help - This message"
    )
    await update.effective_message.reply_text(text)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _ensure_admin(update)
    mode = "Paper" if _config.get("paper_trading") else "LIVE"
    bal = _trading.executor.balance_usd if _trading else 0
    enabled = _config.get("trading", {}).get("enabled", False)
    await update.effective_message.reply_text(
        f"Status: Running\nMode: {mode}\nBalance: ${bal:.2f}\nAuto-trade: {'ON' if enabled else 'OFF'}"
    )


async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _ensure_admin(update)
    await _show_portfolio(update)


async def cmd_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _ensure_admin(update)
    await _show_positions(update)


async def _show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
    if not _trading:
        await update.effective_message.reply_text("Trading engine not available")
        return
    pos = _trading.position_manager.get_open_positions()
    open_val = sum(p.get("current_value_usd", 0) for p in pos)
    total = _trading.executor.balance_usd + _trading.executor.positions_value
    text = (
        f"Balance: ${_trading.executor.balance_usd:.2f}\n"
        f"Open Value: ${open_val:.2f}\n"
        f"Total: ${total:.2f}\n"
        f"Positions: {len(pos)}\n"
        f"PnL: ${sum(p.get('pnl_usd', 0) for p in pos):+.2f}"
    )
    keyboard = [[InlineKeyboardButton("Back", callback_data="menu")]]
    reply = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply)
    else:
        await update.effective_message.reply_text(text, reply_markup=reply)


async def _show_positions(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
    if not _trading:
        await update.effective_message.reply_text("Trading engine not available")
        return
    pos = _trading.position_manager.get_open_positions()
    if not pos:
        keyboard = [[InlineKeyboardButton("Back", callback_data="menu")]]
        await update.effective_message.reply_text("No open positions", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    lines = []
    for p in pos:
        pnl = p.get("pnl_percent", 0)
        emoji = "🟢" if pnl >= 0 else "🔴"
        lines.append(f"{emoji} {p['symbol']}: ${p['amount_usd']:.0f} ({pnl:+.1f}%)")
    keyboard = [[InlineKeyboardButton(f"Sell {p['symbol'][:10]}", callback_data=f"sell_{p['address']}") for p in pos[:3]]]
    keyboard.append([InlineKeyboardButton("Back", callback_data="menu")])
    await update.effective_message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("Cancelled")
    return ConversationHandler.END


async def _show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
    cfg = _config.get("trading", {})
    enabled = cfg.get("enabled", False)
    mode = "Paper" if _config.get("paper_trading") else "LIVE"
    max_pos = cfg.get("max_positions", 5)
    text = (
        f"Auto-trade: {'ON' if enabled else 'OFF'}\n"
        f"Mode: {mode}\n"
        f"Max Positions: {max_pos}\n"
        f"Min Score: {cfg.get('entry', {}).get('min_score_buy', 80)}\n"
        f"Stop Loss: {cfg.get('exit', {}).get('stop_loss_percent', -15)}%"
    )
    keyboard = [
        [InlineKeyboardButton(f"{'Disable' if enabled else 'Enable'} Trading", callback_data="trading_toggle")],
        [InlineKeyboardButton(f"Switch to {'LIVE' if _config.get('paper_trading') else 'Paper'}", callback_data="mode_toggle")],
        [InlineKeyboardButton("Back", callback_data="menu")],
    ]
    reply = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply)
    else:
        await update.effective_message.reply_text(text, reply_markup=reply)


async def _toggle_trading(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
    cfg = _config.get("trading", {})
    cfg["enabled"] = not cfg.get("enabled", False)
    _config["trading"] = cfg
    path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(path, "w") as f:
        json.dump(_config, f, indent=2)
    if _trading:
        _trading.trading_cfg = cfg
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"Auto-trading: {'ON' if cfg['enabled'] else 'OFF'}")
    await _show_settings(update)


async def _toggle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
    _config["paper_trading"] = not _config.get("paper_trading", True)
    path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(path, "w") as f:
        json.dump(_config, f, indent=2)
    if _trading:
        _trading.executor.paper_mode = _config.get("paper_trading", True)
    mode = "Paper" if _config.get("paper_trading") else "LIVE"
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"Switched to {mode} mode")
    await _show_settings(update)


async def buy_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Send me the token address to buy:")
    else:
        args = context.args
        if args and len(args) >= 2:
            return await _execute_buy(update, args[0], float(args[1]))
        await update.effective_message.reply_text("Send me the token address to buy:")
    return AWAIT_BUY_ADDRESS


async def buy_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["buy_address"] = update.message.text.strip()
    await update.message.reply_text("Amount in USD:")
    return AWAIT_BUY_AMOUNT


async def buy_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = context.user_data.get("buy_address")
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid amount. Use /buy <address> <usd>")
        return ConversationHandler.END
    return await _execute_buy(update, address, amount)


async def _execute_buy(update: Update, address: str, amount_usd: float):
    if not _trading:
        await update.effective_message.reply_text("Trading engine not available")
        return ConversationHandler.END
    result = await _trading.executor.buy(address, "solana", amount_usd)
    if result.get("success"):
        tx = result.get("tx", "?")
        price = result.get("price", 0)
        await update.effective_message.reply_text(
            f"Bought ${amount_usd:.2f} at ${price:.8f}\nTx: {tx[:16]}..."
        )
    else:
        await update.effective_message.reply_text(f"Buy failed: {result.get('error', 'unknown')}")
    return ConversationHandler.END


async def sell_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _trading:
        await update.effective_message.reply_text("Trading engine not available")
        return ConversationHandler.END
    pos = _trading.position_manager.get_open_positions()
    if not pos:
        await update.effective_message.reply_text("No open positions to sell")
        return ConversationHandler.END
    keyboard = []
    for p in pos[:10]:
        pnl = p.get("pnl_percent", 0)
        label = f"{p['symbol']} (${p['amount_usd']:.0f}, {pnl:+.1f}%)"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"sell_{p['address']}")])
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="menu")])
    await update.effective_message.reply_text("Select position to sell:", reply_markup=InlineKeyboardMarkup(keyboard))
    return AWAIT_SELL_ADDRESS


async def sell_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    address = query.data.replace("sell_", "")
    context.user_data["sell_address"] = address
    keyboard = [
        [InlineKeyboardButton("25%", callback_data="sellpct_25"),
         InlineKeyboardButton("50%", callback_data="sellpct_50")],
        [InlineKeyboardButton("75%", callback_data="sellpct_75"),
         InlineKeyboardButton("100%", callback_data="sellpct_100")],
        [InlineKeyboardButton("Cancel", callback_data="menu")],
    ]
    await query.edit_message_text("What percent to sell?", reply_markup=InlineKeyboardMarkup(keyboard))
    return AWAIT_SELL_PCT


async def sell_percent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pct = float(query.data.replace("sellpct_", ""))
    address = context.user_data.get("sell_address", "")
    if not _trading:
        await query.edit_message_text("Trading engine not available")
        return ConversationHandler.END
    result = await _trading.executor.sell(address, "solana", pct)
    if result.get("success"):
        price = result.get("price", 0)
        _trading.position_manager.close_position(address, reason="manual_sell")
        await query.edit_message_text(f"Sold {pct}% at ${price:.8f}")
    else:
        await query.edit_message_text(f"Sell failed: {result.get('error', 'unknown')}")
    return ConversationHandler.END
