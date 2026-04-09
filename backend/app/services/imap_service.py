"""
HUNTER.OS - IMAP Reply Detection Service
Polls email inbox for replies to outbound messages.
"""
import imaplib
import email
import logging
from email.header import decode_header
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.message import Message
from app.models.lead import Lead

logger = logging.getLogger(__name__)


class IMAPService:
    """Polls IMAP inbox for reply detection."""

    def __init__(self, db: Session):
        self.db = db

    def check_replies(
        self,
        imap_host: Optional[str] = None,
        imap_port: int = 993,
        email_user: Optional[str] = None,
        email_password: Optional[str] = None,
    ) -> list[dict]:
        """Check for new replies and process them."""
        host = imap_host or settings.SMTP_HOST
        user = email_user or settings.SMTP_USER
        password = email_password or settings.SMTP_PASSWORD

        if not all([host, user, password]):
            logger.warning("IMAP not configured, skipping reply check")
            return []

        detected_replies = []

        try:
            mail = imaplib.IMAP4_SSL(host, imap_port)
            mail.login(user, password)
            mail.select("INBOX")

            # Search for unseen emails
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                return []

            for msg_id in messages[0].split():
                try:
                    status, msg_data = mail.fetch(msg_id, "(RFC822)")
                    if status != "OK":
                        continue

                    raw_email = msg_data[0][1]
                    parsed = email.message_from_bytes(raw_email)

                    from_addr = self._extract_email(parsed.get("From", ""))
                    subject = self._decode_header(parsed.get("Subject", ""))
                    body = self._extract_body(parsed)

                    if not from_addr:
                        continue

                    # Try to match with a lead
                    lead = self.db.query(Lead).filter(
                        Lead.email == from_addr
                    ).first()

                    if lead:
                        # Save as inbound message
                        reply_msg = Message(
                            lead_id=lead.id,
                            direction="inbound",
                            channel="email",
                            subject=subject,
                            body=body,
                            status="received",
                            sender_email=from_addr,
                        )
                        self.db.add(reply_msg)
                        self.db.commit()

                        # Process with sentiment service
                        from app.services.sentiment_service import SentimentService
                        sentiment_svc = SentimentService(self.db)
                        result = sentiment_svc.process_reply(reply_msg.id, body)

                        detected_replies.append({
                            "lead_id": lead.id,
                            "from": from_addr,
                            "subject": subject,
                            "analysis": result.get("analysis"),
                        })

                        logger.info(f"Reply detected from {from_addr} for lead {lead.id}")

                except Exception as e:
                    logger.error(f"Error processing email {msg_id}: {e}")

            mail.logout()

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP connection failed: {e}")
        except Exception as e:
            logger.error(f"Reply check failed: {e}")

        return detected_replies

    @staticmethod
    def _extract_email(from_header: str) -> Optional[str]:
        """Extract email address from From header."""
        if "<" in from_header:
            start = from_header.index("<") + 1
            end = from_header.index(">")
            return from_header[start:end].lower()
        return from_header.strip().lower() if "@" in from_header else None

    @staticmethod
    def _decode_header(header: str) -> str:
        """Decode email header."""
        decoded_parts = decode_header(header)
        parts = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                parts.append(part.decode(encoding or "utf-8", errors="replace"))
            else:
                parts.append(part)
        return " ".join(parts)

    @staticmethod
    def _extract_body(parsed_email) -> str:
        """Extract plain text body from email."""
        if parsed_email.is_multipart():
            for part in parsed_email.walk():
                ct = part.get_content_type()
                if ct == "text/plain":
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        else:
            payload = parsed_email.get_payload(decode=True)
            charset = parsed_email.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        return ""
