"""
HUNTER.OS - Lead-Product Junction Model
Many-to-many: same lead can be targeted for multiple products.
Enables cross-product lead reuse without re-scraping.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class LeadProduct(Base):
    """Junction table linking leads to products with per-product status tracking."""
    __tablename__ = "lead_products"
    __table_args__ = (
        UniqueConstraint("lead_id", "product_id", name="uq_lead_product"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    # Per-product status for this lead
    status = Column(String(50), default="new")  # new | contacted | rejected | won | not_fit
    fit_score = Column(Float, default=0.0)       # AI-calculated product-lead fit (0-100)
    outreach_count = Column(Integer, default=0)
    last_contacted_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(255), nullable=True)

    # Outreach history per product
    outreach_history = Column(JSON, default=list)  # [{date, channel, message_id, outcome}]

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    lead = relationship("Lead", backref="lead_products")
    product = relationship("Product", backref="lead_products")
