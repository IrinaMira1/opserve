import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List


class EventBus:
    """Central event bus — agents emit here, SSE clients subscribe."""

    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []
        self._history: List[Dict] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subscribers.remove(q)

    async def emit(self, event_type: str, agent: str, data: Dict[str, Any]):
        event = {
            "id": f"{int(datetime.utcnow().timestamp() * 1000)}",
            "event": event_type,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        self._history.append(event)
        # keep last 500 events
        if len(self._history) > 500:
            self._history.pop(0)
        for q in list(self._subscribers):
            await q.put(event)

    def get_history(self) -> List[Dict]:
        return list(self._history)

    def format_sse(self, event: Dict) -> str:
        return (
            f"id: {event['id']}\n"
            f"event: {event['event']}\n"
            f"data: {json.dumps(event)}\n\n"
        )


# Singleton shared across the app
bus = EventBus()
