"""
HUNTER.OS - Celery Tasks
Background tasks for production deployment (replaces APScheduler).
"""
import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.process_due_workflows")
def process_due_workflows():
    """Process all workflows that are due for their next step."""
    db = SessionLocal()
    try:
        from app.services.workflow_engine import WorkflowEngine
        engine = WorkflowEngine(db)
        processed = engine.process_due_workflows()
        logger.info(f"Processed {processed} workflows")
    except Exception as e:
        logger.error(f"Workflow processing failed: {e}")
    finally:
        db.close()


@celery_app.task(name="app.tasks.check_email_replies")
def check_email_replies():
    """Check for new email replies via IMAP."""
    db = SessionLocal()
    try:
        from app.services.imap_service import IMAPService
        from app.models.account import EmailAccount
        accounts = db.query(EmailAccount).filter(
            EmailAccount.is_active == True,
            EmailAccount.is_paused == False,
        ).all()
        for account in accounts:
            try:
                service = IMAPService(db)
                service.check_replies(account)
            except Exception as e:
                logger.warning(f"IMAP check failed for {account.email}: {e}")
    except Exception as e:
        logger.error(f"Reply check failed: {e}")
    finally:
        db.close()


@celery_app.task(name="app.tasks.reset_monthly_usage")
def reset_monthly_usage():
    """Reset usage counters on the 1st of each month."""
    now = datetime.now(timezone.utc)
    if now.day != 1:
        return

    db = SessionLocal()
    try:
        from app.models.user import User
        users = db.query(User).all()
        for user in users:
            user.usage_this_month = {}
            user.usage_reset_at = now
        db.commit()
        logger.info(f"Reset monthly usage for {len(users)} users")
    except Exception as e:
        logger.error(f"Usage reset failed: {e}")
    finally:
        db.close()


@celery_app.task(name="app.tasks.auto_select_ab_winners")
def auto_select_ab_winners():
    """Check all active campaigns for A/B test significance."""
    db = SessionLocal()
    try:
        from app.models.campaign import Campaign
        from app.services.ab_testing import ABTestingEngine

        ab = ABTestingEngine(db)
        campaigns = db.query(Campaign).filter(
            Campaign.status == "active",
            Campaign.winning_variant.is_(None),
        ).all()

        for campaign in campaigns:
            if campaign.ab_variants and len(campaign.ab_variants) >= 2:
                winner = ab.auto_select_winner(campaign.id)
                if winner:
                    logger.info(f"Campaign {campaign.id}: winner auto-selected = {winner}")
    except Exception as e:
        logger.error(f"A/B winner selection failed: {e}")
    finally:
        db.close()
