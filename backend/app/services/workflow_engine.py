"""
HUNTER.OS - Workflow Execution Engine
Logic-based decision tree for omnichannel outreach.
"""
import asyncio
import concurrent.futures
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.lead import Lead
from app.models.campaign import Campaign, Workflow
from app.models.message import Message, Notification
from app.models.account import EmailAccount, LinkedInAccount

logger = logging.getLogger(__name__)


def _get_linkedin_cookie(db, user_id: int) -> str | None:
    """Look up the active LinkedIn account's session cookie for a user."""
    from app.core.encryption import decrypt_value
    li_account = db.query(LinkedInAccount).filter(
        LinkedInAccount.user_id == user_id,
        LinkedInAccount.is_active == True,
        LinkedInAccount.is_paused == False,
    ).first()
    if not li_account or not li_account.session_cookie:
        return None
    try:
        return decrypt_value(li_account.session_cookie)
    except Exception as exc:
        # If not encrypted (dev/test), return raw
        logger.warning("Failed to decrypt LinkedIn session cookie, using raw value: %s", exc)
        return li_account.session_cookie


def _run_async(coro):
    """Run an async coroutine from sync context safely.

    If no event loop is running (e.g. APScheduler thread), uses asyncio.run()
    which properly creates and cleans up a loop. If called from within an
    existing loop (e.g. FastAPI), delegates to a thread pool to avoid deadlock.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to use asyncio.run()
        return asyncio.run(coro)
    else:
        # Inside an existing loop — run in a separate thread
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=60)


class WorkflowEngine:
    """
    Executes campaign workflows step-by-step.
    Supports:
    - Conditional branching (if opened → do X, else → do Y)
    - Auto-stop on reply detection
    - Multi-channel sequencing
    - Timing intelligence integration
    """

    def __init__(self, db: Session):
        self.db = db

    def enqueue_lead(self, lead_id: int, campaign_id: int, variant: Optional[str] = None):
        """Add a lead to a campaign's workflow."""
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign or not campaign.workflow_steps:
            raise ValueError(f"Campaign {campaign_id} not found or has no workflow steps")

        # Check if already enrolled
        existing = self.db.query(Workflow).filter(
            and_(Workflow.lead_id == lead_id, Workflow.campaign_id == campaign_id)
        ).first()
        if existing:
            return existing

        first_step = campaign.workflow_steps[0] if campaign.workflow_steps else {}
        delay_hours = first_step.get("delay_hours", 0)

        workflow = Workflow(
            lead_id=lead_id,
            campaign_id=campaign_id,
            current_step=1,
            status="active",
            ab_variant_assigned=variant,
            next_scheduled=datetime.now(timezone.utc) + timedelta(hours=delay_hours),
            event_log=[],
        )
        self.db.add(workflow)
        self.db.commit()

        # Update campaign stats
        campaign.total_leads = (campaign.total_leads or 0) + 1
        self.db.commit()

        return workflow

    def process_due_workflows(self):
        """
        Process all workflows that are due for their next step.
        Called by the scheduler (APScheduler) periodically.
        """
        now = datetime.now(timezone.utc)

        due_workflows = self.db.query(Workflow).filter(
            and_(
                Workflow.status == "active",
                Workflow.next_scheduled <= now,
            )
        ).all()

        processed = 0
        for wf in due_workflows:
            try:
                self._execute_step(wf)
                processed += 1
            except Exception as e:
                logger.error(f"Workflow {wf.id} execution failed: {e}")
                self._log_event(wf, "error", str(e))

        logger.info(f"Processed {processed}/{len(due_workflows)} due workflows")
        return processed

    def _execute_step(self, workflow: Workflow):
        """Execute the current step in a workflow."""
        campaign = workflow.campaign
        steps = campaign.workflow_steps or []

        if workflow.current_step > len(steps):
            workflow.status = "completed"
            self.db.commit()
            return

        step = steps[workflow.current_step - 1]
        channel = step.get("channel", "email")
        template_id = step.get("template_id")
        condition = step.get("condition")

        # Check condition before executing
        if condition:
            should_proceed = self._evaluate_condition(workflow, condition)
            if not should_proceed:
                # Skip to the specified step
                skip_to = condition.get("else", "").replace("skip_to_step_", "")
                if skip_to.isdigit():
                    workflow.current_step = int(skip_to)
                else:
                    workflow.current_step += 1
                self._schedule_next(workflow, steps)
                self.db.commit()
                return

        # Execute the action
        self._log_event(workflow, channel, f"Executing step {workflow.current_step}")

        if channel == "linkedin_visit":
            self._action_linkedin_visit(workflow)
        elif channel == "email":
            self._action_send_email(workflow, template_id)
        elif channel == "linkedin_connect":
            self._action_linkedin_connect(workflow)
        elif channel == "linkedin_dm":
            self._action_linkedin_dm(workflow, template_id)

        # Update workflow state
        workflow.last_action = channel
        workflow.last_action_at = datetime.now(timezone.utc)
        workflow.current_step += 1
        campaign.total_contacted = (campaign.total_contacted or 0) + 1

        # Schedule next step
        self._schedule_next(workflow, steps)
        self.db.commit()

    def _evaluate_condition(self, workflow: Workflow, condition: dict) -> bool:
        """Evaluate a workflow condition (e.g., 'if email_opened')."""
        condition_type = condition.get("if", "")

        if condition_type == "email_opened":
            # Check if any outbound email to this lead was opened
            opened = self.db.query(Message).filter(
                and_(
                    Message.lead_id == workflow.lead_id,
                    Message.direction == "outbound",
                    Message.opened_at.isnot(None),
                )
            ).first()
            return opened is not None

        elif condition_type == "email_clicked":
            clicked = self.db.query(Message).filter(
                and_(
                    Message.lead_id == workflow.lead_id,
                    Message.direction == "outbound",
                    Message.clicked_at.isnot(None),
                )
            ).first()
            return clicked is not None

        elif condition_type == "replied":
            replied = self.db.query(Message).filter(
                and_(
                    Message.lead_id == workflow.lead_id,
                    Message.direction == "inbound",
                )
            ).first()
            return replied is not None

        return True  # Default: proceed

    def _schedule_next(self, workflow: Workflow, steps: list):
        """Schedule the next workflow step."""
        if workflow.current_step > len(steps):
            workflow.status = "completed"
            workflow.next_scheduled = None
        else:
            next_step = steps[workflow.current_step - 1]
            delay = next_step.get("delay_hours", 24)
            workflow.next_scheduled = datetime.now(timezone.utc) + timedelta(hours=delay)

    def _log_event(self, workflow: Workflow, action: str, detail: str = ""):
        """Add event to workflow log."""
        log = workflow.event_log or []
        log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": workflow.current_step,
            "action": action,
            "detail": detail,
        })
        workflow.event_log = log

    # ── Channel Actions ──────────────────────────────────
    def _action_linkedin_visit(self, workflow: Workflow):
        """Execute a LinkedIn profile visit via LinkedInService."""
        lead = self.db.query(Lead).filter(Lead.id == workflow.lead_id).first()
        if not lead or not lead.linkedin_url:
            self._log_event(workflow, "linkedin_visit", "Skipped — no LinkedIn URL")
            return

        try:
            cookie = _get_linkedin_cookie(self.db, lead.user_id)
            if not cookie:
                self._log_event(workflow, "linkedin_visit", "Skipped — no active LinkedIn account")
                return
            from app.services.linkedin_service import LinkedInService
            service = LinkedInService(self.db)
            _run_async(service.visit_profile(lead.linkedin_url, cookie))
            self._log_event(workflow, "linkedin_visit", "Profile visited")
        except Exception as e:
            self._log_event(workflow, "linkedin_visit", f"Failed: {e}")
            logger.warning(f"LinkedIn visit failed for lead {lead.id}: {e}")

    def _action_send_email(self, workflow: Workflow, template_id: Optional[str]):
        """Send email via EmailService with AI-generated content."""
        lead = self.db.query(Lead).filter(Lead.id == workflow.lead_id).first()
        if not lead or not lead.email:
            self._log_event(workflow, "email", "Skipped — no email address")
            return

        try:
            from app.agents.personalization_agent import PersonalizationAgent
            agent = PersonalizationAgent()

            lead_dict = {
                "first_name": lead.first_name, "last_name": lead.last_name,
                "company_name": lead.company_name, "title": lead.title,
                "industry": lead.industry, "last_4_posts": lead.last_4_posts or [],
            }
            msg_data = _run_async(agent.generate_message(lead_dict, {}))

            from app.services.email_service import EmailService
            email_service = EmailService(self.db)

            message = Message(
                user_id=lead.user_id,
                lead_id=lead.id,
                direction="outbound",
                channel="email",
                subject=msg_data.get("subject_line", ""),
                body=msg_data.get("body", ""),
                ai_generated=True,
                status="pending",
                personalization_data=msg_data,
            )
            self.db.add(message)
            self.db.flush()

            from app.models.account import EmailAccount
            sender = self.db.query(EmailAccount).filter(
                EmailAccount.user_id == lead.user_id,
                EmailAccount.is_paused == False,
                EmailAccount.is_active == True,
            ).first()

            if sender:
                from app.core.encryption import decrypt_value
                smtp_pass = None
                if sender.smtp_password_encrypted:
                    try:
                        smtp_pass = decrypt_value(sender.smtp_password_encrypted)
                    except (ValueError, Exception) as exc:
                        logger.error(
                            "Failed to decrypt SMTP password for account %s: %s",
                            sender.email, exc,
                        )
                        # Never fall back to plaintext — skip this sender
                        smtp_pass = None

                email_service.send_email(
                    to_email=lead.email,
                    subject=message.subject,
                    body=message.body,
                    from_email=sender.email,
                    message_id=message.id,
                    smtp_host=sender.smtp_host,
                    smtp_port=sender.smtp_port,
                    smtp_user=sender.smtp_user,
                    smtp_password=smtp_pass,
                )
                self._log_event(workflow, "email", f"Email sent to {lead.email}")

                from app.services.ab_testing import ABTestingEngine
                ab = ABTestingEngine(self.db)
                ab.record_event(
                    workflow.campaign_id,
                    workflow.ab_variant_assigned or "default",
                    "email", "sent",
                )
            else:
                self._log_event(workflow, "email", "No active email account — queued")

        except Exception as e:
            self._log_event(workflow, "email", f"Failed: {e}")
            logger.warning(f"Email send failed for lead {lead.id}: {e}")

    def _action_linkedin_connect(self, workflow: Workflow):
        """Send LinkedIn connection request via LinkedInService."""
        lead = self.db.query(Lead).filter(Lead.id == workflow.lead_id).first()
        if not lead or not lead.linkedin_url:
            self._log_event(workflow, "linkedin_connect", "Skipped — no LinkedIn URL")
            return

        try:
            cookie = _get_linkedin_cookie(self.db, lead.user_id)
            if not cookie:
                self._log_event(workflow, "linkedin_connect", "Skipped — no active LinkedIn account")
                return
            from app.services.linkedin_service import LinkedInService
            service = LinkedInService(self.db)
            note = f"Hi {lead.first_name}, I'd love to connect."
            _run_async(service.send_connection(lead.linkedin_url, cookie, note))
            self._log_event(workflow, "linkedin_connect", "Connection request sent")
        except Exception as e:
            self._log_event(workflow, "linkedin_connect", f"Failed: {e}")
            logger.warning(f"LinkedIn connect failed for lead {lead.id}: {e}")

    def _action_linkedin_dm(self, workflow: Workflow, template_id: Optional[str]):
        """Send LinkedIn DM via LinkedInService."""
        lead = self.db.query(Lead).filter(Lead.id == workflow.lead_id).first()
        if not lead or not lead.linkedin_url:
            self._log_event(workflow, "linkedin_dm", "Skipped — no LinkedIn URL")
            return

        try:
            from app.agents.personalization_agent import PersonalizationAgent
            agent = PersonalizationAgent()

            lead_dict = {
                "first_name": lead.first_name, "last_name": lead.last_name,
                "company_name": lead.company_name, "title": lead.title,
                "industry": lead.industry,
            }
            msg_data = _run_async(agent.generate_message(lead_dict, {}))

            cookie = _get_linkedin_cookie(self.db, lead.user_id)
            if not cookie:
                self._log_event(workflow, "linkedin_dm", "Skipped — no active LinkedIn account")
                return
            from app.services.linkedin_service import LinkedInService
            service = LinkedInService(self.db)
            _run_async(
                service.send_dm(lead.linkedin_url, cookie, msg_data.get("body", ""))
            )
            self._log_event(workflow, "linkedin_dm", "DM sent")
        except Exception as e:
            self._log_event(workflow, "linkedin_dm", f"Failed: {e}")
            logger.warning(f"LinkedIn DM failed for lead {lead.id}: {e}")

    # ── Reply Detection (Auto-Stop) ──────────────────────
    def handle_reply_detected(self, lead_id: int, message_content: str, sentiment: str):
        """
        CRITICAL: When a reply is detected, stop ALL automation for this lead.
        This prevents the embarrassment of sending automated follow-ups after
        the lead has already responded.
        """
        # Stop all active workflows for this lead
        active_workflows = self.db.query(Workflow).filter(
            and_(
                Workflow.lead_id == lead_id,
                Workflow.status == "active",
            )
        ).all()

        for wf in active_workflows:
            wf.status = "stopped_reply"
            wf.next_scheduled = None
            self._log_event(wf, "auto_stop", f"Reply detected: {sentiment}")

        # Update lead status
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if lead:
            lead.status = "replied"
            lead.sentiment = sentiment

            # If positive sentiment, update campaign stats
            if sentiment == "positive":
                for wf in active_workflows:
                    campaign = wf.campaign
                    if campaign:
                        campaign.total_replied = (campaign.total_replied or 0) + 1
                        campaign.reply_rate = (
                            campaign.total_replied / max(campaign.total_contacted, 1)
                        ) * 100

        self.db.commit()

        # Create notification
        for wf in active_workflows:
            notif = Notification(
                user_id=lead.user_id if lead else 0,
                type="reply_received",
                title=f"Reply from {lead.first_name} {lead.last_name}" if lead else "Reply received",
                content=message_content[:500],
                lead_id=lead_id,
                campaign_id=wf.campaign_id,
            )
            self.db.add(notif)

        self.db.commit()
        logger.info(f"Auto-stopped {len(active_workflows)} workflows for lead {lead_id} (reply detected)")
