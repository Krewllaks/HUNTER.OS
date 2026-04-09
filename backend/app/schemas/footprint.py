"""
HUNTER.OS - Digital Footprint Scanner Schemas
Sherlock-style social profile discovery for lead enrichment.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SocialProfile(BaseModel):
    """A discovered social media profile."""
    platform: str
    url: str
    username: str
    verified: bool = True
    category: str = "unknown"
    sales_relevance: float = 0.5


class FootprintScanRequest(BaseModel):
    """Request to scan a lead's digital footprint."""
    custom_usernames: list[str] = []  # Additional usernames to check
    sites: list[str] = []  # Limit to specific sites (empty = all)


class FootprintBulkScanRequest(BaseModel):
    """Bulk scan request for multiple leads."""
    lead_ids: list[int]
    custom_usernames: list[str] = []


class FootprintScanResponse(BaseModel):
    """Result of a footprint scan."""
    lead_id: int
    profiles_found: int
    profiles: list[SocialProfile]
    footprint_score: float  # 0-100
    usernames_checked: list[str]
    scanned_at: datetime
    scan_duration_seconds: float


class DigitalDossier(BaseModel):
    """Full digital dossier for a lead."""
    lead_id: int
    lead_name: str
    lead_company: Optional[str]

    # Social profiles
    profiles: list[SocialProfile]
    footprint_score: float
    total_platforms: int
    active_categories: list[str]

    # Insights
    primary_platform: Optional[str]  # Most relevant platform
    content_creator: bool  # Active content producer?
    tech_oriented: bool  # Developer/tech focused?

    scanned_at: Optional[datetime]
