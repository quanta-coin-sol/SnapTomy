import json
import logging
import os

logger = logging.getLogger(__name__)


class WalletManager:
    def __init__(self, config: dict):
        self.config = config
        self.wallets_file = "wallets.json"
        self.wallets = []
        self._load()

    def _load(self):
        if os.path.exists(self.wallets_file):
            try:
                with open(self.wallets_file) as f:
                    self.wallets = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load wallets: {e}")

    def get_wallets(self, chain: str = None) -> list[dict]:
        if chain:
            return [w for w in self.wallets if w.get("chain") == chain]
        return self.wallets
