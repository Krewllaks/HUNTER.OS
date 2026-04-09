"""
HUNTER.OS - In-memory SSE event bus for real-time hunt progress.

Lightweight pub/sub: no external deps, no Redis needed.
Each subscriber gets an asyncio.Queue; publishers push to all queues.
Slow consumers are dropped (QueueFull) to protect memory.
"""
import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class EventBus:
    """Simple in-process pub/sub for SSE streaming. One bus per process."""

    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def publish(self, channel: str, event_type: str, data: dict) -> None:
        """Publish an event to every subscriber on *channel*.

        Non-blocking: if a subscriber queue is full the message is silently
        dropped (back-pressure on slow clients).
        """
        message = {
            "event": event_type,
            "data": {
                **data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        queues = self._subscribers.get(channel, [])
        for queue in queues:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.debug("Dropped event for slow subscriber on %s", channel)

    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted strings for every event on *channel*.

        Sends a heartbeat comment every 30 s so proxies / browsers
        do not close the connection.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers[channel].append(queue)
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
                except asyncio.TimeoutError:
                    # SSE keep-alive heartbeat (comment line ignored by EventSource)
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        except GeneratorExit:
            pass
        finally:
            self._subscribers[channel].remove(queue)
            if not self._subscribers[channel]:
                del self._subscribers[channel]

    @property
    def active_channels(self) -> list[str]:
        """Return channels that have at least one subscriber (diagnostics)."""
        return [ch for ch, subs in self._subscribers.items() if subs]


# ── Singleton ────────────────────────────────────────────
event_bus = EventBus()
