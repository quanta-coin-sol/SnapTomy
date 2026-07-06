import logging
import os

from solana.keypair import Keypair
from solders.keypair import Keypair as SoldersKeypair

logger = logging.getLogger(__name__)


class SolanaWallet:
    def __init__(self, private_key: str = None):
        self.keypair = None
        if private_key:
            self.from_private_key(private_key)

    def from_private_key(self, key: str):
        try:
            key = key.strip()
            if key.startswith("["):
                import json
                self.keypair = SoldersKeypair.from_bytes(bytes(json.loads(key)))
            else:
                from solders.keypair import Keypair as K
                self.keypair = K.from_base58_string(key)
            logger.info(f"Wallet loaded: {self.keypair.pubkey()}")
        except Exception as e:
            logger.error(f"Failed to load wallet: {e}")

    @property
    def address(self) -> str:
        return str(self.keypair.pubkey()) if self.keypair else None

    def get_signer(self):
        return self.keypair
