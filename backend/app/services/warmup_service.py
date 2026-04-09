"""
HUNTER.OS - Account Warm-up & Rotation Service
Protects email/LinkedIn accounts from bans and spam flags.
"""
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.account import EmailAccount, LinkedInAccount
from app.core.config import settings

logger = logging.getLogger(__name__)


class WarmupService:
    """
    Smart Warm-up Protocol:
    - Day 1-3: Send 5 emails/day
    - Day 4-7: Increase by 3/day
    - Day 8-14: Increase by 5/day until max
    - After 14 days: Full capacity

    Also handles:
    - Account rotation (distribute load across accounts)
    - Health monitoring (pause accounts with high bounce rates)
    - Daily limit reset
    """

    def __init__(self, db: Session):
        self.db = db

    def get_next_email_account(self, user_id: int) -> Optional[EmailAccount]:
        """
        Account Rotation: Get the best email account to send from.
        Prioritizes:
        1. Accounts with remaining daily capacity
        2. Highest health score
        3. Lowest usage today (distribute evenly)
        """
        accounts = self.db.query(EmailAccount).filter(
            and_(
                EmailAccount.user_id == user_id,
                EmailAccount.is_active == True,
                EmailAccount.is_paused == False,
            )
        ).order_by(
            EmailAccount.total_sent_today.asc(),
            EmailAccount.health_score.desc(),
        ).all()

        for account in accounts:
            if account.total_sent_today < account.daily_send_limit:
                return account

        return None  # All accounts at capacity

    def get_next_linkedin_account(self, user_id: int, action: str = "message") -> Optional[LinkedInAccount]:
        """Get the best LinkedIn account for the given action type."""
        accounts = self.db.query(LinkedInAccount).filter(
            and_(
                LinkedInAccount.user_id == user_id,
                LinkedInAccount.is_active == True,
                LinkedInAccount.is_paused == False,
            )
        ).order_by(
            LinkedInAccount.health_score.desc(),
        ).all()

        for account in accounts:
            if action == "message" and account.messages_sent_today < account.daily_message_limit:
                return account
            elif action == "connect" and account.connections_sent_today < account.daily_connection_limit:
                return account
            elif action == "visit" and account.visits_today < account.daily_visit_limit:
                return account

        return None

    def progress_warmup(self):
        """
        Called daily by scheduler.
        Progresses each warming account to the next day's limits.
        """
        warming_emails = self.db.query(EmailAccount).filter(
            EmailAccount.is_warming == True
        ).all()

        for account in warming_emails:
            account.warmup_day += 1

            if account.warmup_day <= 3:
                account.daily_send_limit = settings.WARMUP_START_DAILY
            elif account.warmup_day <= 7:
                account.daily_send_limit = min(
                    settings.WARMUP_START_DAILY + (account.warmup_day - 3) * settings.WARMUP_INCREMENT,
                    settings.WARMUP_MAX_DAILY,
                )
            elif account.warmup_day <= settings.WARMUP_DURATION_DAYS:
                account.daily_send_limit = min(
                    account.daily_send_limit + 5,
                    settings.WARMUP_MAX_DAILY,
                )
            else:
                # Warmup complete
                account.is_warming = False
                account.daily_send_limit = settings.WARMUP_MAX_DAILY
                logger.info(f"Email account {account.email} warmup complete!")

            # Reset daily counter
            account.total_sent_today = 0

        # LinkedIn warmup
        warming_linkedin = self.db.query(LinkedInAccount).filter(
            LinkedInAccount.is_warming == True
        ).all()

        for account in warming_linkedin:
            # LinkedIn warmup is more conservative
            day = account.daily_message_limit  # Use as proxy for warmup day
            account.daily_connection_limit = min(account.daily_connection_limit + 1, 25)
            account.daily_message_limit = min(account.daily_message_limit + 2, 50)
            account.daily_visit_limit = min(account.daily_visit_limit + 5, 100)

            # Reset daily counters
            account.connections_sent_today = 0
            account.messages_sent_today = 0
            account.visits_today = 0

            if account.daily_message_limit >= 50:
                account.is_warming = False

        self.db.commit()
        logger.info(f"Warmup progressed: {len(warming_emails)} email, {len(warming_linkedin)} LinkedIn accounts")

    def check_account_health(self):
        """
        Monitor account health and auto-pause unhealthy accounts.
        Called periodically by scheduler.
        """
        warnings = []

        # Email accounts
        email_accounts = self.db.query(EmailAccount).filter(
            EmailAccount.is_active == True
        ).all()

        for account in email_accounts:
            # Auto-pause if bounce rate > 5%
            if account.bounce_rate > 5.0:
                account.is_paused = True
                account.pause_reason = f"Bounce rate too high: {account.bounce_rate:.1f}%"
                account.health_score = max(0, account.health_score - 20)
                warnings.append(f"PAUSED {account.email}: bounce rate {account.bounce_rate:.1f}%")

            # Auto-pause if spam complaint rate > 0.1%
            elif account.spam_complaint_rate > 0.1:
                account.is_paused = True
                account.pause_reason = f"Spam complaints: {account.spam_complaint_rate:.2f}%"
                account.health_score = max(0, account.health_score - 30)
                warnings.append(f"PAUSED {account.email}: spam complaints {account.spam_complaint_rate:.2f}%")

            # Degrade health score for low open rates
            elif account.open_rate < 10.0 and account.total_sent_all > 100:
                account.health_score = max(0, account.health_score - 5)
                warnings.append(f"WARNING {account.email}: low open rate {account.open_rate:.1f}%")

        # LinkedIn accounts
        linkedin_accounts = self.db.query(LinkedInAccount).filter(
            LinkedInAccount.is_active == True
        ).all()

        for account in linkedin_accounts:
            if account.restriction_count >= 3:
                account.is_paused = True
                account.health_score = max(0, account.health_score - 40)
                warnings.append(f"PAUSED LinkedIn {account.linkedin_email}: {account.restriction_count} restrictions")

        self.db.commit()

        if warnings:
            logger.warning(f"Account health check: {len(warnings)} issues found")
        return warnings

    def reset_daily_counters(self):
        """Reset all daily send counters. Called at midnight."""
        self.db.query(EmailAccount).filter(
            EmailAccount.is_active == True
        ).update({"total_sent_today": 0})

        self.db.query(LinkedInAccount).filter(
            LinkedInAccount.is_active == True
        ).update({
            "connections_sent_today": 0,
            "messages_sent_today": 0,
            "visits_today": 0,
        })

        self.db.commit()
        logger.info("Daily counters reset")

    def get_health_dashboard(self, user_id: int) -> dict:
        """Build the Deliverability Health Dashboard data."""
        email_accounts = self.db.query(EmailAccount).filter(
            EmailAccount.user_id == user_id
        ).all()

        linkedin_accounts = self.db.query(LinkedInAccount).filter(
            LinkedInAccount.user_id == user_id
        ).all()

        warnings = []
        for acc in email_accounts:
            if acc.bounce_rate > 3:
                warnings.append(f"{acc.email}: bounce rate {acc.bounce_rate:.1f}% (threshold: 5%)")
            if acc.is_paused:
                warnings.append(f"{acc.email}: PAUSED - {acc.pause_reason}")
            if not acc.spf_valid:
                warnings.append(f"{acc.email}: SPF record not valid")
            if not acc.dkim_valid:
                warnings.append(f"{acc.email}: DKIM not configured")
            if not acc.dmarc_valid:
                warnings.append(f"{acc.email}: DMARC policy missing")

        for acc in linkedin_accounts:
            if acc.restriction_count > 0:
                warnings.append(f"LinkedIn {acc.linkedin_email}: {acc.restriction_count} past restrictions")

        total_sent = sum(a.total_sent_today for a in email_accounts)
        total_capacity = sum(a.daily_send_limit for a in email_accounts if not a.is_paused)

        return {
            "total_email_accounts": len(email_accounts),
            "total_linkedin_accounts": len(linkedin_accounts),
            "avg_email_health": (
                sum(a.health_score for a in email_accounts) / max(len(email_accounts), 1)
            ),
            "avg_linkedin_health": (
                sum(a.health_score for a in linkedin_accounts) / max(len(linkedin_accounts), 1)
            ),
            "accounts_warming": sum(1 for a in email_accounts if a.is_warming) + sum(1 for a in linkedin_accounts if a.is_warming),
            "accounts_paused": sum(1 for a in email_accounts if a.is_paused) + sum(1 for a in linkedin_accounts if a.is_paused),
            "total_sent_today": total_sent,
            "total_daily_capacity": total_capacity,
            "warnings": warnings,
        }
