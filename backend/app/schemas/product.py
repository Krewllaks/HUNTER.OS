"""
HUNTER.OS - Product Schemas
"""
from typing import Optional
from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    description_prompt: str


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description_prompt: Optional[str] = None
    icp_profile: Optional[dict] = None
    target_industries: Optional[list] = None
    target_titles: Optional[list] = None
    target_company_sizes: Optional[list] = None


class ProductResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description_prompt: str
    ai_analysis: Optional[dict] = None
    icp_profile: Optional[dict] = None
    search_queries: Optional[dict] = None
    target_industries: Optional[list] = None
    target_titles: Optional[list] = None
    target_company_sizes: Optional[list] = None
    status: str

    model_config = {"from_attributes": True}


class ICPRefineRequest(BaseModel):
    """User answers to ICP clarifying questions."""
    answers: dict  # question_id → answer (str or list[str])


class ProductListResponse(BaseModel):
    products: list[ProductResponse]
    total: int
