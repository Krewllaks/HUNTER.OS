"""
HUNTER.OS - Email Tracking Endpoints
Open tracking (1x1 pixel) and click tracking (redirect).
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import Response, RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.message import Message
from app.models.lead import Lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["Tracking"])

# 1x1 transparent GIF pixel
TRACKING_PIXEL = bytes([
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00,
    0x80, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x21,
    0xF9, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0x2C, 0x00, 0x00,
    0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
    0x01, 0x00, 0x3B,
])


@router.get("/open/{tracking_id}")
def track_open(
    tracking_id: str,
    db: Session = Depends(get_db),
):
    """Track email open via 1x1 pixel. Updates Message.opened_at."""
    msg = db.query(Message).filter(Message.tracking_id == tracking_id).first()
    if msg and not msg.opened_at:
        msg.opened_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Email opened: tracking_id={tracking_id}, lead_id={msg.lead_id}")

    return Response(content=TRACKING_PIXEL, media_type="image/gif")


@router.get("/click/{tracking_id}")
def track_click(
    tracking_id: str,
    url: str = "https://hunteros.com",
    db: Session = Depends(get_db),
):
    """Track link click and redirect. Updates Message.clicked_at."""
    msg = db.query(Message).filter(Message.tracking_id == tracking_id).first()
    if msg and not msg.clicked_at:
        msg.clicked_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Link clicked: tracking_id={tracking_id}, lead_id={msg.lead_id}")

    return RedirectResponse(url=url)


@router.get("/unsubscribe/{tracking_id}")
def unsubscribe(tracking_id: str, db: Session = Depends(get_db)):
    """One-click unsubscribe (CAN-SPAM compliance). No auth required."""
    msg = db.query(Message).filter(Message.tracking_id == tracking_id).first()
    if not msg:
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;text-align:center;padding:60px;'>"
            "<h2>Already unsubscribed.</h2>"
            "</body></html>"
        )

    lead = db.query(Lead).filter(Lead.id == msg.lead_id).first()
    if lead:
        lead.do_not_contact = True
        lead.is_blacklisted = True
        # Stop all active workflows for this lead
        from app.models.campaign import Workflow
        workflows = db.query(Workflow).filter(
            Workflow.lead_id == lead.id,
            Workflow.status == "active",
        ).all()
        for wf in workflows:
            wf.status = "stopped_unsubscribe"
        db.commit()
        logger.info(f"Lead {lead.id} unsubscribed via tracking_id={tracking_id}")

    return HTMLResponse(
        "<html><body style='font-family:sans-serif;text-align:center;padding:60px;'>"
        "<h2>Successfully Unsubscribed</h2>"
        "<p>You will no longer receive emails from us.</p>"
        "</body></html>"
    )
