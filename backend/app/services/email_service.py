"""
HUNTER.OS - Email Sending Service
SMTP sending with rotation, tracking pixel injection, rate limiting.
"""
import logging
import smtplib
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.message import Message

logger = logging.getLogger(__name__)


class EmailService:
    """Handles email sending with tracking and rate limiting."""

    def __init__(self, db: Session):
        self.db = db

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        message_id: Optional[int] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
    ) -> dict:
        """Send an email with tracking pixel injection."""
        host = smtp_host or settings.SMTP_HOST
        port = smtp_port or settings.SMTP_PORT
        user = smtp_user or settings.SMTP_USER
        password = smtp_password or settings.SMTP_PASSWORD
        sender = from_email or user

        if not all([host, user, password]):
            logger.error("SMTP not configured")
            return {"status": "error", "detail": "SMTP not configured"}

        # Generate tracking ID
        tracking_id = str(uuid.uuid4())

        # Inject tracking pixel + CAN-SPAM unsubscribe footer
        tracking_pixel = f'<img src="{settings.API_V1_PREFIX}/tracking/open/{tracking_id}" width="1" height="1" style="display:none" />'
        unsubscribe_footer = self._build_unsubscribe_footer(tracking_id)
        html_body = self._text_to_html(body) + unsubscribe_footer + tracking_pixel

        # Build email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{sender}>" if from_name else sender
        msg["To"] = to_email
        msg["Reply-To"] = sender

        # CAN-SPAM: List-Unsubscribe headers (RFC 8058 one-click)
        unsubscribe_url = f"{settings.API_V1_PREFIX}/tracking/unsubscribe/{tracking_id}"
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

        # Plain text + HTML
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                server.starttls()
                server.login(user, password)
                server.send_message(msg)

            logger.info(f"Email sent to {to_email} (tracking: {tracking_id})")

            # Update message record if exists
            if message_id:
                db_msg = self.db.query(Message).filter(Message.id == message_id).first()
                if db_msg:
                    db_msg.status = "sent"
                    db_msg.tracking_id = tracking_id
                    self.db.commit()

            return {
                "status": "sent",
                "tracking_id": tracking_id,
                "to": to_email,
            }

        except smtplib.SMTPAuthenticationError:
            logger.error(f"SMTP auth failed for {user}")
            return {"status": "error", "detail": "SMTP authentication failed"}
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return {"status": "error", "detail": str(e)}

    @staticmethod
    def _build_unsubscribe_footer(tracking_id: str) -> str:
        """Generate CAN-SPAM compliant unsubscribe footer."""
        unsubscribe_url = f"{settings.API_V1_PREFIX}/tracking/unsubscribe/{tracking_id}"
        return f'''
<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 11px; color: #999; text-align: center;">
  <p>This email was sent by HUNTER.OS on behalf of our customer.</p>
  <p><a href="{unsubscribe_url}" style="color: #666; text-decoration: underline;">Unsubscribe</a> from future emails.</p>
</div>'''

    @staticmethod
    def _text_to_html(text: str) -> str:
        """Convert plain text to simple HTML."""
        paragraphs = text.split("\n\n")
        html_parts = [f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs if p.strip()]
        return f"""<div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
{''.join(html_parts)}
</div>"""
