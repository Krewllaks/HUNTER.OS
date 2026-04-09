"""
HUNTER.OS - Lead Enrichment Pipeline
Orchestrates: Footprint Scan -> Content Analysis -> Scoring Boost

Automatically enriches leads after discovery with:
1. Digital footprint scanning (Sherlock-style)
2. Content analysis from discovered platforms
3. Social proof scoring boost
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cache import cache_get, cache_set, cache_key
from app.models.lead import Lead
from app.services.footprint_scanner import DigitalFootprintScanner
from app.services.lead_enrichment_api import LeadEnrichmentAPI

logger = logging.getLogger(__name__)


class EnrichmentPipeline:
    """Orchestrates multi-stage lead enrichment after discovery."""

    def __init__(self, db: Session):
        self.db = db
        self.scanner = DigitalFootprintScanner()
        self.enrichment_api = LeadEnrichmentAPI()

    async def enrich_lead(self, lead_id: int) -> dict:
        """Run the full enrichment pipeline for a single lead.

        Phase 11: gated by ``INTENT_SCORE_THRESHOLD_ENRICHMENT``.
        Low-signal leads are skipped *before* a single API call is
        made — this is the single biggest cost-saver in the platform.

        Steps:
        1. Run footprint scan (discover social profiles)
        2. Calculate social proof score
        3. Boost lead scoring based on digital presence
        4. Update lead record
        """
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            logger.error("Lead %d not found for enrichment", lead_id)
            return {"status": "error", "reason": "lead_not_found"}

        # ════════════════════════════════════════════════
        # ADDED (Phase 11): CONDITIONAL ENRICHMENT GATE
        # Only enrich high-intent leads → biggest budget saver.
        # ════════════════════════════════════════════════
        threshold = settings.INTENT_SCORE_THRESHOLD_ENRICHMENT
        lead_score = getattr(lead, "intent_score", None) or 0
        if lead_score < threshold:
            logger.info(
                f"⛔ SKIPPING ENRICHMENT for lead {lead_id}: "
                f"intent_score={lead_score} < threshold={threshold}"
            )
            return {
                "status": "skipped",
                "skipped": True,
                "reason": "below_enrichment_threshold",
                "lead_id": lead_id,
                "intent_score": lead_score,
                "threshold": threshold,
            }
        # ════════════════════════════════════════════════

        result = {"lead_id": lead_id, "steps": []}

        # Step 1: Footprint Scan
        try:
            scan_result = await self.scanner.scan_lead(lead)
            lead.social_profiles = scan_result["profiles"]
            lead.digital_footprint_score = scan_result["footprint_score"]
            lead.footprint_scanned_at = datetime.now(timezone.utc)

            result["steps"].append({
                "step": "footprint_scan",
                "status": "success",
                "profiles_found": len(scan_result["profiles"]),
                "score": scan_result["footprint_score"],
            })
        except Exception as exc:
            logger.warning("Footprint scan failed for lead %d: %s", lead_id, exc)
            result["steps"].append({
                "step": "footprint_scan",
                "status": "failed",
                "error": str(exc),
            })

        # Step 2: External API Enrichment (Hunter.io, FullContact, BuiltWith)
        try:
            domain = None
            if lead.email and "@" in lead.email:
                domain = lead.email.split("@")[1]
            elif lead.company_domain:
                domain = lead.company_domain

            api_result = await self.enrichment_api.full_enrich(
                domain=domain,
                email=lead.email,
                first_name=lead.first_name,
                last_name=lead.last_name,
            )

            # Update lead with API data
            updated_fields = []
            if api_result.get("email_found") and not lead.email:
                lead.email = api_result["email_found"]
                updated_fields.append("email")

            person = api_result.get("person", {})
            if person.get("title") and not lead.title:
                lead.title = person["title"]
                updated_fields.append("title")
            if person.get("company") and not lead.company_name:
                lead.company_name = person["company"]
                updated_fields.append("company_name")

            # Merge API social profiles with footprint scan results
            if person.get("social_profiles"):
                existing_platforms = {p.get("platform", "").lower() for p in (lead.social_profiles or [])}
                for sp in person["social_profiles"]:
                    if sp.get("platform", "").lower() not in existing_platforms:
                        profiles = lead.social_profiles or []
                        profiles.append({
                            "platform": sp["platform"],
                            "url": sp.get("url", ""),
                            "username": sp.get("username", ""),
                            "verified": True,
                            "category": "professional",
                            "sales_relevance": 0.7,
                        })
                        lead.social_profiles = profiles
                        updated_fields.append(f"social:{sp['platform']}")

            company = api_result.get("company", {})
            if company.get("technologies"):
                tech_data = lead.technographics or {}
                tech_data["builtwith"] = company["technologies"][:20]
                tech_data["category_summary"] = company.get("category_summary", {})
                lead.technographics = tech_data
                updated_fields.append("technographics")

            result["steps"].append({
                "step": "api_enrichment",
                "status": "success",
                "providers_used": api_result.get("providers_used", []),
                "fields_updated": updated_fields,
            })
        except Exception as exc:
            logger.warning("API enrichment failed for lead %d: %s", lead_id, exc)
            result["steps"].append({
                "step": "api_enrichment",
                "status": "failed",
                "error": str(exc),
            })

        # Step 3: Social Proof Scoring Boost
        try:
            boost = self._calculate_social_proof_boost(lead)
            original_score = lead.intent_score or 0.0

            # Apply boost (capped at 100)
            lead.intent_score = min(100.0, original_score + boost)

            result["steps"].append({
                "step": "social_proof_boost",
                "status": "success",
                "original_score": original_score,
                "boost": boost,
                "new_score": lead.intent_score,
            })
        except Exception as exc:
            logger.warning("Social proof scoring failed for lead %d: %s", lead_id, exc)
            result["steps"].append({
                "step": "social_proof_boost",
                "status": "failed",
                "error": str(exc),
            })

        # Step 4: Content Analysis Enhancement (if ContentAnalystAgent available)
        try:
            content_boost = await self._run_content_analysis(lead)
            if content_boost:
                result["steps"].append({
                    "step": "content_analysis",
                    "status": "success",
                    "insights": content_boost,
                })
        except Exception as exc:
            logger.debug("Content analysis skipped for lead %d: %s", lead_id, exc)

        # Save all changes
        self.db.commit()

        result["status"] = "success"
        result["final_score"] = lead.intent_score
        result["footprint_score"] = lead.digital_footprint_score

        logger.info(
            "Enrichment complete for lead %d: %d profiles, footprint=%.1f, intent=%.1f",
            lead_id,
            len(lead.social_profiles or []),
            lead.digital_footprint_score or 0,
            lead.intent_score or 0,
        )

        return result

    async def enrich_leads_batch(self, lead_ids: list[int]) -> list[dict]:
        """Enrich multiple leads sequentially."""
        results = []
        for lead_id in lead_ids:
            result = await self.enrich_lead(lead_id)
            results.append(result)
        return results

    def _calculate_social_proof_boost(self, lead: Lead) -> float:
        """Calculate intent score boost based on digital presence.

        Scoring:
        - Verified LinkedIn: +5
        - Twitter/X active: +3
        - GitHub (tech sales): +3
        - Blog/Medium: +3
        - 5+ platforms: +5 bonus
        - Content creator: +3
        - Tech-oriented with dev platforms: +3
        """
        profiles = lead.social_profiles or []
        if not profiles:
            return 0.0

        boost = 0.0
        platforms = {p.get("platform", "").lower() for p in profiles}

        # Individual platform bonuses
        if "linkedin" in platforms:
            boost += 5.0
        if "twitter" in platforms:
            boost += 3.0
        if "github" in platforms:
            boost += 3.0
        if "medium" in platforms or "substack" in platforms:
            boost += 3.0
        if "producthunt" in platforms or "indiehackers" in platforms:
            boost += 3.0
        if "crunchbase" in platforms:
            boost += 3.0

        # Breadth bonus
        if len(profiles) >= 5:
            boost += 5.0
        elif len(profiles) >= 3:
            boost += 2.0

        # Category diversity
        categories = {p.get("category", "unknown") for p in profiles}
        content_cats = {"content", "creator", "streaming"}
        if categories & content_cats:
            boost += 3.0

        return min(boost, 25.0)  # Cap individual boost at 25 points

    async def _run_content_analysis(self, lead: Lead) -> dict | None:
        """Run ContentAnalystAgent with enriched social data (if available).

        Returns additional insights or None if agent unavailable.
        """
        profiles = lead.social_profiles or []
        if not profiles:
            return None

        # Build platform summary for content analysis
        platform_summary = []
        for p in profiles:
            platform_summary.append(f"{p.get('platform')}: {p.get('url')}")

        # Check if ContentAnalystAgent is available
        try:
            from app.agents.content_analyst_agent import ContentAnalystAgent
            agent = ContentAnalystAgent()

            lead_name = " ".join(filter(None, [lead.first_name, lead.last_name]))

            # Enhanced analysis prompt with social profile data
            enriched_context = {
                "name": lead_name,
                "company": lead.company_name,
                "title": lead.title,
                "social_profiles": platform_summary,
                "platform_count": len(profiles),
                "existing_posts": lead.last_4_posts or [],
            }

            # Only run if we have meaningful data
            if len(profiles) >= 2:
                analysis = await agent.analyze(
                    lead_name=lead_name,
                    company=lead.company_name or "",
                    posts=lead.last_4_posts or [],
                    social_profiles=platform_summary,
                )
                return analysis
        except (ImportError, Exception) as exc:
            logger.debug("ContentAnalystAgent not available: %s", exc)

        return None
