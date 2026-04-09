"""HUNTER.OS - Structured JSON Logging with Request ID propagation."""
import logging
import json
import sys
from datetime import datetime, timezone
from contextvars import ContextVar

# Context variable for request ID propagation across async boundaries
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get("-"),
        }

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if record.exc_info and record.exc_info[1]:
            log_data["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_data, ensure_ascii=False)


class DevFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        rid = request_id_var.get("-")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{ts} | {rid[:8]:8s} | {record.name:30s} | {record.levelname:7s} | {record.getMessage()}"


def setup_logging(debug: bool = False) -> None:
    """Configure logging based on environment.

    Args:
        debug: When True, use human-readable format + DEBUG level.
               When False, use JSON format + INFO level (production).
    """
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if debug:
        handler.setFormatter(DevFormatter())
        root.setLevel(logging.DEBUG)
    else:
        handler.setFormatter(JSONFormatter())
        root.setLevel(logging.INFO)

    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.WARNING if not debug else logging.INFO
    )
