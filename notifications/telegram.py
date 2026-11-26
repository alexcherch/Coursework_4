import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
REQUEST_TIMEOUT = 10


class TelegramError(Exception):
    """Raised when a message cannot be sent through the Telegram Bot API."""


def send_message(chat_id, text, *, token=None, timeout=REQUEST_TIMEOUT):
    """Send a text message to a Telegram chat and return the API response payload."""
    bot_token = token or settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        raise TelegramError("Telegram bot token is not configured.")

    try:
        response = requests.post(
            TELEGRAM_API_URL.format(token=bot_token),
            json={"chat_id": chat_id, "text": text},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise TelegramError(f"Telegram request failed: {exc}") from exc

    if response.status_code != 200:
        raise TelegramError(
            f"Telegram API returned HTTP {response.status_code}: {response.text}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise TelegramError("Telegram API returned an invalid JSON response.") from exc

    if not payload.get("ok"):
        description = payload.get("description", "unknown error")
        raise TelegramError(f"Telegram API error: {description}")

    return payload
