"""Telegram alert sender.

Minimal — no SDK, just HTTPS POST to https://api.telegram.org. Pass
TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID via env. If either is missing,
send_alert no-ops (silent: alerts are opt-in).
"""
from __future__ import annotations

import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

TELEGRAM_BASE = "https://api.telegram.org"


async def send_telegram(text: str) -> bool:
    """Send a Markdown-formatted message. Returns True if delivered."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False

    url = f"{TELEGRAM_BASE}/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
        return True
    except Exception as e:                              # noqa: BLE001
        logger.warning("alerts.telegram_failed", extra={"error": str(e)})
        return False
