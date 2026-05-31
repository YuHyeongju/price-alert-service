"""알림 발송: 콘솔(기본) / 디스코드 웹훅."""
from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _send_discord(text: str) -> bool:
    try:
        resp = httpx.post(
            settings.discord_webhook_url, json={"content": text}, timeout=5.0
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.warning("디스코드 전송 실패: %s", exc)
        return False


def notify(channel: str, title: str, message: str, link: str = "") -> None:
    """알림을 발송한다. 실패해도 예외를 올리지 않는다(엔진 보호)."""
    text = f"🔔 {title}\n{message}"
    if link:
        text += f"\n{link}"

    if channel == "discord" and settings.discord_enabled:
        if _send_discord(text):
            return
        # 실패하면 아래 콘솔로 폴백

    logger.info("[ALERT] %s", text.replace("\n", " | "))
    try:
        print(f"\n===== 🔔 가격 알림 =====\n{text}\n=======================\n")
    except UnicodeEncodeError:
        # 콘솔이 일부 문자를 표현 못 해도 알림 자체를 실패시키지 않는다(ASCII 폴백).
        print("[ALERT] price alert fired (see logs / notification channel)")
