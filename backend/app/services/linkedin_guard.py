"""
HUNTER.OS - LinkedIn Anti-Ban Guard
Rate limiting, human behavior simulation, risk detection.
Persists state to DB (SQLite/PostgreSQL) for crash-safety and multi-worker support.
"""
import logging
import random
import asyncio
from datetime import datetime, date, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class LinkedInGuard:
    """
    Protects LinkedIn accounts from bans through:
    - Daily action limits with warmup schedule
    - Human-like delay patterns with fatigue simulation
    - Risk detection and auto-pause
    - Session scheduling (active/break cycles)

    State is persisted to DB. Falls back to in-memory if db is None.
    """

    # Daily limits per action type (at full capacity)
    DAILY_LIMITS = {
        "profile_view": 50,
        "connect": 25,
        "dm": 20,
        "search": 30,
        "follow": 20,
        "endorse": 15,
    }

    # Warmup schedule: gradually increase capacity over weeks
    WARMUP_SCHEDULE = {
        1: 0.30,  # Week 1: 30% capacity
        2: 0.60,  # Week 2: 60%
        3: 0.80,  # Week 3: 80%
        4: 1.00,  # Week 4+: full capacity
    }

    # Base delays per action (milliseconds)
    BASE_DELAYS = {
        "profile_view": 2000,
        "connect": 3000,
        "dm": 5000,
        "search": 2500,
        "follow": 2000,
        "endorse": 1500,
    }

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        # Static config — OK to keep in-memory (no persistence needed)
        self._account_age_weeks: dict[str, int] = {}
        # In-memory fallback when db is None
        self._daily_counts: dict[str, dict[str, int]] = {}
        self._session_start: dict[str, datetime] = {}
        self._action_count_session: dict[str, int] = {}
        self._paused_until: dict[str, datetime] = {}

    # ── DB helpers ────────────────────────────────────────────

    def _get_state(self, account_id: str):
        """Get or create today's state record for an account."""
        if not self.db:
            return None
        from app.models.linkedin_guard_state import LinkedInGuardState

        today = date.today()
        state = (
            self.db.query(LinkedInGuardState)
            .filter(
                LinkedInGuardState.account_id == account_id,
                LinkedInGuardState.date == today,
            )
            .first()
        )
        if not state:
            state = LinkedInGuardState(
                account_id=account_id,
                date=today,
                action_counts={},
                session_action_count=0,
            )
            self.db.add(state)
            self.db.flush()
        return state

    def _commit(self):
        """Commit DB changes, swallow errors to avoid breaking callers."""
        if not self.db:
            return
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"LinkedInGuard DB commit failed: {e}")
            self.db.rollback()

    # ── Public API (signatures unchanged) ─────────────────────

    def register_account(self, account_id: str, age_weeks: int = 52):
        """Register a LinkedIn account with its age for warmup calculation."""
        self._account_age_weeks[account_id] = age_weeks
        # Ensure state row exists in DB
        if self.db:
            self._get_state(account_id)
            self._commit()
        else:
            if account_id not in self._daily_counts:
                self._daily_counts[account_id] = {}

    def can_perform(self, account_id: str, action_type: str) -> dict:
        """
        Check if an action can be performed safely.
        Returns: {"allowed": bool, "reason": str, "wait_seconds": int}
        """
        # Check if account is paused
        paused_until = self._read_paused_until(account_id)
        if paused_until:
            now = datetime.now(timezone.utc)
            if now < paused_until:
                wait = (paused_until - now).total_seconds()
                return {
                    "allowed": False,
                    "reason": "account_paused",
                    "wait_seconds": int(wait),
                    "resume_at": str(paused_until),
                }
            else:
                self._clear_pause(account_id)

        # Check session schedule
        session_check = self._check_session(account_id)
        if not session_check["allowed"]:
            return session_check

        # Check daily limit
        limit = self._get_effective_limit(account_id, action_type)
        current = self._read_action_count(account_id, action_type)

        if current >= limit:
            return {
                "allowed": False,
                "reason": "daily_limit_reached",
                "current": current,
                "limit": limit,
                "wait_seconds": self._seconds_until_midnight(),
            }

        # Slow down at 80% capacity
        if limit > 0 and current / limit >= 0.80:
            return {
                "allowed": True,
                "reason": "approaching_limit",
                "speed_modifier": 0.5,  # Halve the speed
                "current": current,
                "limit": limit,
            }

        return {"allowed": True, "current": current, "limit": limit}

    def record_action(self, account_id: str, action_type: str):
        """Record that an action was performed."""
        if self.db:
            state = self._get_state(account_id)
            counts = dict(state.action_counts or {})
            counts[action_type] = counts.get(action_type, 0) + 1
            state.action_counts = counts
            state.session_action_count = (state.session_action_count or 0) + 1
            state.updated_at = datetime.now(timezone.utc)
            self._commit()
        else:
            if account_id not in self._daily_counts:
                self._daily_counts[account_id] = {}
            self._daily_counts[account_id][action_type] = (
                self._daily_counts[account_id].get(action_type, 0) + 1
            )
            self._action_count_session[account_id] = (
                self._action_count_session.get(account_id, 0) + 1
            )

    async def smart_delay(self, account_id: str, action_type: str):
        """Apply a human-like delay before an action."""
        base = self.BASE_DELAYS.get(action_type, 2000)
        jitter = random.uniform(0, base * 0.5)  # +/-50% jitter

        # Fatigue factor: delays increase with more actions in session
        session_count = self._read_session_action_count(account_id)
        fatigue = session_count * 50  # +50ms per action in session

        # Speed modifier from limit check
        check = self.can_perform(account_id, action_type)
        speed_mod = check.get("speed_modifier", 1.0)

        total_ms = (base + jitter + fatigue) / speed_mod
        total_seconds = total_ms / 1000

        logger.debug(
            f"LinkedIn delay: {total_seconds:.1f}s "
            f"(base={base}ms, jitter={jitter:.0f}ms, fatigue={fatigue}ms)"
        )
        await asyncio.sleep(total_seconds)

    async def simulate_page_behavior(self, page):
        """Simulate human-like page interaction before taking action."""
        # 1. Wait (reading simulation)
        await asyncio.sleep(random.uniform(2, 5))

        # 2. Random scroll (30-70% of page)
        scroll_pct = random.uniform(0.3, 0.7)
        try:
            await page.evaluate(f"window.scrollBy(0, window.innerHeight * {scroll_pct})")
        except Exception as exc:
            logger.debug("Human simulation scroll failed: %s", exc)
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # 3. Hover over a random element (optional)
        try:
            elements = await page.query_selector_all("a, button, span")
            if elements and len(elements) > 3:
                target = random.choice(elements[:10])
                await target.hover()
                await asyncio.sleep(random.uniform(0.3, 0.8))
        except Exception as exc:
            logger.debug("Human simulation hover failed: %s", exc)

    def auto_pause(self, account_id: str, reason: str, hours: int = 6):
        """Pause an account due to detected risk."""
        pause_until = datetime.now(timezone.utc) + timedelta(hours=hours)
        if self.db:
            state = self._get_state(account_id)
            state.paused_until = pause_until
            state.pause_reason = reason
            state.updated_at = datetime.now(timezone.utc)
            self._commit()
        else:
            self._paused_until[account_id] = pause_until
        logger.warning(
            f"LinkedIn account {account_id} paused for {hours}h. Reason: {reason}"
        )

    def handle_risk_signal(self, account_id: str, signal: str):
        """Handle risk signals from LinkedIn responses."""
        if signal == "http_429":
            self.auto_pause(account_id, "Rate limited (HTTP 429)", hours=6)
        elif signal == "captcha":
            self.auto_pause(account_id, "CAPTCHA detected", hours=24)
        elif signal == "unusual_activity":
            self.auto_pause(account_id, "Unusual activity warning", hours=48)
        elif signal == "consecutive_failures":
            self.auto_pause(account_id, "3+ consecutive failures", hours=0.5)

    def check_health(self, account_id: str) -> dict:
        """Get health score for an account (0-100, higher = safer)."""
        score = 100
        reasons = []

        # Check daily usage
        counts = self._read_all_action_counts(account_id)
        for action, count in counts.items():
            limit = self._get_effective_limit(account_id, action)
            if limit > 0:
                usage_pct = count / limit
                if usage_pct >= 0.9:
                    score -= 30
                    reasons.append(f"{action} at {usage_pct:.0%} capacity")
                elif usage_pct >= 0.7:
                    score -= 15
                    reasons.append(f"{action} at {usage_pct:.0%} capacity")

        # Check if paused
        paused_until = self._read_paused_until(account_id)
        if paused_until and datetime.now(timezone.utc) < paused_until:
            score -= 40
            reasons.append("Account currently paused")

        # Account age factor
        age = self._account_age_weeks.get(account_id, 52)
        if age < 26:  # Less than 6 months
            score -= 20
            reasons.append("Young account (< 6 months)")

        return {
            "score": max(0, score),
            "status": "healthy" if score >= 70 else "warning" if score >= 40 else "critical",
            "reasons": reasons,
            "daily_counts": counts,
        }

    def reset_daily_counters(self):
        """Reset all daily counters. Call at midnight."""
        if self.db:
            from app.models.linkedin_guard_state import LinkedInGuardState

            today = date.today()
            deleted = (
                self.db.query(LinkedInGuardState)
                .filter(LinkedInGuardState.date < today)
                .delete(synchronize_session="fetch")
            )
            self._commit()
            logger.info(f"LinkedIn daily counters reset (purged {deleted} old records)")
        else:
            self._daily_counts = {}
            self._action_count_session = {}
            logger.info("LinkedIn daily counters reset (in-memory)")

    def get_session_schedule(self) -> dict:
        """Get recommended session timing."""
        return {
            "active_minutes": 45,
            "break_minutes": random.randint(15, 30),
            "max_sessions_per_day": 4,
        }

    # ── DB-backed read helpers ────────────────────────────────

    def _read_action_count(self, account_id: str, action_type: str) -> int:
        """Read a single action count for today."""
        if self.db:
            state = self._get_state(account_id)
            return (state.action_counts or {}).get(action_type, 0)
        return self._daily_counts.get(account_id, {}).get(action_type, 0)

    def _read_all_action_counts(self, account_id: str) -> dict:
        """Read all action counts for today."""
        if self.db:
            state = self._get_state(account_id)
            return dict(state.action_counts or {})
        return dict(self._daily_counts.get(account_id, {}))

    def _read_session_action_count(self, account_id: str) -> int:
        """Read session action count."""
        if self.db:
            state = self._get_state(account_id)
            return state.session_action_count or 0
        return self._action_count_session.get(account_id, 0)

    def _read_paused_until(self, account_id: str) -> Optional[datetime]:
        """Read pause timestamp."""
        if self.db:
            state = self._get_state(account_id)
            return state.paused_until
        return self._paused_until.get(account_id)

    def _clear_pause(self, account_id: str):
        """Clear pause state."""
        if self.db:
            state = self._get_state(account_id)
            state.paused_until = None
            state.pause_reason = None
            state.updated_at = datetime.now(timezone.utc)
            self._commit()
        else:
            self._paused_until.pop(account_id, None)

    # ── Internal helpers ──────────────────────────────────────

    def _get_effective_limit(self, account_id: str, action_type: str) -> int:
        """Calculate effective limit considering warmup and account age."""
        base_limit = self.DAILY_LIMITS.get(action_type, 20)
        age = self._account_age_weeks.get(account_id, 52)

        # Warmup multiplier
        warmup_week = min(age, 4)
        warmup_mult = self.WARMUP_SCHEDULE.get(warmup_week, 1.0)

        # Young account penalty
        age_mult = 0.5 if age < 26 else 1.0

        return int(base_limit * warmup_mult * age_mult)

    def _check_session(self, account_id: str) -> dict:
        """Check if current session duration is within safe limits."""
        session_start = self._read_session_start(account_id)

        if not session_start:
            self._write_session_start(account_id, datetime.now(timezone.utc))
            return {"allowed": True}

        elapsed = (datetime.now(timezone.utc) - session_start).total_seconds()
        max_session = 45 * 60  # 45 minutes

        if elapsed > max_session:
            break_time = random.randint(15, 30) * 60
            new_start = datetime.now(timezone.utc) + timedelta(seconds=break_time)
            self._write_session_start(account_id, new_start)
            self._reset_session_count(account_id)
            return {
                "allowed": False,
                "reason": "session_break",
                "wait_seconds": break_time,
            }

        return {"allowed": True}

    def _read_session_start(self, account_id: str) -> Optional[datetime]:
        """Read session start timestamp."""
        if self.db:
            state = self._get_state(account_id)
            return state.session_started_at
        return self._session_start.get(account_id)

    def _write_session_start(self, account_id: str, ts: datetime):
        """Write session start timestamp."""
        if self.db:
            state = self._get_state(account_id)
            state.session_started_at = ts
            state.updated_at = datetime.now(timezone.utc)
            self._commit()
        else:
            self._session_start[account_id] = ts

    def _reset_session_count(self, account_id: str):
        """Reset session action count (on break)."""
        if self.db:
            state = self._get_state(account_id)
            state.session_action_count = 0
            state.updated_at = datetime.now(timezone.utc)
            self._commit()
        else:
            self._action_count_session[account_id] = 0

    @staticmethod
    def _seconds_until_midnight() -> int:
        """Seconds until midnight UTC."""
        now = datetime.now(timezone.utc)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return int((midnight - now).total_seconds())
