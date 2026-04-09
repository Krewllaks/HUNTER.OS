"""
HUNTER.OS - Sentiment Analysis & Reply Detection Service
Classifies reply sentiment and triggers auto-stop on reply.
"""
import asyncio
import concurrent.futures
import json
import logging

import google.generativeai as genai
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.lead import Lead
from app.models.message import Message

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from sync context safely.

    If no event loop is running (e.g. APScheduler thread), uses asyncio.run()
    which properly creates and cleans up a loop. If called from within an
    existing loop (e.g. FastAPI), delegates to a thread pool to avoid deadlock.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=60)


SENTIMENT_PROMPT = """You are a sales reply analyst for HUNTER.OS.
Analyze the reply and classify it.

Output strict JSON:
{
    "sentiment": "positive|negative|neutral|objection",
    "confidence": 0.0-1.0,
    "intent": "meeting_request|price_inquiry|not_interested|info_request|referral|out_of_office|auto_reply|other",
    "summary": "One sentence summary of what they said",
    "should_stop_automation": true/false,
    "suggested_action": "schedule_meeting|send_info|handle_objection|mark_lost|wait|escalate",
    "urgency": "high|medium|low"
}

Rules:
- positive: interested, wants to learn more, asks questions about product
- negative: not interested, unsubscribe, hostile
- objection: price concern, timing issue, using competitor, needs approval
- neutral: out of office, auto-reply, unclear
- should_stop_automation = true for ANY human reply (never double-email someone who replied)
- auto_reply and out_of_office: should_stop_automation = false"""


class SentimentService:
    """Analyzes reply sentiment and manages automation stop signals."""

    def __init__(self, db: Session):
        self.db = db
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=SENTIMENT_PROMPT,
        )

    async def analyze_reply(self, reply_text: str, lead_data: dict = None) -> dict:
        """Analyze a reply's sentiment and intent."""
        context = ""
        if lead_data:
            context = f"""
Context:
- Lead: {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}
- Company: {lead_data.get('company_name', '')}
- Title: {lead_data.get('title', '')}
- Previous status: {lead_data.get('status', 'contacted')}"""

        prompt = f"""Analyze this reply from a sales prospect:

Reply text: "{reply_text}"
{context}

Classify the sentiment, intent, and recommended action."""

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text.strip())
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "confidence": 0.3,
                "intent": "other",
                "summary": "Could not analyze reply",
                "should_stop_automation": True,
                "suggested_action": "escalate",
                "urgency": "medium",
            }

    def process_reply(self, message_id: int, reply_text: str) -> dict:
        """Process an incoming reply: analyze sentiment, update lead, stop automation."""
        msg = self.db.query(Message).filter(Message.id == message_id).first()
        if not msg:
            return {"error": "Message not found"}

        lead = self.db.query(Lead).filter(Lead.id == msg.lead_id).first()
        if not lead:
            return {"error": "Lead not found"}

        # Analyze sentiment
        lead_data = {
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "company_name": lead.company_name,
            "title": lead.title,
            "status": lead.status,
        }

        analysis = _run_async(self.analyze_reply(reply_text, lead_data))

        # Update message with sentiment
        msg.sentiment_label = analysis.get("sentiment", "neutral")
        msg.sentiment_confidence = analysis.get("confidence", 0.5)
        msg.auto_label = analysis.get("intent", "other")

        # Update lead status
        sentiment = analysis.get("sentiment")
        if sentiment == "positive":
            lead.status = "replied"
            lead.sentiment = "positive"
        elif sentiment == "negative":
            lead.sentiment = "negative"
            if analysis.get("intent") == "not_interested":
                lead.status = "lost"
        elif sentiment == "objection":
            lead.sentiment = "objection"
            lead.objection_type = analysis.get("intent")
            lead.status = "replied"
        else:
            lead.status = "replied"
            lead.sentiment = "neutral"

        # Stop automation if needed
        if analysis.get("should_stop_automation", True):
            self._stop_lead_automation(lead)

        self.db.commit()
        logger.info(
            f"Reply processed for lead {lead.id}: "
            f"sentiment={sentiment}, intent={analysis.get('intent')}"
        )

        return {
            "lead_id": lead.id,
            "analysis": analysis,
            "lead_status": lead.status,
            "automation_stopped": analysis.get("should_stop_automation", True),
        }

    def _stop_lead_automation(self, lead: Lead):
        """Stop all active automation for a lead."""
        from app.models.campaign import Workflow

        workflows = self.db.query(Workflow).filter(
            Workflow.lead_id == lead.id,
            Workflow.status == "active",
        ).all()

        for wf in workflows:
            wf.status = "stopped_reply"
            wf.event_log = (wf.event_log or []) + [{
                "action": "auto_stopped",
                "reason": "reply_detected",
                "timestamp": str(lead.updated_at),
            }]

        if workflows:
            logger.info(f"Stopped {len(workflows)} active workflows for lead {lead.id}")
