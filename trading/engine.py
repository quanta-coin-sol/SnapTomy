import asyncio
import logging
import time

from analysis.contract_analyzer import ContractAnalyzer
from analysis.data_collector import DataCollector
from analysis.honeypot import HoneypotDetector
from analysis.scorer import Scorer
from analysis.social_analyzer import SocialAnalyzer
from analysis.wallet_analyzer import WalletAnalyzer
from discovery.base import DiscoveredToken
from monitoring.portfolio import PortfolioTracker
from monitoring.rug_detector import RugDetector
from notifications.manager import NotificationManager
from trading.executor import TradeExecutor
from trading.position_manager import PositionManager
from trading.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class TradingEngine:
    def __init__(self, config: dict, notification_mgr: NotificationManager = None):
        self.config = config
        self.trading_cfg = config.get("trading", {})
        self.exit_cfg = self.trading_cfg.get("exit", {})
        self.entry_cfg = self.trading_cfg.get("entry", {})
        self.data_collector = DataCollector(config)
        self.contract_analyzer = ContractAnalyzer(config)
        self.wallet_analyzer = WalletAnalyzer(config)
        self.social_analyzer = SocialAnalyzer(config)
        self.honeypot = HoneypotDetector(config)
        self.scorer = Scorer(config)
        self.executor = TradeExecutor(config)
        self.position_manager = PositionManager(config)
        self.risk_manager = RiskManager(config)
        self.rug_detector = RugDetector(config)
        self.portfolio = PortfolioTracker(config)
        self.notifier = notification_mgr or NotificationManager(config)
        self.queue = asyncio.Queue()
        self._running = False
        self._seen_tokens: set[str] = set()

    async def enqueue_for_analysis(self, token: DiscoveredToken):
        if token.address in self._seen_tokens:
            return
        self._seen_tokens.add(token.address)
        logger.info(f"Enqueued {token.symbol} ({token.address[:8]}...)")
        await self.queue.put(token)

    async def run(self):
        self._running = True
        monitor_task = asyncio.create_task(self._monitor_positions())
        logger.info("Trading engine started, waiting for tokens...")

        while self._running:
            try:
                token = await asyncio.wait_for(self.queue.get(), timeout=5)
                logger.info(f"Engine received: {token.symbol}")
                await self._analyze_and_trade(token)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Engine error: {e}")

        monitor_task.cancel()

    async def _analyze_and_trade(self, token: DiscoveredToken):
        if not self.trading_cfg.get("enabled", True):
            return
        open_count = len(self.position_manager.get_open_positions())
        max_pos = self.trading_cfg.get("max_positions", 5)
        if open_count >= max_pos:
            logger.info(f"Max positions ({max_pos}) reached, skipping {token.symbol}")
            return

        age = time.time() - (token.discovered_at.timestamp() if token.discovered_at else time.time())
        max_age = self.trading_cfg.get("max_age_seconds", 600)
        if age > max_age:
            logger.info(f"{token.symbol} too old ({age:.0f}s > {max_age}s), skipping")
            return

        logger.info(f"Analyzing {token.symbol} ({token.address[:8]}...)")

        logger.info(f"  -> collecting data for {token.symbol}")
        data = await self.data_collector.collect(token.address, token.chain)
        contract = await self.contract_analyzer.analyze(token.address, token.chain)
        honeypot = await self.honeypot.check(token.address, token.chain)
        if honeypot.get("is_honeypot"):
            logger.warning(f"Honeypot detected for {token.symbol}, skipping")
            return
        contract["is_honeypot"] = honeypot.get("is_honeypot", False)
        wallets = await self.wallet_analyzer.analyze(token.address, token.chain)
        social = await self.social_analyzer.analyze(token.address, token.chain)

        score_result = await self.scorer.score(data, contract, wallets, social)
        risk = await self.risk_manager.assess(contract, wallets, score_result["overall"])

        logger.info(f"{token.symbol}: score={score_result['overall']}, rec={score_result['recommendation']}, risk={risk['risk_percent']}%")

        if not risk["approved"]:
            logger.info(f"Risk too high for {token.symbol}: {risk['issues']}")
            return

        rec = score_result["recommendation"]
        if rec in ("IGNORE", "WATCH"):
            logger.info(f"Skipping {token.symbol}: recommendation is {rec}")
            return

        amount_usd = self._calc_position_size(rec)
        if amount_usd < 10:
            logger.info(f"Position size ${amount_usd:.2f} too small for {token.symbol}")
            return

        liq = contract.get("liquidity_usd", 0)
        min_liq = self.trading_cfg.get("min_liquidity_usd", 30000)
        if liq < min_liq:
            logger.info(f"Liquidity ${liq:.0f} < ${min_liq} for {token.symbol}, skipping")
            return

        exec_result = await self.executor.buy(token.address, token.chain, amount_usd)
        if exec_result["success"]:
            price = exec_result.get("price", data.get("price_usd", 0))
            self.position_manager.open_position(
                address=token.address,
                chain=token.chain,
                symbol=token.symbol,
                entry_price=price,
                amount_usd=amount_usd,
                score=score_result["overall"],
                tx=exec_result.get("tx"),
            )
            logger.info(f"BOUGHT {token.symbol}: ${amount_usd:.2f} @ ${price:.8f}")
            await self.notifier.send_buy_alert(
                {"symbol": token.symbol, "address": token.address, "amount_usd": amount_usd},
                score_result["overall"],
                exec_result.get("tx"),
            )

    def _calc_position_size(self, recommendation: str) -> float:
        balance = self.portfolio.balance_usd
        if recommendation == "STRONG BUY":
            return balance * (self.entry_cfg.get("size_strong_buy_percent", 1.0) / 100)
        elif recommendation == "BUY":
            return balance * (self.entry_cfg.get("size_buy_percent", 0.5) / 100)
        elif recommendation == "BUY SMALL":
            return balance * (self.entry_cfg.get("size_buy_small_percent", 0.25) / 100)
        return 0

    async def _monitor_positions(self):
        while self._running:
            try:
                open_positions = self.position_manager.get_open_positions()
                for pos in open_positions:
                    rug = await self.rug_detector.check(pos)
                    pos["current_risk"] = rug
                    if rug["is_rug"]:
                        logger.warning(f"RUG DETECTED: {pos['symbol']} - {rug['issues']}")
                        await self.notifier.send_rug_alert(pos, rug["issues"])
                        if self.exit_cfg.get("rug_sell_immediately", True):
                            result = await self.executor.sell(pos["address"], pos["chain"])
                            self.position_manager.close_position(pos["address"], reason="rug_detected", tx=result.get("tx"))
                            await self.notifier.send_sell_alert(pos, pos.get("pnl_percent", 0), result.get("tx"))
                        continue

                    if rug["price"] is not None:
                        self.position_manager.update_price(pos["address"], rug["price"])
                        pnl = pos.get("pnl_percent", 0)
                        if pnl <= self.exit_cfg.get("stop_loss_percent", -15):
                            logger.info(f"Stop loss triggered for {pos['symbol']} ({pnl:.1f}%)")
                            result = await self.executor.sell(pos["address"], pos["chain"])
                            self.position_manager.close_position(pos["address"], reason="stop_loss", tx=result.get("tx"))
                            await self.notifier.send_sell_alert(pos, pnl, result.get("tx"))
                            continue
                        if pnl >= self.exit_cfg.get("take_profit_percent", 50):
                            logger.info(f"Take profit triggered for {pos['symbol']} ({pnl:.1f}%)")
                            result = await self.executor.sell(pos["address"], pos["chain"])
                            self.position_manager.close_position(pos["address"], reason="take_profit", tx=result.get("tx"))
                            await self.notifier.send_sell_alert(pos, pnl, result.get("tx"))
                            continue
                        if pos.get("trailing_activated") and rug["price"] <= pos["trailing_stop"]:
                            logger.info(f"Trailing stop triggered for {pos['symbol']} ({pnl:.1f}%)")
                            result = await self.executor.sell(pos["address"], pos["chain"])
                            self.position_manager.close_position(pos["address"], reason="trailing_stop", tx=result.get("tx"))
                            await self.notifier.send_sell_alert(pos, pnl, result.get("tx"))
                            continue
                    self.position_manager._save()
                self.portfolio.update(open_positions, self.executor.balance_usd)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            await asyncio.sleep(15)

    def stop(self):
        self._running = False
