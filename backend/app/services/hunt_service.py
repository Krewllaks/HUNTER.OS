"""
HUNTER.OS - Hunt Orchestration Service
Coordinates the full research -> score -> personalize pipeline.
All agent calls are properly awaited (async).
"""
import uuid
import json
import logging
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.lead import Lead, BuyingCommittee
from app.agents.research_agent import create_research_agent
from app.agents.scoring_agent import ScoringAgent
from app.agents.personalization_agent import PersonalizationAgent

logger = logging.getLogger(__name__)


class HuntService:
    """
    Orchestrates the full AI hunting pipeline:
    1. Research (ReAct Agent) -> gather signals
    2. Score (CoT Agent) -> rank leads
    3. Personalize -> generate messages
    4. Enqueue -> workflow engine
    """

    def __init__(self, db: Session):
        self.db = db
        self.scoring_agent = ScoringAgent()
        self.personalization_agent = PersonalizationAgent()

    async def start_hunt(
        self,
        user_id: int,
        target_domains: list[str] = None,
        target_linkedin_urls: list[str] = None,
        icp_description: Optional[str] = None,
        lookalike_company: Optional[str] = None,
        campaign_id: Optional[int] = None,
        signals_to_track: list[str] = None,
        auto_personalize: bool = True,
        auto_score: bool = True,
        max_leads: int = 100,
        linkedin_cookie: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> dict:
        """Start the hunt process. Returns results dict."""
        hunt_id = str(uuid.uuid4())[:8]
        target_domains = target_domains or []
        target_linkedin_urls = target_linkedin_urls or []
        signals_to_track = signals_to_track or [
            "technographics", "hiring_intent", "news",
            "website_changes", "social_engagement",
        ]

        logger.info(f"Hunt {hunt_id} started: {len(target_domains)} domains, {len(target_linkedin_urls)} LinkedIn URLs")

        results = {
            "hunt_id": hunt_id,
            "leads_researched": 0,
            "leads_scored": 0,
            "leads_personalized": 0,
            "errors": [],
        }

        research_agent = create_research_agent(
            linkedin_cookie=linkedin_cookie,
            proxy=proxy,
        )

        # ── Process domains ──────────────────────────────
        for domain in target_domains:
            try:
                lead_data = await self._research_domain(research_agent, domain, signals_to_track)
                lead = self._save_lead(user_id, lead_data, campaign_id, source="domain_hunt")

                if auto_score:
                    score = await self.scoring_agent.score_lead(lead_data)
                    lead.intent_score = score.get("final_score", 0)
                    lead.confidence = score.get("confidence", 0)
                    lead.icp_match_score = score.get("icp_match_score", 0)
                    results["leads_scored"] += 1

                if auto_personalize and lead.intent_score >= 30:
                    msg = await self.personalization_agent.generate_message(
                        lead_data=lead_data,
                        channel="email",
                    )
                    lead.notes = (lead.notes or "") + f"\n\n[AI MESSAGE DRAFT]\n{msg.get('body', '')}"
                    results["leads_personalized"] += 1

                self.db.commit()
                results["leads_researched"] += 1

            except Exception as e:
                logger.error(f"Hunt error for domain {domain}: {e}")
                results["errors"].append({"domain": domain, "error": str(e)})

        # ── Process LinkedIn URLs ────────────────────────
        for linkedin_url in target_linkedin_urls:
            try:
                lead_data = await self._research_linkedin(research_agent, linkedin_url, signals_to_track)
                lead = self._save_lead(user_id, lead_data, campaign_id, source="linkedin_hunt")

                if auto_score:
                    score = await self.scoring_agent.score_lead(lead_data)
                    lead.intent_score = score.get("final_score", 0)
                    lead.confidence = score.get("confidence", 0)
                    results["leads_scored"] += 1

                self.db.commit()
                results["leads_researched"] += 1

            except Exception as e:
                logger.error(f"Hunt error for LinkedIn {linkedin_url}: {e}")
                results["errors"].append({"url": linkedin_url, "error": str(e)})

        # ── Enrichment Pipeline: scan digital footprint for all discovered leads ──
        try:
            from app.services.enrichment_pipeline import EnrichmentPipeline
            pipeline = EnrichmentPipeline(self.db)

            enriched_leads = self.db.query(Lead).filter(
                Lead.user_id == user_id,
                Lead.footprint_scanned_at.is_(None),
                Lead.status == "researched",
                Lead.is_deleted == False,
            ).order_by(Lead.created_at.desc()).limit(max_leads).all()

            enrichment_count = 0
            for lead in enriched_leads:
                try:
                    await pipeline.enrich_lead(lead.id)
                    enrichment_count += 1
                except Exception as exc:
                    logger.debug("Enrichment skipped for lead %d: %s", lead.id, exc)

            results["leads_enriched"] = enrichment_count
            logger.info("Hunt %s enrichment: %d leads enriched", hunt_id, enrichment_count)
        except Exception as exc:
            logger.warning("Enrichment pipeline failed: %s", exc)
            results["leads_enriched"] = 0

        return results

    async def _research_domain(self, agent, domain: str, signals: list[str]) -> dict:
        """Use ReAct agent to research a company domain."""
        task = f"""Research the company at domain: {domain}

Gather these signals: {', '.join(signals)}

Return a comprehensive intelligence dossier as JSON with these fields:
- company_name, industry, company_size, domain
- tech_stack (list of detected technologies)
- news (list of recent headlines with dates)
- hiring_signals (list of open positions)
- website_changes (list of detected changes)
- email (if discoverable)
- title, first_name, last_name (key contact if found)

If you cannot find a piece of data, set it to null or an empty list."""

        result = await agent.run(task)

        try:
            parsed = json.loads(result) if isinstance(result, str) else result
            # Ensure domain is always present
            if isinstance(parsed, dict):
                parsed.setdefault("domain", domain)
                parsed.setdefault("company_name", domain.split(".")[0].title())
            return parsed
        except json.JSONDecodeError:
            return {
                "domain": domain,
                "raw_research": result,
                "company_name": domain.split(".")[0].title(),
            }

    async def _research_linkedin(self, agent, linkedin_url: str, signals: list[str]) -> dict:
        """Use ReAct agent to research a LinkedIn profile."""
        task = f"""Research the person at LinkedIn URL: {linkedin_url}

Gather these intelligence signals: {', '.join(signals)}

Return a comprehensive dossier as JSON with these fields:
- first_name, last_name, title, company_name, linkedin_url
- communication_style (formal/casual/mixed)
- recent_posts (list of last 4 post summaries)
- engagement (list of recent likes/comments)
- common_ground (list of shared interests)
- hobbies (list)
- tech_stack (company technologies if discoverable)

If you cannot find a piece of data, set it to null or an empty list."""

        result = await agent.run(task)

        try:
            parsed = json.loads(result) if isinstance(result, str) else result
            if isinstance(parsed, dict):
                parsed.setdefault("linkedin_url", linkedin_url)
            return parsed
        except json.JSONDecodeError:
            return {
                "linkedin_url": linkedin_url,
                "raw_research": result,
            }

    def _save_lead(
        self,
        user_id: int,
        lead_data: dict,
        campaign_id: Optional[int],
        source: str,
    ) -> Lead:
        """Save researched lead data to database."""
        # Parse name safely
        raw_name = lead_data.get("name", "")
        first = lead_data.get("first_name") or (raw_name.split(" ")[0] if raw_name else None)
        last = lead_data.get("last_name") or (" ".join(raw_name.split(" ")[1:]) if raw_name else None)

        lead = Lead(
            user_id=user_id,
            first_name=first,
            last_name=last,
            email=lead_data.get("email"),
            linkedin_url=lead_data.get("linkedin_url"),
            company_name=lead_data.get("company_name") or lead_data.get("company"),
            company_domain=lead_data.get("domain") or lead_data.get("company_domain"),
            company_size=lead_data.get("company_size") or lead_data.get("size"),
            industry=lead_data.get("industry"),
            title=lead_data.get("title") or lead_data.get("headline"),
            last_4_posts=lead_data.get("recent_posts", []),
            technographics=lead_data.get("tech_stack", []),
            recent_news=lead_data.get("news", []),
            hiring_signals=lead_data.get("hiring_signals", []),
            website_changes=lead_data.get("website_changes", []),
            social_engagement=lead_data.get("engagement", []),
            content_intent=lead_data.get("content_intent", []),
            communication_style=lead_data.get("communication_style", "formal"),
            hobbies=lead_data.get("hobbies", []),
            common_ground=lead_data.get("common_ground", []),
            media_quotes=lead_data.get("media_quotes", []),
            review_highlights=lead_data.get("review_highlights", []),
            source=source,
            campaign_id=campaign_id,
            status="researched",
        )
        self.db.add(lead)
        self.db.flush()

        # Save buying committee if found
        for member in lead_data.get("buying_committee", []):
            bc = BuyingCommittee(
                lead_id=lead.id,
                name=member.get("name", "Unknown"),
                role=member.get("role"),
                email=member.get("email"),
                linkedin_url=member.get("linkedin_url"),
                personalization_angle=member.get("personalization_angle"),
            )
            self.db.add(bc)

        return lead
