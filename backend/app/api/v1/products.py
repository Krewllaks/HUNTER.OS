"""
HUNTER.OS - Product API Endpoints
Product onboarding: describe your product → AI analyzes → start hunting.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductListResponse, ICPRefineRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(
    req: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new product to hunt customers for."""
    product = Product(
        user_id=current_user.id,
        name=req.name,
        description_prompt=req.description_prompt,
        status="draft",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=ProductListResponse)
def list_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all products for the current user."""
    products = (
        db.query(Product)
        .filter(Product.user_id == current_user.id)
        .order_by(Product.created_at.desc())
        .all()
    )
    return ProductListResponse(products=products, total=len(products))


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific product with its AI analysis."""
    product = db.query(Product).filter(
        Product.id == product_id, Product.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    req: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update product details or refine ICP."""
    product = db.query(Product).filter(
        Product.id == product_id, Product.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


@router.post("/{product_id}/analyze", response_model=ProductResponse)
async def analyze_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run AI analysis on the product to generate ICP and search strategies."""
    product = db.query(Product).filter(
        Product.id == product_id, Product.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.status = "analyzing"
    db.commit()

    from app.agents.product_agent import ProductAnalysisAgent
    agent = ProductAnalysisAgent()
    result = await agent.analyze_with_cache(product.name, product.description_prompt, db_product=product)

    if "error" in result and "_fallback" not in result:
        product.status = "draft"
        db.commit()
        raise HTTPException(status_code=500, detail=result["error"])

    # Save AI analysis results
    product.ai_analysis = result.get("value_proposition")
    product.icp_profile = result.get("icp_profile")
    product.search_queries = result.get("search_strategies")
    product.target_industries = result.get("icp_profile", {}).get("industries")
    product.target_titles = result.get("icp_profile", {}).get("target_titles")
    product.target_company_sizes = result.get("icp_profile", {}).get("company_sizes")
    product.status = "ready"

    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}/questions")
async def get_refinement_questions(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate clarifying questions based on initial AI analysis."""
    product = db.query(Product).filter(
        Product.id == product_id, Product.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.ai_analysis:
        raise HTTPException(status_code=400, detail="Product must be analyzed first.")

    from app.agents.product_agent import ProductAnalysisAgent
    agent = ProductAnalysisAgent()

    # Reconstruct full analysis from stored fields
    initial_analysis = {
        "value_proposition": product.ai_analysis,
        "icp_profile": product.icp_profile or {},
        "search_strategies": product.search_queries or {},
    }

    questions = await agent.generate_questions(
        product.name, product.description_prompt, initial_analysis
    )

    return {"product_id": product_id, "questions": questions}


@router.post("/{product_id}/refine-icp", response_model=ProductResponse)
async def refine_icp(
    product_id: int,
    req: ICPRefineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Refine ICP using user's answers to clarifying questions."""
    product = db.query(Product).filter(
        Product.id == product_id, Product.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.ai_analysis:
        raise HTTPException(status_code=400, detail="Product must be analyzed first.")

    from app.agents.product_agent import ProductAnalysisAgent
    agent = ProductAnalysisAgent()

    initial_analysis = {
        "value_proposition": product.ai_analysis,
        "icp_profile": product.icp_profile or {},
        "search_strategies": product.search_queries or {},
    }

    refined = await agent.refine_with_answers(
        product.name, product.description_prompt, initial_analysis, req.answers
    )

    # Save refined analysis
    product.ai_analysis = refined.get("value_proposition", product.ai_analysis)
    product.icp_profile = refined.get("icp_profile", product.icp_profile)
    product.search_queries = refined.get("search_strategies", product.search_queries)
    product.target_industries = refined.get("icp_profile", {}).get("industries")
    product.target_titles = refined.get("icp_profile", {}).get("target_titles")
    product.target_company_sizes = refined.get("icp_profile", {}).get("company_sizes")

    # Clear old cache since ICP changed
    product.analysis_cache = None
    product.status = "ready"

    db.commit()
    db.refresh(product)
    return product


def _run_hunting_background(product_id: int, user_id: int):
    """Background task: run the discovery pipeline."""
    from app.core.database import SessionLocal
    from app.services.discovery_service import DiscoveryService

    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return

        service = DiscoveryService(db)
        service.discover_customers(product, user_id)
    except Exception as e:
        logger.error(f"Hunting background task failed: {e}")
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            product.status = "ready"
            db.commit()
    finally:
        db.close()


@router.post("/{product_id}/start-hunting")
def start_hunting(
    product_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start autonomous customer discovery for this product."""
    product = db.query(Product).filter(
        Product.id == product_id, Product.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.icp_profile:
        raise HTTPException(status_code=400, detail="Product must be analyzed first. Call /analyze endpoint.")

    product.status = "hunting"
    db.commit()

    background_tasks.add_task(_run_hunting_background, product_id, current_user.id)

    return {
        "message": "Hunting started",
        "product_id": product_id,
        "status": "hunting",
        "icp_profile": product.icp_profile,
    }


@router.get("/{product_id}/hunt-progress")
def get_hunt_progress(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get real-time hunt progress for a product."""
    product = db.query(Product).filter(
        Product.id == product_id, Product.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    progress = product.hunt_progress or {}
    return {
        "product_id": product_id,
        "status": product.status,
        "progress": progress,
    }


@router.post("/{product_id}/match-existing-leads")
def match_existing_leads(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Find existing leads in the pool that fit this product's ICP."""
    product = db.query(Product).filter(
        Product.id == product_id, Product.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.icp_profile:
        raise HTTPException(status_code=400, detail="Product must be analyzed first.")

    from app.services.discovery_service import DiscoveryService
    service = DiscoveryService(db)
    matched = service.match_existing_leads(product, current_user.id)

    return {
        "product_id": product_id,
        "matched_leads": len(matched),
        "leads": matched,
    }
