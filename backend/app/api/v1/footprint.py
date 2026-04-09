"""
HUNTER.OS - Digital Footprint API Endpoints
Sherlock-style social profile discovery for lead enrichment.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.lead import Lead
from app.schemas.footprint import (
    FootprintScanRequest,
    FootprintBulkScanRequest,
    FootprintScanResponse,
    SocialProfile,
    DigitalDossier,
)
from app.services.footprint_scanner import DigitalFootprintScanner
from app.services.enrichment_pipeline import EnrichmentPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/footprint", tags=["Footprint"])


async def _run_footprint_scan(lead_id: int, user_id: int, custom_usernames: list[str], site_filter: list[str]):
    """Background task to run the footprint scan and update lead."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == user_id).first()
        if not lead:
            logger.error("Lead %d not found for footprint scan", lead_id)
            return

        scanner = DigitalFootprintScanner()
        result = await scanner.scan_lead(lead, custom_usernames=custom_usernames or None)

        # Update lead with scan results
        lead.social_profiles = result["profiles"]
        lead.digital_footprint_score = result["footprint_score"]
        lead.footprint_scanned_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Footprint scan saved for lead %d: %d profiles, score=%.1f",
            lead_id, len(result["profiles"]), result["footprint_score"],
        )
    except Exception as exc:
        logger.error("Footprint scan failed for lead %d: %s", lead_id, exc)
        db.rollback()
    finally:
        db.close()


@router.post("/scan/{lead_id}", response_model=FootprintScanResponse)
async def scan_lead_footprint(
    lead_id: int,
    req: FootprintScanRequest = FootprintScanRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a digital footprint scan for a lead.

    Extracts candidate usernames from the lead's email, LinkedIn URL, and name,
    then checks 50+ platforms for matching profiles.

    The scan runs in the background. Results are saved to the lead's
    social_profiles field and can be retrieved via GET /footprint/{lead_id}.
    """
    # Check plan limits
    from app.services.plan_limiter import PlanLimiter
    limiter = PlanLimiter(db)
    limiter.check_footprint_scan(current_user)

    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.user_id == current_user.id,
        Lead.is_deleted == False,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Quick synchronous scan for immediate response
    scanner = DigitalFootprintScanner()
    result = await scanner.scan_lead(lead, custom_usernames=req.custom_usernames or None)

    # Save results
    lead.social_profiles = result["profiles"]
    lead.digital_footprint_score = result["footprint_score"]
    lead.footprint_scanned_at = datetime.now(timezone.utc)
    db.commit()

    return FootprintScanResponse(
        lead_id=lead_id,
        profiles_found=len(result["profiles"]),
        profiles=[SocialProfile(**p) for p in result["profiles"]],
        footprint_score=result["footprint_score"],
        usernames_checked=result["usernames_checked"],
        scanned_at=lead.footprint_scanned_at,
        scan_duration_seconds=result["scan_duration"],
    )


@router.post("/bulk-scan")
async def bulk_scan_footprint(
    req: FootprintBulkScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start footprint scans for multiple leads (Enterprise only).

    Scans run in the background. Check individual lead results via GET /footprint/{lead_id}.
    """
    # Enterprise check
    if current_user.plan != "enterprise":
        raise HTTPException(status_code=402, detail="Bulk scan requires Enterprise plan")

    # Validate leads exist
    leads = db.query(Lead).filter(
        Lead.id.in_(req.lead_ids),
        Lead.user_id == current_user.id,
        Lead.is_deleted == False,
    ).all()

    if not leads:
        raise HTTPException(status_code=404, detail="No matching leads found")

    # Queue background scans
    for lead in leads:
        background_tasks.add_task(
            _run_footprint_scan,
            lead.id,
            current_user.id,
            req.custom_usernames,
            [],
        )

    return {
        "message": f"Footprint scans queued for {len(leads)} leads",
        "lead_ids": [l.id for l in leads],
    }


@router.get("/{lead_id}", response_model=FootprintScanResponse)
def get_footprint_results(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get cached footprint scan results for a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.user_id == current_user.id,
        Lead.is_deleted == False,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if not lead.footprint_scanned_at:
        raise HTTPException(status_code=404, detail="No footprint scan results. Run POST /footprint/scan/{lead_id} first.")

    profiles = lead.social_profiles or []

    return FootprintScanResponse(
        lead_id=lead_id,
        profiles_found=len(profiles),
        profiles=[SocialProfile(**p) for p in profiles],
        footprint_score=lead.digital_footprint_score or 0.0,
        usernames_checked=[],  # Not stored after scan
        scanned_at=lead.footprint_scanned_at,
        scan_duration_seconds=0.0,  # Not available for cached results
    )


@router.get("/{lead_id}/dossier", response_model=DigitalDossier)
def get_digital_dossier(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full digital dossier for a lead.

    Combines social profiles with insights about the lead's digital presence.
    """
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.user_id == current_user.id,
        Lead.is_deleted == False,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    profiles = lead.social_profiles or []
    categories = list({p.get("category", "unknown") for p in profiles})

    # Determine primary platform (highest sales_relevance)
    primary = None
    if profiles:
        sorted_profiles = sorted(profiles, key=lambda p: p.get("sales_relevance", 0), reverse=True)
        primary = sorted_profiles[0].get("platform")

    # Determine if tech-oriented or content creator
    tech_categories = {"developer", "data_science", "ai_ml", "security"}
    content_categories = {"content", "creator", "streaming"}
    tech_oriented = bool(set(categories) & tech_categories)
    content_creator = bool(set(categories) & content_categories)

    lead_name = " ".join(filter(None, [lead.first_name, lead.last_name])) or "Unknown"

    return DigitalDossier(
        lead_id=lead_id,
        lead_name=lead_name,
        lead_company=lead.company_name,
        profiles=[SocialProfile(**p) for p in profiles],
        footprint_score=lead.digital_footprint_score or 0.0,
        total_platforms=len(profiles),
        active_categories=categories,
        primary_platform=primary,
        content_creator=content_creator,
        tech_oriented=tech_oriented,
        scanned_at=lead.footprint_scanned_at,
    )


@router.post("/enrich/{lead_id}")
async def enrich_lead(
    lead_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run full enrichment pipeline on a lead.

    Combines: footprint scan + external API enrichment (Hunter.io, FullContact,
    BuiltWith, Snov.io, RocketReach) + social proof scoring + content analysis.
    """
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.user_id == current_user.id,
        Lead.is_deleted == False,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    pipeline = EnrichmentPipeline(db)
    result = await pipeline.enrich_lead(lead_id)

    return result


@router.post("/enrich-batch")
async def enrich_leads_batch(
    lead_ids: list[int],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run enrichment pipeline on multiple leads (background).

    Enterprise only.
    """
    if current_user.plan != "enterprise":
        raise HTTPException(status_code=402, detail="Batch enrichment requires Enterprise plan")

    leads = db.query(Lead).filter(
        Lead.id.in_(lead_ids),
        Lead.user_id == current_user.id,
        Lead.is_deleted == False,
    ).all()

    if not leads:
        raise HTTPException(status_code=404, detail="No matching leads found")

    async def _run_batch():
        from app.core.database import SessionLocal
        batch_db = SessionLocal()
        try:
            pipeline = EnrichmentPipeline(batch_db)
            await pipeline.enrich_leads_batch([l.id for l in leads])
        except Exception as exc:
            logger.error("Batch enrichment failed: %s", exc)
        finally:
            batch_db.close()

    background_tasks.add_task(_run_batch)

    return {
        "message": f"Enrichment queued for {len(leads)} leads",
        "lead_ids": [l.id for l in leads],
    }
