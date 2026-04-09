"""
HUNTER.OS - Product Model
Represents the user's product/service that the AI will analyze and find customers for.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # ── User Input ────────────────────────────────────────
    name = Column(String(255), nullable=False)
    description_prompt = Column(Text, nullable=False)  # User's raw product description

    # ── AI Analysis Results ───────────────────────────────
    ai_analysis = Column(JSON)  # {value_proposition, target_market, pain_points_solved, differentiators}
    icp_profile = Column(JSON)  # {industries, titles, company_sizes, pain_points, keywords}
    search_queries = Column(JSON)  # AI-generated queries for finding customers
    target_industries = Column(JSON)  # ["SaaS", "E-commerce", ...]
    target_titles = Column(JSON)  # ["CEO", "CTO", "VP Marketing", ...]
    target_company_sizes = Column(JSON)  # ["1-10", "11-50", ...]

    # ── ICP Analysis Cache ───────────────────────────────
    analysis_cache = Column(JSON)  # Full Gemini result + _cache_key for dedup

    # ── Status ────────────────────────────────────────────
    status = Column(String(50), default="draft")  # draft | analyzing | ready | hunting | active

    # ── Hunt Progress Tracking ─────────────────────────────
    hunt_progress = Column(JSON, default=dict)
    # {
    #   "phase": "searching|analyzing|scoring|saving|complete|error",
    #   "percent": 0-100,
    #   "detail": "Searching Google for marketing agencies...",
    #   "queries_total": 5,
    #   "queries_done": 2,
    #   "results_found": 14,
    #   "leads_created": 3,
    #   "leads_reused": 1,
    #   "started_at": "2026-03-20T01:00:00Z",
    #   "finished_at": null,
    #   "error": null
    # }

    # ── Timestamps ────────────────────────────────────────
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
