"""
HUNTER.OS - Hunt API Endpoints
Start AI-powered lead research & enrichment + real-time SSE progress stream.
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, decode_token
from app.models.user import User
from app.schemas.lead import HuntRequest, HuntResponse
from app.services.hunt_service import HuntService
from app.services.event_bus import event_bus

router = APIRouter(prefix="/hunt", tags=["Hunt"])


# ── Auth helper: accept Bearer header OR ?token= query param ──
def _get_user_flexible(
    request: Request,
    token: str = Query(None, description="JWT token (for EventSource which cannot send headers)"),
    db: Session = Depends(get_db),
) -> User:
    """Resolve current user from either Authorization header or query param.

    EventSource (browser SSE API) cannot set custom headers, so the frontend
    passes the JWT as a query parameter instead.
    """
    from app.models.user import User as UserModel

    # 1. Try standard Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header.split(" ", 1)[1]
    elif token:
        raw_token = token
    else:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    payload = decode_token(raw_token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(UserModel).filter(UserModel.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/start", response_model=HuntResponse)
async def start_hunt(
    req: HuntRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start the AI-powered hunt process.

    The hunt runs in the background and:
    1. Researches each target using the ReAct agent
    2. Scores leads using Chain-of-Thought analysis
    3. Generates personalized messages
    4. Enqueues leads into campaign workflows

    Returns a hunt_id for status tracking.
    """
    hunt_service = HuntService(db)

    # Estimate number of leads
    estimated = len(req.target_domains) + len(req.target_linkedin_urls)
    if req.lookalike_company:
        estimated += req.max_leads

    # Run hunt in background
    import uuid
    hunt_id = str(uuid.uuid4())[:8]

    background_tasks.add_task(
        hunt_service.start_hunt,
        user_id=current_user.id,
        target_domains=req.target_domains,
        target_linkedin_urls=req.target_linkedin_urls,
        icp_description=req.icp_description,
        lookalike_company=req.lookalike_company,
        campaign_id=req.campaign_id,
        signals_to_track=req.signals_to_track,
        auto_personalize=req.auto_personalize,
        auto_score=req.auto_score,
        max_leads=req.max_leads,
    )

    return HuntResponse(
        hunt_id=hunt_id,
        status="started",
        message=f"Hunt initiated. Researching {estimated} targets.",
        estimated_leads=estimated,
    )


@router.get("/stream/{product_id}")
async def stream_hunt_progress(
    product_id: int,
    current_user: User = Depends(_get_user_flexible),
):
    """SSE endpoint for real-time hunt / discovery progress.

    Connect via EventSource:
        const src = new EventSource(`/api/v1/hunt/stream/{product_id}?token=<jwt>`);

    Events emitted:
        - discovery_started   {product_id, product_name, query_count}
        - discovery_progress  {found, total_queries, current_query, queries_done}
        - lead_found          {name, company, score, linkedin_url}
        - lead_reused         {lead_id, company}
        - discovery_complete  {total_leads_new, total_leads_reused, duration_seconds}
        - discovery_error     {error}
    """
    channel = f"hunt:{current_user.id}:{product_id}"

    async def generate():
        async for chunk in event_bus.subscribe(channel):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
