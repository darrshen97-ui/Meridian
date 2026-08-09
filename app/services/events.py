"""In-process event bus feeding Server-Sent Events, one stream per user."""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, user_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers[user_id].add(queue)
        return queue

    def unsubscribe(self, user_id: int, queue: asyncio.Queue) -> None:
        self._subscribers[user_id].discard(queue)

    def publish(self, user_id: int, event_type: str, data: dict) -> None:
        for queue in list(self._subscribers[user_id]):
            try:
                queue.put_nowait((event_type, data))
            except asyncio.QueueFull:  # slow consumer: drop rather than block sync
                pass


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def sse_format(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
