"""
HUNTER.OS - Lead Scoring Agent (Gemini Chain-of-Thought)
Transparent scoring with step-by-step reasoning.
"""
import json
import logging
from typing import Optional

import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

SCORING_SYSTEM_PROMPT = """You are the Lead Scoring Engine for HUNTER.OS.

You score leads using Chain-of-Thought reasoning. For each lead, you must:

## Scoring Dimensions (each 0-100):

1. **ICP Match** (weight: 30%)
   - Does the company match the Ideal Customer Profile?
   - Right industry? Right size? Right tech stack?

2. **Intent Signals** (weight: 35%)
   - Hiring signals: Are they hiring for roles that suggest need for our product?
   - News signals: Recent funding/growth/leadership changes?
   - Website changes: New products/services that suggest expansion?
   - Content engagement: Are they engaging with relevant topics?

3. **Accessibility** (weight: 15%)
   - Do we have a valid email?
   - Do we have LinkedIn access?
   - Is there a buying committee member we can reach?

4. **Timing** (weight: 20%)
   - How fresh are the signals? (last 7 days = hot, 30 days = warm, 90 days = cool)
   - Are they in a buying cycle?

## Confidence Score:
Also output a confidence score (0-100) based on data completeness:
- Full profile + website + news + social = 80-100
- Profile + website only = 50-70
- Just a name and email = 10-30

## Output Format (strict JSON):
{
    "chain_of_thought": "Step-by-step reasoning...",
    "icp_match_score": 75,
    "intent_score": 82,
    "accessibility_score": 90,
    "timing_score": 60,
    "final_score": 77.5,
    "confidence": 85,
    "top_signals": ["hiring_sales_reps", "recent_funding"],
    "recommended_approach": "Lead with hiring intent angle...",
    "urgency": "high"
}
"""


class ScoringAgent:
    """Chain-of-Thought lead scoring with transparent reasoning via Gemini."""

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=SCORING_SYSTEM_PROMPT,
        )

    async def score_lead(self, lead_data: dict, icp_criteria: Optional[dict] = None) -> dict:
        """
        Score a single lead using CoT reasoning.
        Returns scoring result with chain-of-thought reasoning.
        """
        icp_text = json.dumps(icp_criteria, default=str) if icp_criteria else "No specific ICP defined - use general B2B criteria."

        prompt = f"""Score this lead using Chain-of-Thought reasoning.

## ICP Criteria:
{icp_text}

## Lead Intelligence Data:
{json.dumps(lead_data, indent=2, default=str)}

Think step by step through each scoring dimension, then produce the final JSON score."""

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )

            result = json.loads(response.text)

            # Calculate weighted score if not provided
            if "final_score" not in result:
                result["final_score"] = round(
                    result.get("icp_match_score", 0) * 0.30 +
                    result.get("intent_score", 0) * 0.35 +
                    result.get("accessibility_score", 0) * 0.15 +
                    result.get("timing_score", 0) * 0.20,
                    1,
                )

            return result

        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            return {
                "error": str(e),
                "final_score": 0,
                "confidence": 0,
                "chain_of_thought": f"Scoring failed: {e}",
            }

    async def batch_score(self, leads: list[dict], icp_criteria: Optional[dict] = None) -> list[dict]:
        """Score multiple leads. Must be called from an async context."""
        results = []
        for lead_data in leads:
            score = await self.score_lead(lead_data, icp_criteria)
            score["lead_id"] = lead_data.get("id")
            results.append(score)

        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        return results
