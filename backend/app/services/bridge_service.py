"""
HUNTER.OS - Notification Bridge Service
Bridges notifications to Telegram and WhatsApp.
"""
import logging
from typing import Optional
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.models.message import Notification
from app.core.config import settings

logger = logging.getLogger(__name__)


class BridgeService:
    """
    Sends notifications to external messaging platforms.
    Supports: Telegram, WhatsApp (via API).
    """

    def __init__(self, db: Session):
        self.db = db

    async def send_to_telegram(self, message: str, chat_id: Optional[str] = None) -> bool:
        """Send message to Telegram via Bot API."""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram bot token not configured")
            return False

        target_chat = chat_id or settings.TELEGRAM_CHAT_ID
        if not target_chat:
            logger.warning("No Telegram chat ID configured")
            return False

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json={
                    "chat_id": target_chat,
                    "text": message,
                    "parse_mode": "HTML",
                })
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    async def send_to_whatsapp(self, message: str, phone: Optional[str] = None) -> bool:
        """Send message to WhatsApp via configured API."""
        if not settings.WHATSAPP_API_URL or not settings.WHATSAPP_API_TOKEN:
            logger.warning("WhatsApp API not configured")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.WHATSAPP_API_URL,
                    headers={"Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}"},
                    json={"message": message, "phone": phone},
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return False

    async def bridge_notifications(
        self,
        user_id: int,
        notification_ids: list[int] = None,
        send_to: list[str] = None,
        custom_message: Optional[str] = None,
    ) -> dict:
        """Bridge pending notifications to messaging platforms."""
        send_to = send_to or ["telegram"]

        if notification_ids:
            notifications = self.db.query(Notification).filter(
                Notification.id.in_(notification_ids),
                Notification.user_id == user_id,
            ).all()
        else:
            # Get all undelivered notifications
            notifications = self.db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.sent_to_telegram == False,
                Notification.sent_to_whatsapp == False,
            ).order_by(Notification.created_at.desc()).limit(20).all()

        results = {"telegram_sent": 0, "whatsapp_sent": 0, "errors": []}

        for notif in notifications:
            message = custom_message or self._format_notification(notif)

            if "telegram" in send_to:
                success = await self.send_to_telegram(message)
                if success:
                    notif.sent_to_telegram = True
                    notif.sent_at = datetime.now(timezone.utc)
                    results["telegram_sent"] += 1
                else:
                    results["errors"].append(f"Telegram failed for notification {notif.id}")

            if "whatsapp" in send_to:
                success = await self.send_to_whatsapp(message)
                if success:
                    notif.sent_to_whatsapp = True
                    notif.sent_at = datetime.now(timezone.utc)
                    results["whatsapp_sent"] += 1
                else:
                    results["errors"].append(f"WhatsApp failed for notification {notif.id}")

        self.db.commit()
        return results

    def _format_notification(self, notif: Notification) -> str:
        """Format a notification for messaging platforms."""
        emoji_map = {
            "reply_received": "📩",
            "meeting_booked": "📅",
            "lead_scored": "🎯",
            "campaign_ended": "📊",
        }
        emoji = emoji_map.get(notif.type, "🔔")

        return f"""{emoji} <b>HUNTER.OS Alert</b>

<b>{notif.title or notif.type.replace('_', ' ').title()}</b>

{notif.content[:300]}

<i>— Sent via HUNTER.OS</i>"""
