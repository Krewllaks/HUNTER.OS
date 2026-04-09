"""
HUNTER.OS / ARES - Core Configuration
Environment-based settings with Pydantic + dotenv
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "HUNTER.OS"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./hunter.db"

    # ── JWT Auth ─────────────────────────────────────────
    SECRET_KEY: str  # REQUIRED - no default, must be set in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Long-lived refresh token

    # ── Gemini / LLM ────────────────────────────────────
    GEMINI_API_KEY: str  # REQUIRED - no default, must be set in .env
    GEMINI_MODEL: str = "gemini-2.0-flash"
    LLM_TEMPERATURE: float = 0.7

    # ── LLM Cost Controls ──────────────────────────────
    LLM_MONTHLY_TOKEN_BUDGET_TRIAL: int = 500_000
    LLM_MONTHLY_TOKEN_BUDGET_PRO: int = 25_000_000
    LLM_MONTHLY_TOKEN_BUDGET_ENTERPRISE: int = 100_000_000
    LLM_COST_ALERT_THRESHOLD: float = 0.8  # Alert at 80% budget

    # ── Credential Encryption ──────────────────────────
    ENCRYPTION_KEY: Optional[str] = None  # Fernet key for encrypting stored credentials

    # ── Redis ───────────────────────────────────────────
    REDIS_URL: Optional[str] = None  # e.g. redis://localhost:6379/0

    # ── Sentry ──────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None

    # ── Scraping ─────────────────────────────────────────
    PLAYWRIGHT_HEADLESS: bool = True
    PROXY_POOL: list[str] = []
    MAX_CONCURRENT_SCRAPERS: int = 5
    SCRAPE_TIMEOUT_MS: int = 30000

    # ── Email ────────────────────────────────────────────
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # ── Warmup ───────────────────────────────────────────
    WARMUP_START_DAILY: int = 5
    WARMUP_INCREMENT: int = 3
    WARMUP_MAX_DAILY: int = 50
    WARMUP_DURATION_DAYS: int = 14

    # ── Bridge (Telegram / WhatsApp) ─────────────────────
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    WHATSAPP_API_URL: Optional[str] = None
    WHATSAPP_API_TOKEN: Optional[str] = None

    # ── IMAP (Reply Detection) ──────────────────────────
    IMAP_HOST: Optional[str] = None
    IMAP_PORT: int = 993
    IMAP_USER: Optional[str] = None
    IMAP_PASSWORD: Optional[str] = None

    # ── Lead Enrichment APIs ───────────────────────────
    FULLCONTACT_API_KEY: Optional[str] = None
    HUNTER_IO_API_KEY: Optional[str] = None
    SNOV_IO_CLIENT_ID: Optional[str] = None
    SNOV_IO_CLIENT_SECRET: Optional[str] = None
    ROCKETREACH_API_KEY: Optional[str] = None
    BUILTWITH_API_KEY: Optional[str] = None

    # ── CRM ──────────────────────────────────────────────
    HUBSPOT_API_KEY: Optional[str] = None
    PIPEDRIVE_API_KEY: Optional[str] = None

    # ── LemonSqueezy ──────────────────────────────────────
    LEMONSQUEEZY_API_KEY: Optional[str] = None
    LEMONSQUEEZY_STORE_ID: Optional[str] = None
    LEMONSQUEEZY_WEBHOOK_SECRET: Optional[str] = None

    # ── Google News ──────────────────────────────────────
    GOOGLE_NEWS_API_KEY: Optional[str] = None

    # ── Google Custom Search API (CAPTCHA-free alternative) ──
    GOOGLE_SEARCH_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_CX: Optional[str] = None

    # ── Default Sender ─────────────────────────────────────
    DEFAULT_FROM_EMAIL: Optional[str] = None

    # ══════════════════════════════════════════════════════
    # Phase 11 — Cost Optimization & Data Quality
    # ══════════════════════════════════════════════════════
    # All new fields below are Optional and default to safe values.
    # When a key is empty the related feature silently no-ops, so the
    # existing Phase 1-10 behaviour stays fully backward compatible.

    # ── SERP Provider (cheapest 2026: ScrapingDog) ────────
    # Price: $3 / 1,000 requests · Free: 1,000 requests/month
    # Docs: https://www.scrapingdog.com/documentation/google
    SCRAPINGDOG_API_KEY: Optional[str] = None

    # ── Enrichment Providers (free tiers first) ───────────
    # Apollo.io — best free email finder (50 people match / month)
    APOLLO_API_KEY: Optional[str] = None
    # People Data Labs — profile enrichment ONLY (needs an existing
    # email). Free tier: 1,000 records / month.
    PDL_API_KEY: Optional[str] = None

    # ── IPRoyal Residential Proxy (cheapest 2026 ~$1.5/GB) ──
    # Sticky session format: user-session-N:pass@host:port
    IPROYAL_USERNAME: Optional[str] = None
    IPROYAL_PASSWORD: Optional[str] = None
    IPROYAL_ENDPOINT: str = "geo.iproyal.com:12321"
    IPROYAL_POOL_SIZE: int = 10  # number of sticky sessions to rotate

    # ── Score thresholds (budget protection) ─────────────
    # Discovery: only persist leads with intent_score >= this value.
    # Enrichment: only call paid/free providers if intent_score >= this.
    # Tightening these two numbers is the single biggest cost lever.
    INTENT_SCORE_THRESHOLD_DISCOVERY: int = 50
    INTENT_SCORE_THRESHOLD_ENRICHMENT: int = 60

    # ── Cache TTL ────────────────────────────────────────
    # Default 30 days. Raise for even cheaper ops, lower if data
    # freshness matters more than cost for your use case.
    CACHE_TTL_DAYS: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
