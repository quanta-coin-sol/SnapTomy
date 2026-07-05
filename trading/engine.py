import asyncio
import logging
from collections import deque

from analysis.data_collector import DataCollector
from analysis.contract_analyzer import ContractAnalyzer
from analysis.wallet_analyzer import WalletAnalyzer
from analysis.social_analyzer import SocialAnalyzer
from analysis.scorer import Scorer
from discovery.base import DiscoveredToken

logger = logging.getLogger(__name__)


class TradingEngine:
    def __init__(self, config: dict):
        self.config = config
        self.data_collector = DataCollector(config)
        self.contract_analyzer = ContractAnalyzer(config)
        self.wallet_analyzer = WalletAnalyzer(config)
        self.social_analyzer = SocialAnalyzer(config)
        self.scorer = Scorer(config)
        self.queue = asyncio.Queue()
        self._running = False
        self.min_score = config.get("trading", {}).get("min_analysis_score", 60)

    async def enqueue_for_analysis(self, token: DiscoveredToken):
        await self.queue.put(token)

    async def run(self):
        self._running = True
        while self._running:
            try:
                token = await asyncio.wait_for(self.queue.get(), timeout=30)
                await self._analyze_and_trade(token)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"TradingEngine error: {e}")

    async def _analyze_and_trade(self, token: DiscoveredToken):
        logger.info(f"Analyzing {token.symbol} ({token.address[:8]}...)")
        data = await self.data_collector.collect(token.address, token.chain)
        contract = await self.contract_analyzer.analyze(token.address, token.chain)
        wallets = await self.wallet_analyzer.analyze(token.address, token.chain)
        social = await self.social_analyzer.analyze(token.address, token.chain)
        score = await self.scorer.score(contract, wallets, social)
        logger.info(f"Score for {token.symbol}: {score}")
        if score >= self.min_score:
            logger.info(f"Signal: BUY {token.symbol} (score={score})")
        else:
            logger.info(f"Skip {token.symbol}: score {score} < {self.min_score}")

    def stop(self):
        self._running = False
