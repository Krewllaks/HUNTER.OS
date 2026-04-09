"""HUNTER.OS - FastAPI Middleware for request tracking."""
import uuid
import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging_config import request_id_var

logger = logging.getLogger("hunter.http")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns a unique request ID to every request and logs request/response.

    - Accepts client-provided X-Request-ID or generates a short UUID.
    - Sets the request_id context variable so all downstream logs include it.
    - Echoes the request ID back in the response header.
    - Logs method, path, status code, and duration for every request.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Use client-provided ID or generate a short one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request_id_var.set(request_id)

        start = time.monotonic()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.monotonic() - start) * 1000
            logger.error(
                "%s %s 500 %.0fms",
                request.method,
                request.url.path,
                duration_ms,
                exc_info=True,
            )
            raise

        duration_ms = (time.monotonic() - start) * 1000
        response.headers["X-Request-ID"] = request_id

        # Skip health checks to reduce noise
        if request.url.path != "/health":
            level = logging.WARNING if response.status_code >= 400 else logging.INFO
            logger.log(
                level,
                "%s %s %s %.0fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

        return response
