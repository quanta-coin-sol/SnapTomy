import json
import logging

import aiohttp

logger = logging.getLogger(__name__)


class WebhookNotifier:
    def __init__(self, config: dict):
        self.config = config
        self.url = config.get("notification", {}).get("webhook_url")

    async def send(self, event: str, data: dict, *args):
        if not self.url:
            return
        payload = {"event": event, "data": data}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(self.url, json=payload, timeout=10) as r:
                    if r.status not in (200, 201, 204):
                        logger.warning(f"Webhook: HTTP {r.status}")
        except Exception as e:
            logger.error(f"Webhook error: {e}")
