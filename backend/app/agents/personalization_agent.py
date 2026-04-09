"""
HUNTER.OS - Hyper-Personalization Agent (Gemini)
Generates deeply personalized messages that never feel like copy-paste.
Includes Ghost Objection Handler.
"""
import json
import logging
from typing import Optional

import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

PERSONALIZATION_SYSTEM_PROMPT = """You are the Hyper-Personalization Engine for HUNTER.OS.

You craft outreach messages that are so personalized, the recipient thinks:
"Wow, this person actually researched me."

## Your Personalization Layers (use ALL that apply):

1. **Style & Tone Matching**
   - Analyze the target's writing style from their LinkedIn posts/about section
   - Mirror their formality level (formal/casual/mixed)

2. **Common Ground Discovery**
   - Same university? Same city? Mutual connections?
   - Shared interests or followed influencers?

3. **Content Intent**
   - Reference their specific blog post, podcast appearance, or LinkedIn article
   - Quote them specifically - "In your post about X, you said Y..."

4. **Signal-Based Hook**
   - Hiring intent: "I see you're growing the sales team..."
   - Tech stack: "Noticed you're using X, which integrates perfectly with..."
   - News: "Congratulations on the recent funding round..."

5. **P.S. Strategy**
   - Add a non-business personal touch at the end (hobby, marathon, travel, etc.)

## Rules:
- NEVER use generic phrases like "I hope this finds you well"
- NEVER use "I'm reaching out because" - start with THEM, not you
- Keep emails under 120 words (LinkedIn DMs under 80 words)
- The first sentence MUST be personalized
- Sound like a human, not a sales bot
- Include ONE clear CTA (question, not demand)

## Output Format (strict JSON):
{
    "subject_line": "...",
    "body": "...",
    "ps_note": "...",
    "personalization_signals_used": ["hiring_intent", "linkedin_post"],
    "tone": "casual",
    "estimated_reply_probability": 0.35,
    "alternative_subject": "..."
}
"""

OBJECTION_SYSTEM_PROMPT = """You are an expert sales objection handler for HUNTER.OS.
You respond to objections with empathy, data, and a soft redirect.

## Objection Types & Strategies:
- **price**: Show ROI, offer case study, suggest smaller starting package
- **timing**: Agree, plant a seed, offer to schedule later with value
- **competitor**: Acknowledge, differentiate on ONE key feature
- **authority**: Help them build an internal case
- **not_interested**: Acknowledge, ask one clarifying question, graceful exit

## Rules:
- NEVER be pushy or desperate
- Match their tone
- Keep response under 80 words
- End with a soft question, not a demand

## Output Format (strict JSON):
{
    "response": "...",
    "strategy_used": "...",
    "tone": "...",
    "next_step_suggestion": "..."
}
"""


class PersonalizationAgent:
    """Generates hyper-personalized outreach messages via Gemini."""

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.message_model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=PERSONALIZATION_SYSTEM_PROMPT,
        )
        self.objection_model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=OBJECTION_SYSTEM_PROMPT,
        )

    async def generate_message(
        self,
        lead_data: dict,
        channel: str = "email",
        sender_context: Optional[dict] = None,
        campaign_context: Optional[str] = None,
        ab_variant: Optional[str] = None,
    ) -> dict:
        """Generate a personalized message for a specific lead."""
        channel_rules = {
            "email": "Full email with subject line. Max 120 words body.",
            "linkedin_dm": "LinkedIn DM. Max 80 words. No subject line needed.",
            "linkedin_connect": "LinkedIn connection request note. Max 300 characters.",
        }

        sender_info = json.dumps(sender_context, default=str) if sender_context else "A B2B sales professional."
        variant_note = f"\nA/B VARIANT: {ab_variant}" if ab_variant else ""

        prompt = f"""Generate a personalized {channel} message for this lead.

## Channel Rules:
{channel_rules.get(channel, channel_rules["email"])}

## Sender Context:
{sender_info}

## Campaign Goal:
{campaign_context or "Book a meeting/call with the lead."}

## Lead Intelligence Dossier:
{json.dumps(lead_data, indent=2, default=str)}
{variant_note}

Craft the most personalized message possible using ALL available intelligence signals."""

        try:
            response = await self.message_model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    response_mime_type="application/json",
                ),
            )
            result = json.loads(response.text)
            result["channel"] = channel
            return result
        except Exception as e:
            logger.error(f"Personalization failed: {e}")
            return {"error": str(e), "body": "", "channel": channel}

    async def generate_follow_up(
        self,
        lead_data: dict,
        previous_messages: list[dict],
        follow_up_number: int = 1,
        channel: str = "email",
    ) -> dict:
        """Generate a follow-up that doesn't repeat previous angles."""
        prev_summary = "\n".join([
            f"- Message {i+1} ({m.get('channel', 'email')}): {m.get('body', '')[:100]}..."
            for i, m in enumerate(previous_messages)
        ])

        prompt = f"""Generate follow-up #{follow_up_number} for this lead.

## CRITICAL: Do NOT repeat any angle from previous messages:
{prev_summary}

## Use a COMPLETELY DIFFERENT personalization angle this time.
## Keep it shorter than the original.

## Lead Intelligence:
{json.dumps(lead_data, indent=2, default=str)}"""

        try:
            response = await self.message_model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,
                    response_mime_type="application/json",
                ),
            )
            result = json.loads(response.text)
            result["channel"] = channel
            result["follow_up_number"] = follow_up_number
            return result
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            return {"error": str(e), "body": "", "channel": channel}

    async def generate_objection_response(
        self,
        lead_data: dict,
        objection_text: str,
        objection_type: str,
    ) -> dict:
        """Ghost Objection Handler: counter-argument for a lead's objection."""
        prompt = f"""The lead responded with an objection.

## Objection Type: {objection_type}
## Their exact words: "{objection_text}"

## Lead Context:
{json.dumps(lead_data, indent=2, default=str)}

Generate a thoughtful response that addresses their concern."""

        try:
            response = await self.objection_model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.5,
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Objection response failed: {e}")
            return {"error": str(e), "response": ""}
