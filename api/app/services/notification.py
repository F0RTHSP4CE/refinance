"""Notification service – sends messages to entities via all available channels."""

from __future__ import annotations

import logging
import time

import requests
from app.config import Config
from app.models.entity import Entity

logger = logging.getLogger(__name__)

# How many times to retry a single Telegram send after a 429 response.
_TELEGRAM_MAX_RETRIES = 3
# Hard cap on the retry_after sleep (seconds) so a broadcast loop isn't stalled forever.
_TELEGRAM_MAX_RETRY_SLEEP = 30


class NotificationService:
    """Sends a message to an entity through every channel that is configured for it."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def send(
        self,
        entity: Entity,
        message: str,
        *,
        telegram_reply_markup: str | None = None,
    ) -> dict[str, bool]:
        """Dispatch *message* to all channels available for *entity*.

        Returns a mapping of channel name → success flag.
        Currently the only supported channel is Telegram (via ``auth.telegram_id``).
        *telegram_reply_markup* is an optional JSON-encoded reply_markup string that
        is forwarded to the Telegram sendMessage call when provided.
        """
        results: dict[str, bool] = {}

        auth = entity.auth or {}
        telegram_id_raw = auth.get("telegram_id")
        if telegram_id_raw is not None:
            try:
                telegram_id = int(telegram_id_raw)
                results["telegram"] = self._send_telegram(
                    telegram_id, message, reply_markup=telegram_reply_markup
                )
            except (ValueError, TypeError):
                logger.error(
                    "NotificationService: invalid telegram_id for entity id=%s",
                    entity.id,
                )
                results["telegram"] = False

        return results

    def _post_with_retry(
        self,
        url: str,
        payload: dict,
        telegram_id: int,
    ) -> bool:
        """POST *payload* to *url*, retrying on 429 up to _TELEGRAM_MAX_RETRIES times.

        When Telegram responds with 429 the ``parameters.retry_after`` value is
        honoured (capped at ``_TELEGRAM_MAX_RETRY_SLEEP`` seconds) so the
        message is not dropped but simply delayed.
        """
        for attempt in range(1, _TELEGRAM_MAX_RETRIES + 1):
            try:
                response = requests.post(url, data=payload, timeout=5)
            except Exception:
                logger.exception(
                    "NotificationService: Exception sending Telegram message to chat_id=%s",
                    telegram_id,
                )
                return False

            if response.status_code == 200:
                logger.info(
                    "NotificationService: Telegram message sent to chat_id=%s",
                    telegram_id,
                )
                return True

            if response.status_code == 429:
                retry_after = _TELEGRAM_MAX_RETRY_SLEEP
                try:
                    retry_after = min(
                        int(
                            response.json()
                            .get("parameters", {})
                            .get("retry_after", retry_after)
                        ),
                        _TELEGRAM_MAX_RETRY_SLEEP,
                    )
                except Exception:
                    pass
                logger.warning(
                    "NotificationService: Telegram rate-limited chat_id=%s, "
                    "sleeping %ss before retry (attempt %s/%s)",
                    telegram_id,
                    retry_after,
                    attempt,
                    _TELEGRAM_MAX_RETRIES,
                )
                time.sleep(retry_after)
                continue

            logger.error(
                "NotificationService: Telegram sendMessage failed status=%s body=%s",
                response.status_code,
                response.text,
            )
            return False

        logger.error(
            "NotificationService: Telegram message to chat_id=%s dropped after %s retries (rate-limited)",
            telegram_id,
            _TELEGRAM_MAX_RETRIES,
        )
        return False

    def _send_telegram(
        self,
        telegram_id: int,
        message: str,
        *,
        reply_markup: str | None = None,
    ) -> bool:
        """Send an HTML-formatted message to a Telegram chat.

        If *reply_markup* (a JSON string) is provided it is included in the
        request.  On failure (non-429) the call is retried without it as a
        fallback.  429 responses are handled transparently by _post_with_retry.
        """
        if not self.config.telegram_bot_api_token:
            logger.warning("NotificationService: Telegram bot token not configured")
            return False

        base_url = f"https://api.telegram.org/bot{self.config.telegram_bot_api_token}/sendMessage"

        payload: dict = {
            "chat_id": telegram_id,
            "text": message,
            "parse_mode": "HTML",
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        if self._post_with_retry(base_url, payload, telegram_id):
            return True

        # If reply_markup was present, try once more without it in case it was the cause.
        if reply_markup is not None:
            logger.info(
                "NotificationService: Retrying without reply_markup for chat_id=%s",
                telegram_id,
            )
            del payload["reply_markup"]
            return self._post_with_retry(base_url, payload, telegram_id)

        return False
