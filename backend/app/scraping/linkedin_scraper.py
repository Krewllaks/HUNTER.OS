"""
HUNTER.OS - LinkedIn Stealth Scraper
Extracts profile data, posts, engagement, and hiring signals.
"""
import asyncio
import re
import logging
from typing import Optional
from datetime import datetime, timezone

from app.scraping.stealth_browser import StealthBrowser

logger = logging.getLogger(__name__)


class LinkedInScraper:
    """
    Scrapes LinkedIn profiles & company pages using Playwright stealth mode.
    Requires a valid li_at session cookie.
    """

    def __init__(self, session_cookie: str, proxy: Optional[str] = None):
        self.session_cookie = session_cookie
        self.proxy = proxy

    async def scrape_profile(self, linkedin_url: str) -> dict:
        """
        Scrape a LinkedIn profile for:
        - Name, title, company, location
        - About section (for communication style analysis)
        - Last 4 posts
        - Hobbies / interests
        """
        async with StealthBrowser(
            proxy=self.proxy,
            session_cookie=self.session_cookie
        ) as browser:
            page = browser.page
            await browser.navigate(linkedin_url)

            # Wait for profile to load
            try:
                await page.wait_for_selector("h1", timeout=10000)
            except Exception:
                logger.warning(f"Profile load timeout: {linkedin_url}")
                return {"error": "Profile load timeout", "url": linkedin_url}

            # Scroll to load dynamic content
            await browser.human_scroll("down", 800)
            await asyncio.sleep(1)
            await browser.human_scroll("down", 800)

            profile_data = await page.evaluate("""
                () => {
                    const getText = (sel) => {
                        const el = document.querySelector(sel);
                        return el ? el.innerText.trim() : null;
                    };

                    const getAll = (sel) => {
                        return Array.from(document.querySelectorAll(sel))
                            .map(el => el.innerText.trim())
                            .filter(Boolean);
                    };

                    return {
                        name: getText('h1'),
                        headline: getText('.text-body-medium.break-words'),
                        location: getText('.text-body-small.inline.t-black--light.break-words'),
                        about: getText('#about ~ div .inline-show-more-text'),
                        experience: getAll('#experience ~ div .display-flex.align-items-center .mr1 .visually-hidden'),
                        education: getAll('#education ~ div .display-flex.align-items-center .mr1 .visually-hidden'),
                        current_company: getText('.inline-show-more-text .link-without-visited-state'),
                    };
                }
            """)

            # Get recent posts
            posts = await self._scrape_recent_posts(browser, linkedin_url)
            profile_data["recent_posts"] = posts

            # Get engagement data (what they like/comment on)
            engagement = await self._scrape_engagement(browser, linkedin_url)
            profile_data["engagement"] = engagement

            return profile_data

    async def _scrape_recent_posts(self, browser: StealthBrowser, profile_url: str) -> list:
        """Scrape last 4 posts from profile's activity."""
        activity_url = f"{profile_url.rstrip('/')}/recent-activity/all/"

        try:
            await browser.navigate(activity_url)
            await asyncio.sleep(2)
            await browser.human_scroll("down", 600)

            posts = await browser.page.evaluate("""
                () => {
                    const postElements = document.querySelectorAll('.feed-shared-update-v2');
                    const posts = [];
                    const items = Array.from(postElements).slice(0, 4);

                    for (const post of items) {
                        const textEl = post.querySelector('.feed-shared-text .break-words');
                        const timeEl = post.querySelector('.update-components-actor__sub-description .visually-hidden');
                        posts.push({
                            text: textEl ? textEl.innerText.trim().substring(0, 500) : '',
                            time: timeEl ? timeEl.innerText.trim() : '',
                        });
                    }
                    return posts;
                }
            """)
            return posts
        except Exception as e:
            logger.warning(f"Failed to scrape posts: {e}")
            return []

    async def _scrape_engagement(self, browser: StealthBrowser, profile_url: str) -> list:
        """Scrape what the person has liked/commented on recently."""
        reactions_url = f"{profile_url.rstrip('/')}/recent-activity/reactions/"

        try:
            await browser.navigate(reactions_url)
            await asyncio.sleep(2)

            engagement = await browser.page.evaluate("""
                () => {
                    const items = document.querySelectorAll('.feed-shared-update-v2');
                    const data = [];
                    const entries = Array.from(items).slice(0, 5);

                    for (const item of entries) {
                        const textEl = item.querySelector('.feed-shared-text .break-words');
                        const authorEl = item.querySelector('.update-components-actor__name .visually-hidden');
                        data.push({
                            author: authorEl ? authorEl.innerText.trim() : '',
                            content: textEl ? textEl.innerText.trim().substring(0, 300) : '',
                            type: 'reaction',
                        });
                    }
                    return data;
                }
            """)
            return engagement
        except Exception as e:
            logger.warning(f"Failed to scrape engagement: {e}")
            return []

    async def scrape_company_page(self, company_url: str) -> dict:
        """Scrape company page for technographics, hiring, and news."""
        async with StealthBrowser(
            proxy=self.proxy,
            session_cookie=self.session_cookie
        ) as browser:
            await browser.navigate(company_url)

            company_data = await browser.page.evaluate("""
                () => {
                    const getText = (sel) => {
                        const el = document.querySelector(sel);
                        return el ? el.innerText.trim() : null;
                    };

                    return {
                        name: getText('h1'),
                        tagline: getText('.org-top-card-summary__tagline'),
                        industry: getText('.org-top-card-summary-info-list__info-item'),
                        size: getText('.org-about-company-module__company-size-definition-text'),
                        description: getText('.org-about-us-organization-description__text'),
                        website: getText('.org-about-us-company-module__website'),
                    };
                }
            """)

            # Check jobs tab for hiring signals
            hiring = await self._scrape_company_jobs(browser, company_url)
            company_data["hiring_signals"] = hiring

            return company_data

    async def _scrape_company_jobs(self, browser: StealthBrowser, company_url: str) -> list:
        """Scrape open positions from company's LinkedIn jobs tab."""
        jobs_url = f"{company_url.rstrip('/')}/jobs/"

        try:
            await browser.navigate(jobs_url)
            await asyncio.sleep(2)

            jobs = await browser.page.evaluate("""
                () => {
                    const jobCards = document.querySelectorAll('.org-jobs-job-search-form-module__job-card-container');
                    return Array.from(jobCards).slice(0, 10).map(card => {
                        const titleEl = card.querySelector('.job-card-list__title');
                        const locationEl = card.querySelector('.job-card-container__metadata-item');
                        return {
                            role: titleEl ? titleEl.innerText.trim() : '',
                            location: locationEl ? locationEl.innerText.trim() : '',
                            platform: 'linkedin',
                            date: new Date().toISOString(),
                        };
                    });
                }
            """)
            return jobs
        except Exception as e:
            logger.warning(f"Failed to scrape company jobs: {e}")
            return []

    async def visit_profile(self, linkedin_url: str) -> bool:
        """
        Silent profile visit (for omnichannel workflow step 1).
        Just visits the profile to trigger LinkedIn notification.
        """
        try:
            async with StealthBrowser(
                proxy=self.proxy,
                session_cookie=self.session_cookie
            ) as browser:
                await browser.navigate(linkedin_url)
                await browser.human_scroll("down", 400)
                await asyncio.sleep(2)
                await browser.random_mouse_movement()
                return True
        except Exception as e:
            logger.error(f"Profile visit failed: {e}")
            return False
