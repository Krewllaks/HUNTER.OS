"""
HUNTER.OS - LinkedIn Automation Service
Profile visits, connection requests, direct messages with anti-ban protection.
"""
import logging
import asyncio
from typing import Optional

from sqlalchemy.orm import Session

from app.services.linkedin_guard import LinkedInGuard
from app.scraping.stealth_browser import StealthBrowser

logger = logging.getLogger(__name__)


class LinkedInService:
    """LinkedIn automation with LinkedInGuard protection."""

    def __init__(self, db: Session, account_id: str = "default"):
        self.db = db
        self.account_id = account_id
        self.guard = LinkedInGuard(db)
        self.guard.register_account(account_id)

    async def visit_profile(self, profile_url: str, li_at_cookie: str) -> dict:
        """Visit a LinkedIn profile (generates a notification to the person)."""
        check = self.guard.can_perform(self.account_id, "profile_view")
        if not check["allowed"]:
            return {"status": "blocked", **check}

        await self.guard.smart_delay(self.account_id, "profile_view")

        try:
            async with StealthBrowser(cookies=[{"name": "li_at", "value": li_at_cookie, "domain": ".linkedin.com"}]) as browser:
                await browser.navigate(profile_url)
                await self.guard.simulate_page_behavior(browser.page)

                # Extract profile name for logging
                name = await browser.page.evaluate(
                    "document.querySelector('h1')?.innerText || 'Unknown'"
                )

                self.guard.record_action(self.account_id, "profile_view")
                logger.info(f"LinkedIn profile visited: {name}")
                return {"status": "visited", "name": name, "url": profile_url}

        except Exception as e:
            if "429" in str(e):
                self.guard.handle_risk_signal(self.account_id, "http_429")
            logger.error(f"LinkedIn profile visit failed: {e}")
            return {"status": "error", "detail": str(e)}

    async def send_connection(
        self,
        profile_url: str,
        li_at_cookie: str,
        note: Optional[str] = None,
    ) -> dict:
        """Send a LinkedIn connection request with optional note."""
        check = self.guard.can_perform(self.account_id, "connect")
        if not check["allowed"]:
            return {"status": "blocked", **check}

        # Always visit profile before connecting (human pattern)
        await self.visit_profile(profile_url, li_at_cookie)
        await self.guard.smart_delay(self.account_id, "connect")

        try:
            async with StealthBrowser(cookies=[{"name": "li_at", "value": li_at_cookie, "domain": ".linkedin.com"}]) as browser:
                await browser.navigate(profile_url)
                await self.guard.simulate_page_behavior(browser.page)

                # Click Connect button
                connected = await browser.page.evaluate("""
                    () => {
                        const btns = Array.from(document.querySelectorAll('button'));
                        const connectBtn = btns.find(b =>
                            b.innerText.includes('Connect') && !b.innerText.includes('Connected')
                        );
                        if (connectBtn) { connectBtn.click(); return true; }
                        return false;
                    }
                """)

                if not connected:
                    return {"status": "already_connected_or_button_not_found"}

                await asyncio.sleep(1.5)

                # Add note if provided
                if note:
                    await browser.page.evaluate(f"""
                        () => {{
                            const addNote = Array.from(document.querySelectorAll('button'))
                                .find(b => b.innerText.includes('Add a note'));
                            if (addNote) {{ addNote.click(); }}
                        }}
                    """)
                    await asyncio.sleep(1)
                    textarea = await browser.page.query_selector("textarea")
                    if textarea:
                        await textarea.fill(note[:300])  # 300 char limit
                        await asyncio.sleep(0.5)

                # Click Send
                await browser.page.evaluate("""
                    () => {
                        const sendBtn = Array.from(document.querySelectorAll('button'))
                            .find(b => b.innerText.includes('Send'));
                        if (sendBtn) { sendBtn.click(); }
                    }
                """)

                self.guard.record_action(self.account_id, "connect")
                logger.info(f"LinkedIn connection sent to: {profile_url}")
                return {"status": "sent", "url": profile_url, "note": bool(note)}

        except Exception as e:
            if "429" in str(e) or "captcha" in str(e).lower():
                self.guard.handle_risk_signal(self.account_id, "http_429")
            logger.error(f"LinkedIn connection failed: {e}")
            return {"status": "error", "detail": str(e)}

    async def send_dm(
        self,
        profile_url: str,
        li_at_cookie: str,
        message: str,
    ) -> dict:
        """Send a LinkedIn direct message."""
        check = self.guard.can_perform(self.account_id, "dm")
        if not check["allowed"]:
            return {"status": "blocked", **check}

        await self.guard.smart_delay(self.account_id, "dm")

        try:
            async with StealthBrowser(cookies=[{"name": "li_at", "value": li_at_cookie, "domain": ".linkedin.com"}]) as browser:
                await browser.navigate(profile_url)
                await self.guard.simulate_page_behavior(browser.page)

                # Click Message button
                msg_btn_found = await browser.page.evaluate("""
                    () => {
                        const btns = Array.from(document.querySelectorAll('button'));
                        const msgBtn = btns.find(b => b.innerText.includes('Message'));
                        if (msgBtn) { msgBtn.click(); return true; }
                        return false;
                    }
                """)

                if not msg_btn_found:
                    return {"status": "message_button_not_found"}

                await asyncio.sleep(2)

                # Type message
                msg_box = await browser.page.query_selector("div[role='textbox']")
                if msg_box:
                    await msg_box.fill(message)
                    await asyncio.sleep(1)

                    # Send
                    await browser.page.evaluate("""
                        () => {
                            const sendBtn = Array.from(document.querySelectorAll('button'))
                                .find(b => b.innerText.includes('Send'));
                            if (sendBtn) { sendBtn.click(); }
                        }
                    """)

                    self.guard.record_action(self.account_id, "dm")
                    logger.info(f"LinkedIn DM sent to: {profile_url}")
                    return {"status": "sent", "url": profile_url}
                else:
                    return {"status": "message_box_not_found"}

        except Exception as e:
            if "captcha" in str(e).lower():
                self.guard.handle_risk_signal(self.account_id, "captcha")
            logger.error(f"LinkedIn DM failed: {e}")
            return {"status": "error", "detail": str(e)}

    def get_account_health(self) -> dict:
        """Get current account health status."""
        return self.guard.check_health(self.account_id)
