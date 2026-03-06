from __future__ import annotations

from backend.interfaces.websockets.websocket import WebSocketHandler
from backend.utils.print_style import PrintStyle


class HelloHandler(WebSocketHandler):
    """Sample handler used for foundational testing."""

    @classmethod
    def get_event_types(cls) -> list[str]:
        return ["hello_request"]

    async def process_event(self, event_type: str, data: dict, sid: str):
        name = data.get("name") or "stranger"
        PrintStyle.info(f"hello_request from {sid} ({name})")
        return {"message": f"Hello, {name}!", "handler": self.identifier}
