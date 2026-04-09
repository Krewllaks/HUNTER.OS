"""
HUNTER.OS - Content Analyst Agent
Analyzes a lead's digital footprint (posts, articles, comments) to extract
personality traits, communication style, pain points, and personalization hooks.
"""
import json
import logging

import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)


CONTENT_ANALYSIS_PROMPT = """You are the Content Analyst for HUNTER.OS / ARES Engine.

Your job: deeply analyze a person's digital content (LinkedIn posts, blog articles,
comments, tweets) to build a psychological and professional profile.

This profile will be used to craft hyper-personalized outreach messages.

## What to Extract:

1. **Communication Style**: formal, casual, mixed, academic, storytelling
2. **Topics They Care About**: recurring themes in their content
3. **Pain Points**: problems they mention or hint at
4. **Interests & Hobbies**: non-work interests visible in their content
5. **Tone & Sentiment**: optimistic, critical, analytical, motivational
6. **Recent Focus**: what they've been talking about most recently
7. **Engagement Patterns**: what type of content they engage with most
8. **Personality Signals**: introvert/extrovert, data-driven/intuitive, risk-taker/conservative
9. **Quotable Moments**: specific things they said that we can reference
10. **Best Approach**: how to approach this person based on their profile

## Output Format (strict JSON):
{
    "communication_style": "formal|casual|mixed|academic|storytelling",
    "topics": ["topic1", "topic2", "topic3"],
    "pain_points": ["pain1", "pain2"],
    "interests_hobbies": ["interest1", "interest2"],
    "tone": "optimistic|critical|analytical|motivational|neutral",
    "recent_focus": "What they've been most focused on recently",
    "personality_type": "analytical|driver|expressive|amiable",
    "quotable_moments": [
        {"source": "LinkedIn post", "quote": "exact or paraphrased quote", "context": "what it was about"}
    ],
    "engagement_style": "commenter|poster|sharer|lurker",
    "best_approach": {
        "opening_angle": "How to start the conversation",
        "tone_to_use": "Match their style description",
        "topics_to_reference": ["topic they'll respond to"],
        "avoid": ["things that would turn them off"]
    },
    "confidence": 0.0-1.0
}"""


class ContentAnalystAgent:
    """Analyzes a lead's digital content to build a personality profile."""

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=CONTENT_ANALYSIS_PROMPT,
        )

    async def analyze(self, lead_data: dict) -> dict:
        """Analyze all available content for a lead and return a profile."""
        content_pieces = []

        # Gather all content
        if lead_data.get("last_4_posts"):
            posts = lead_data["last_4_posts"]
            if isinstance(posts, list):
                for i, post in enumerate(posts):
                    if isinstance(post, dict):
                        content_pieces.append(f"LinkedIn Post {i+1}: {post.get('content', post.get('text', str(post)))}")
                    else:
                        content_pieces.append(f"LinkedIn Post {i+1}: {post}")
            elif isinstance(posts, str):
                content_pieces.append(f"LinkedIn Posts: {posts}")

        if lead_data.get("content_intent"):
            ci = lead_data["content_intent"]
            if isinstance(ci, list):
                for item in ci:
                    if isinstance(item, dict):
                        content_pieces.append(f"Content: {item.get('title', '')} - {item.get('summary', '')}")
                    else:
                        content_pieces.append(f"Content: {item}")
            elif isinstance(ci, str):
                content_pieces.append(f"Content Intent: {ci}")

        if lead_data.get("social_engagement"):
            se = lead_data["social_engagement"]
            if isinstance(se, list):
                for item in se:
                    if isinstance(item, dict):
                        content_pieces.append(f"Social: {item.get('platform', '')} - {item.get('content', item.get('action', str(item)))}")
                    else:
                        content_pieces.append(f"Social: {item}")

        if lead_data.get("media_quotes"):
            for quote in lead_data["media_quotes"]:
                if isinstance(quote, dict):
                    content_pieces.append(f"Quote ({quote.get('source', 'unknown')}): {quote.get('quote', '')}")

        # Build context
        all_content = "\n\n".join(content_pieces) if content_pieces else "No content available"

        prompt = f"""Analyze this person's digital footprint and build a profile.

## Person Info:
- Name: {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}
- Title: {lead_data.get('title', 'Unknown')}
- Company: {lead_data.get('company_name', 'Unknown')}
- Industry: {lead_data.get('industry', 'Unknown')}
- Communication Style (if known): {lead_data.get('communication_style', 'unknown')}
- Known Hobbies: {lead_data.get('hobbies', [])}

## Their Digital Content:
{all_content}

## Additional Signals:
- Technographics: {lead_data.get('technographics', [])}
- Hiring Signals: {lead_data.get('hiring_signals', [])}
- Recent News: {lead_data.get('recent_news', [])}
- Website Changes: {lead_data.get('website_changes', [])}

Build the most detailed profile possible from available data.
If data is limited, infer what you can from job title and industry, but set confidence lower."""

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                ),
            )
            result = json.loads(response.text.strip())
            logger.info(f"Content analysis completed for: {lead_data.get('first_name', 'Unknown')}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in content analysis: {e}")
            return self._fallback_profile(lead_data)
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return self._fallback_profile(lead_data)

    @staticmethod
    def _fallback_profile(lead_data: dict) -> dict:
        """Return a basic profile when AI analysis fails."""
        return {
            "communication_style": lead_data.get("communication_style", "formal"),
            "topics": [],
            "pain_points": [],
            "interests_hobbies": lead_data.get("hobbies", []),
            "tone": "neutral",
            "recent_focus": "",
            "personality_type": "analytical",
            "quotable_moments": [],
            "engagement_style": "unknown",
            "best_approach": {
                "opening_angle": "Direct value proposition",
                "tone_to_use": "Professional and respectful",
                "topics_to_reference": [],
                "avoid": ["Being too casual too early"],
            },
            "confidence": 0.1,
        }
