"""
HUNTER.OS / ARES - Main Application Entry Point
AI-Powered Autonomous Sales Agentic System
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.core.logging_config import setup_logging
from app.core.middleware import RequestIDMiddleware

# ── API Routers ──────────────────────────────────────────
from app.api.v1.auth import router as auth_router
from app.api.v1.leads import router as leads_router
from app.api.v1.hunt import router as hunt_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.inbox import router as inbox_router
from app.api.v1.accounts import router as accounts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.products import router as products_router
from app.api.v1.messages import router as messages_router
from app.api.v1.tracking import router as tracking_router
from app.api.v1.billing import router as billing_router
from app.api.v1.audit import router as audit_router
from app.api.v1.gdpr import router as gdpr_router
from app.api.v1.crm import router as crm_router
from app.api.v1.footprint import router as footprint_router

# ── Logging ──────────────────────────────────────────────
setup_logging(debug=settings.DEBUG)
logger = logging.getLogger("hunter.os")

# ── Scheduler (Background Jobs) ─────────────────────────
scheduler = BackgroundScheduler()


def _run_scheduled_warmup():
    """Daily warmup progression."""
    from app.services.warmup_service import WarmupService
    db = SessionLocal()
    try:
        svc = WarmupService(db)
        svc.progress_warmup()
        svc.check_account_health()
    finally:
        db.close()


def _run_scheduled_workflows():
    """Process due workflow steps every 5 minutes."""
    from app.services.workflow_engine import WorkflowEngine
    db = SessionLocal()
    try:
        engine = WorkflowEngine(db)
        engine.process_due_workflows()
    finally:
        db.close()


def _run_daily_reset():
    """Reset daily counters at midnight."""
    from app.services.warmup_service import WarmupService
    db = SessionLocal()
    try:
        svc = WarmupService(db)
        svc.reset_daily_counters()
    finally:
        db.close()


def _run_reply_check():
    """Check for email replies every 2 minutes."""
    from app.services.imap_service import IMAPService
    db = SessionLocal()
    try:
        svc = IMAPService(db)
        replies = svc.check_replies()
        if replies:
            logger.info(f"Detected {len(replies)} new replies")
    except Exception as e:
        logger.error(f"Reply check failed: {e}")
    finally:
        db.close()


def _run_monthly_usage_reset():
    """Reset monthly usage counters on the 1st."""
    from app.models.user import User
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            user.usage_this_month = {}
        db.commit()
        logger.info(f"Monthly usage reset for {len(users)} users")
    finally:
        db.close()


# ── App Lifespan ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=" * 60)
    logger.info("  HUNTER.OS / ARES - Initializing...")
    logger.info("=" * 60)

    # Import all models so Base.metadata.create_all() picks them up
    import app.models.user  # noqa: F401
    import app.models.lead  # noqa: F401
    import app.models.product  # noqa: F401
    import app.models.campaign  # noqa: F401
    import app.models.message  # noqa: F401
    import app.models.account  # noqa: F401
    import app.models.lead_product  # noqa: F401
    import app.models.refresh_token  # noqa: F401
    import app.models.audit_log  # noqa: F401
    import app.models.linkedin_guard_state  # noqa: F401

    init_db()
    logger.info("Database initialized")

    # Schedule background jobs
    scheduler.add_job(_run_scheduled_workflows, "interval", minutes=5, id="workflow_processor")
    scheduler.add_job(_run_scheduled_warmup, "cron", hour=6, minute=0, id="daily_warmup")
    scheduler.add_job(_run_daily_reset, "cron", hour=0, minute=0, id="daily_reset")
    scheduler.add_job(_run_reply_check, "interval", minutes=2, id="reply_checker")
    scheduler.add_job(_run_monthly_usage_reset, "cron", day=1, hour=0, minute=5, id="monthly_usage_reset")
    scheduler.start()
    logger.info("Background scheduler started (5 jobs)")

    logger.info(f"API ready at {settings.API_V1_PREFIX}")
    logger.info("=" * 60)

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("HUNTER.OS shut down gracefully")


# ── FastAPI App ──────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Autonomous Sales Agentic System",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ── CORS (for Next.js frontend) ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# ── Request ID + Structured Logging Middleware ───────────
# Added AFTER CORS so it executes BEFORE CORS (Starlette LIFO)
app.add_middleware(RequestIDMiddleware)

# ── Register Routers ────────────────────────────────────
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(leads_router, prefix=settings.API_V1_PREFIX)
app.include_router(hunt_router, prefix=settings.API_V1_PREFIX)
app.include_router(campaigns_router, prefix=settings.API_V1_PREFIX)
app.include_router(inbox_router, prefix=settings.API_V1_PREFIX)
app.include_router(accounts_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(products_router, prefix=settings.API_V1_PREFIX)
app.include_router(messages_router, prefix=settings.API_V1_PREFIX)
app.include_router(tracking_router, prefix=settings.API_V1_PREFIX)
app.include_router(billing_router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_router, prefix=settings.API_V1_PREFIX)
app.include_router(gdpr_router, prefix=settings.API_V1_PREFIX)
app.include_router(crm_router, prefix=settings.API_V1_PREFIX)
app.include_router(footprint_router, prefix=settings.API_V1_PREFIX)


# ── Health Check ─────────────────────────────────────────
@app.get("/health")
def health_check():
    from sqlalchemy import text
    from app.core.database import SessionLocal

    result = {"status": "ok", "db": "unknown", "redis": "not_configured"}

    # Check database connectivity
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        result["db"] = "ok"
    except Exception as exc:
        result["db"] = f"error: {exc}"
        result["status"] = "degraded"

    # Check Redis connectivity (if configured)
    from app.core.redis import get_redis
    redis_client = get_redis()
    if redis_client:
        try:
            redis_client.ping()
            result["redis"] = "ok"
        except Exception as exc:
            result["redis"] = f"error: {exc}"
            result["status"] = "degraded"

    # Always return 200 so Railway / Vercel healthchecks don't fail the
    # deployment over a transient DB/Redis hiccup.  Operators can still
    # read result["status"] to know if something is degraded.
    from fastapi.responses import JSONResponse
    return JSONResponse(content=result, status_code=200)
