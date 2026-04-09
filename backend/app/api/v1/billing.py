"""
HUNTER.OS - Billing & Subscription API
LemonSqueezy integration for trial/pro/enterprise plans.
"""
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.plan_limiter import PlanLimiter, PLAN_LIMITS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])

LEMONSQUEEZY_API = "https://api.lemonsqueezy.com/v1"


def _ls_headers() -> dict:
    """LemonSqueezy API headers."""
    return {
        "Authorization": f"Bearer {settings.LEMONSQUEEZY_API_KEY}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


# ── Usage ──────────────────────────────────────────────
@router.get("/usage")
def get_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current plan usage and limits."""
    limiter = PlanLimiter(db)
    return limiter.get_usage_summary(current_user)


# ── Plans ──────────────────────────────────────────────
@router.get("/plans")
def get_plans():
    """Get available plans and their features."""
    return {
        "plans": [
            {
                "id": "trial",
                "name": "Trial",
                "price": 0,
                "currency": "USD",
                "interval": "forever",
                "features": PLAN_LIMITS["trial"],
                "description": "10 lead keşfi + 5 mesaj ile başlayın",
            },
            {
                "id": "pro",
                "name": "Pro",
                "price": 49,
                "currency": "USD",
                "interval": "month",
                "features": PLAN_LIMITS["pro"],
                "description": "Sınırsız keşif, mesaj, LinkedIn otomasyonu",
                "popular": True,
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price": 149,
                "currency": "USD",
                "interval": "month",
                "features": PLAN_LIMITS["enterprise"],
                "description": "Çoklu ürün, takım, API erişimi",
            },
        ],
    }


# ── Checkout ───────────────────────────────────────────
class CheckoutRequest(BaseModel):
    plan: str = "pro"  # "pro" or "enterprise"
    variant_id: Optional[str] = None


@router.post("/checkout")
async def create_checkout(
    req: CheckoutRequest = CheckoutRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a LemonSqueezy checkout session."""
    if not settings.LEMONSQUEEZY_API_KEY:
        raise HTTPException(503, "Ödeme sistemi henüz yapılandırılmamış")

    # If variant_id provided directly, use it
    variant_id = req.variant_id

    # Otherwise, try to find the right variant from the store
    if not variant_id and settings.LEMONSQUEEZY_STORE_ID:
        variant_id = await _find_variant_for_plan(req.plan)

    if not variant_id:
        # Fallback: list store products and find matching variant
        variant_id = await _find_variant_for_plan(req.plan)

    if not variant_id:
        raise HTTPException(
            400,
            "Plan bulunamadı. LemonSqueezy'de ürün oluşturmanız gerekiyor.",
        )

    # Create checkout via LemonSqueezy API
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": current_user.email,
                    "name": current_user.full_name or "",
                    "custom": {
                        "user_id": str(current_user.id),
                    },
                },
            },
            "relationships": {
                "store": {
                    "data": {
                        "type": "stores",
                        "id": settings.LEMONSQUEEZY_STORE_ID,
                    }
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": variant_id,
                    }
                },
            },
        }
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{LEMONSQUEEZY_API}/checkouts",
            headers=_ls_headers(),
            json=payload,
        )

    if resp.status_code not in (200, 201):
        logger.error(f"LemonSqueezy checkout error: {resp.status_code} {resp.text}")
        raise HTTPException(502, "Checkout oluşturulamadı, lütfen tekrar deneyin")

    data = resp.json()
    checkout_url = data["data"]["attributes"]["url"]

    return {
        "checkout_url": checkout_url,
        "current_plan": getattr(current_user, "plan", "trial"),
    }


# ── Store Info ─────────────────────────────────────────
@router.get("/store-info")
async def get_store_info(
    current_user: User = Depends(get_current_user),
):
    """Get LemonSqueezy store info and products (admin debug)."""
    if not settings.LEMONSQUEEZY_API_KEY:
        return {"status": "not_configured", "message": "LEMONSQUEEZY_API_KEY not set"}

    async with httpx.AsyncClient(timeout=15) as client:
        # Get stores
        stores_resp = await client.get(
            f"{LEMONSQUEEZY_API}/stores", headers=_ls_headers()
        )
        stores = stores_resp.json() if stores_resp.status_code == 200 else {}

        # Get products
        products_resp = await client.get(
            f"{LEMONSQUEEZY_API}/products", headers=_ls_headers()
        )
        products = products_resp.json() if products_resp.status_code == 200 else {}

        # Get variants
        variants_resp = await client.get(
            f"{LEMONSQUEEZY_API}/variants", headers=_ls_headers()
        )
        variants = variants_resp.json() if variants_resp.status_code == 200 else {}

    return {
        "stores": stores,
        "products": products,
        "variants": variants,
    }


# ── Customer Portal ────────────────────────────────────
@router.post("/portal")
async def get_customer_portal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get customer portal URL for managing subscription."""
    if not current_user.subscription_id:
        raise HTTPException(400, "Aktif abonelik bulunamadı")

    if not settings.LEMONSQUEEZY_API_KEY:
        raise HTTPException(503, "Ödeme sistemi henüz yapılandırılmamış")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{LEMONSQUEEZY_API}/subscriptions/{current_user.subscription_id}",
            headers=_ls_headers(),
        )

    if resp.status_code != 200:
        raise HTTPException(502, "Abonelik bilgisi alınamadı")

    data = resp.json()
    urls = data["data"]["attributes"].get("urls", {})

    return {
        "portal_url": urls.get("customer_portal"),
        "update_payment_url": urls.get("update_payment_method"),
    }


# ── Webhook ────────────────────────────────────────────
@router.post("/webhook")
async def billing_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle LemonSqueezy webhook events."""
    raw_body = await request.body()

    # Verify webhook signature if secret is configured
    if settings.LEMONSQUEEZY_WEBHOOK_SECRET:
        signature = request.headers.get("x-signature", "")
        expected = hmac.new(
            settings.LEMONSQUEEZY_WEBHOOK_SECRET.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            logger.warning("Invalid webhook signature")
            raise HTTPException(403, "Invalid signature")

    body = await request.json()
    event_type = body.get("meta", {}).get("event_name", "")

    logger.info(f"Billing webhook received: {event_type}")

    if event_type == "subscription_created":
        _handle_subscription_created(db, body)
    elif event_type == "subscription_updated":
        _handle_subscription_updated(db, body)
    elif event_type == "subscription_cancelled":
        _handle_subscription_cancelled(db, body)
    elif event_type == "subscription_expired":
        _handle_subscription_expired(db, body)
    elif event_type == "order_created":
        _handle_order_created(db, body)

    return {"status": "ok"}


# ── Webhook Handlers ───────────────────────────────────
def _handle_subscription_created(db: Session, data: dict):
    """Handle new subscription."""
    attrs = data.get("data", {}).get("attributes", {})
    user_email = attrs.get("user_email")
    variant = attrs.get("variant_name", "pro").lower()
    sub_id = str(data.get("data", {}).get("id", ""))

    # Also check custom user_id from checkout
    custom = data.get("meta", {}).get("custom_data", {})
    user_id = custom.get("user_id")

    user = None
    if user_id:
        user = db.query(User).filter(User.id == int(user_id)).first()
    if not user and user_email:
        user = db.query(User).filter(User.email == user_email).first()

    if user:
        user.plan = "enterprise" if "enterprise" in variant else "pro"
        user.subscription_id = sub_id
        db.commit()
        logger.info(f"Subscription created for {user.email}: {user.plan}")
    else:
        logger.warning(f"Webhook: user not found for email={user_email}, id={user_id}")


def _handle_subscription_updated(db: Session, data: dict):
    """Handle subscription update (plan change)."""
    _handle_subscription_created(db, data)


def _handle_subscription_cancelled(db: Session, data: dict):
    """Handle subscription cancellation — downgrade at period end."""
    attrs = data.get("data", {}).get("attributes", {})
    user_email = attrs.get("user_email")

    user = db.query(User).filter(User.email == user_email).first()
    if user:
        logger.info(
            f"Subscription cancelled for {user_email}, will downgrade at period end"
        )


def _handle_subscription_expired(db: Session, data: dict):
    """Handle subscription expiration — downgrade to trial."""
    attrs = data.get("data", {}).get("attributes", {})
    user_email = attrs.get("user_email")

    user = db.query(User).filter(User.email == user_email).first()
    if user:
        user.plan = "trial"
        user.subscription_id = None
        db.commit()
        logger.info(f"Subscription expired for {user_email}, downgraded to trial")


def _handle_order_created(db: Session, data: dict):
    """Handle one-time order (if needed)."""
    logger.info(f"Order created: {data.get('data', {}).get('id')}")


# ── Helpers ────────────────────────────────────────────
async def _find_variant_for_plan(plan: str) -> Optional[str]:
    """Find the LemonSqueezy variant ID for a given plan name."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{LEMONSQUEEZY_API}/variants",
                headers=_ls_headers(),
            )
        if resp.status_code != 200:
            return None

        data = resp.json()
        for variant in data.get("data", []):
            name = variant["attributes"]["name"].lower()
            if plan.lower() in name:
                return variant["id"]
    except Exception as e:
        logger.error(f"Error finding variant: {e}")

    return None
