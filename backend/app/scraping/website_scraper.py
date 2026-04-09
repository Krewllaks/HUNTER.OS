"""
HUNTER.OS - Website Intelligence Scraper
Technographics detection, website change monitoring, content extraction.
"""
import re
import logging
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone

from app.scraping.stealth_browser import StealthBrowser

logger = logging.getLogger(__name__)

TECH_SIGNATURES = {
    "Shopify": [r"cdn\.shopify\.com", r"Shopify\.theme"],
    "WordPress": [r"wp-content", r"wp-includes"],
    "HubSpot": [r"hubspot\.com", r"hs-scripts"],
    "Stripe": [r"stripe\.com", r"Stripe\("],
    "Next.js": [r"__NEXT_DATA__", r"_next/"],
}

class WebsiteScraper:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy

    async def analyze_website(self, domain: str) -> Dict[str, Any]:
        url = f"https://{domain}" if not domain.startswith("http") else domain
        async with StealthBrowser(proxy=self.proxy) as browser:
            html = await browser.navigate(url)
            page_text = await browser.extract_text()
            tech_stack = self._detect_technologies(html)
            
            return {
                "domain": domain,
                "tech_stack": tech_stack,
                "page_text": page_text[:2000],
                "scraped_at": datetime.now(timezone.utc).isoformat()
            }

    def _detect_technologies(self, html: str) -> List[Dict[str, str]]:
        detected = []
        html_lower = html.lower()
        for tech, patterns in TECH_SIGNATURES.items():
            if any(re.search(p, html_lower) for p in patterns):
                detected.append({"name": tech, "confidence": "high"})
        return detected

class NewsScraper:
    """Eksik olan NewsScraper sınıfı eklendi."""
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy

    async def search_company_news(self, company_name: str, max_results: int = 5) -> List[Dict[str, str]]:
        query = f"{company_name} funding OR hiring OR launch"
        search_url = f"https://news.google.com/search?q={query.replace(' ', '%20')}&hl=en"
        
        async with StealthBrowser(proxy=self.proxy) as browser:
            try:
                await browser.navigate(search_url)
                await asyncio.sleep(2)
                
                # Regex dizesi r"" (raw) olarak düzeltildi
                articles = await browser.page.evaluate(r"""
                    (max) => {
                        const items = document.querySelectorAll('article');
                        return Array.from(items).slice(0, max).map(item => ({
                            headline: item.querySelector('a')?.innerText || '',
                            url: item.querySelector('a')?.href || '',
                            date: item.querySelector('time')?.getAttribute('datetime') || ''
                        })).filter(a => a.headline.length > 0);
                    }
                """, max_results)
                return articles
            except Exception as e:
                logger.error(f"News scrape failed: {e}")
                return []