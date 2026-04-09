"""
HUNTER.OS - Research Agent
ReAct agent that hunts for lead intelligence signals.
Uses Step-Back Prompting for context compression.
"""
import json
import logging
from typing import Optional

from app.agents.base_agent import ReActAgent
from app.scraping.linkedin_scraper import LinkedInScraper
from app.scraping.website_scraper import WebsiteScraper, NewsScraper

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = """You are ARES, an elite sales intelligence research agent for HUNTER.OS.

Your mission is to build a comprehensive intelligence dossier on a target lead/company.
You must gather ACTIONABLE signals that indicate buying intent.

## Your Intelligence Priorities (in order):
1. **Technographics**: What tech stack does the company use? What are they missing?
2. **Hiring Intent**: What positions are they hiring for? What does this reveal about their plans?
3. **News & Funding**: Any recent funding, acquisitions, leadership changes?
4. **Website Changes**: New pages, pricing changes, new products/services?
5. **Content Intent**: CEO's recent posts, podcast appearances, blog articles?
6. **Social Engagement**: What topics are they engaging with on LinkedIn?
7. **Competitive Displacement**: Signs of switching from a competitor?

## Step-Back Prompting Rule:
When you receive large amounts of data (full web pages, long post histories), you MUST
compress it using this technique:
- Step back and ask: "What is the KEY INSIGHT from this data for a sales approach?"
- Summarize to 2-3 sentences max per signal
- Focus ONLY on actionable intelligence

## Output Quality:
- Every signal must have a CONFIDENCE score (low/medium/high)
- Every signal must suggest a PERSONALIZATION ANGLE
- If data is insufficient, say so honestly - never fabricate signals
"""


def create_research_agent(
    linkedin_cookie: Optional[str] = None,
    proxy: Optional[str] = None,
) -> ReActAgent:
    """Factory: creates a research agent with scraping tools."""

    linkedin = LinkedInScraper(session_cookie=linkedin_cookie or "", proxy=proxy)
    website = WebsiteScraper(proxy=proxy)
    news = NewsScraper(proxy=proxy)

    # ── Tool functions ───────────────────────────────────
    async def scrape_linkedin_profile(url: str) -> dict:
        """Scrape a LinkedIn profile for name, title, about, posts, and engagement data."""
        try:
            return await linkedin.scrape_profile(url)
        except Exception as e:
            return {"error": str(e), "url": url}

    async def scrape_company_page(url: str) -> dict:
        """Scrape a LinkedIn company page for description, size, industry, and hiring signals."""
        try:
            return await linkedin.scrape_company_page(url)
        except Exception as e:
            return {"error": str(e), "url": url}

    async def analyze_website(domain: str) -> dict:
        """Analyze a company website for technographics (tech stack), content, and structure."""
        try:
            return await website.analyze_website(domain)
        except Exception as e:
            return {"error": str(e), "domain": domain}

    async def search_news(company_name: str) -> list:
        """Search Google News for recent company mentions: funding, hiring, acquisitions, product launches."""
        try:
            return await news.search_company_news(company_name)
        except Exception as e:
            return [{"error": str(e)}]

    def compress_context(text: str, focus: str = "sales_signals") -> str:
        """Step-Back Prompting: Compress a large text into key sales-relevant insights (2-3 sentences)."""
        if len(text) > 3000:
            return text[:3000] + "\n...[TRUNCATED - Use Step-Back Prompting to extract key signals]"
        return text

    tools = {
        "scrape_linkedin_profile": scrape_linkedin_profile,
        "scrape_company_page": scrape_company_page,
        "analyze_website": analyze_website,
        "search_news": search_news,
        "compress_context": compress_context,
    }

    return ReActAgent(
        system_prompt=RESEARCH_SYSTEM_PROMPT,
        tools=tools,
        max_steps=8,
    )
