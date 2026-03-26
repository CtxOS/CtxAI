"""Integration tests for WebSocket event flow.

Tests the full cycle: client connect → send event → handler dispatch → response.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ctxai.helpers.websocket import WebSocketHandler
from ctxai.helpers.websocket_manager import WebSocketManager


class FakeSocketIOServer:
    """Minimal Socket.IO server mock for integration tests."""

    def __init__(self):
        self.emitted: list[dict[str, Any]] = []
        self.emit = AsyncMock(side_effect=self._record_emit)
        self.disconnect = AsyncMock()

    async def _record_emit(self, event, data, namespace=None, room=None, **kw):
        self.emitted.append({"event": event, "data": data, "namespace": namespace, "room": room})


class EchoHandler(WebSocketHandler):
    """Handler that echoes back received data."""

    _last_instance: "EchoHandler | None" = None

    def __init__(self, socketio, lock):
        super().__init__(socketio, lock)
        self.processed_events: list[dict[str, Any]] = []
        EchoHandler._last_instance = self

    @classmethod
    def get_event_types(cls) -> list[str]:
        return ["echo", "ping"]

    async def process_event(self, event_type: str, data: dict[str, Any], sid: str) -> dict[str, Any]:
        record = {"event": event_type, "data": data, "sid": sid}
        self.processed_events.append(record)

        if event_type == "ping":
            return {"pong": True, "original": data}
        return {"echo": True, "event": event_type, "data": data}


class FireAndForgetHandler(WebSocketHandler):
    """Handler that returns None (no response)."""

    _last_instance: "FireAndForgetHandler | None" = None

    def __init__(self, socketio, lock):
        super().__init__(socketio, lock)
        self.received: list[str] = []
        FireAndForgetHandler._last_instance = self

    @classmethod
    def get_event_types(cls) -> list[str]:
        return ["notify"]

    async def process_event(self, event_type: str, data: dict[str, Any], sid: str) -> None:
        self.received.append(data.get("message", ""))
        return None


@pytest.fixture
def socketio_server():
    return FakeSocketIOServer()


@pytest.fixture
def manager(socketio_server):
    lock = asyncio.Lock()
    mgr = WebSocketManager(socketio_server, lock)
    return mgr


@pytest.fixture
def connected_client(manager):
    """Register a test client connection."""
    sid = "test-sid-001"
    asyncio.get_event_loop().run_until_complete(manager.handle_connect("/test", sid, user_id="test_user"))
    return sid


class TestConnectDisconnect:
    @pytest.mark.asyncio
    async def test_connect_tracks_session(self, manager):
        sid = "sid-connect-1"
        await manager.handle_connect("/test", sid, user_id="user1")
        assert sid in manager._sessions  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_disconnect_removes_session(self, manager):
        sid = "sid-disconnect-1"
        await manager.handle_connect("/test", sid, user_id="user1")
        await manager.handle_disconnect("/test", sid)
        assert sid not in manager._sessions  # type: ignore[attr-defined]


class TestEventRouting:
    @pytest.mark.asyncio
    async def test_echo_handler_returns_response(self, manager, socketio_server):
        lock = asyncio.Lock()
        handler = EchoHandler.get_instance(socketio_server, lock)
        manager.register_handlers({"/test": [handler]})

        sid = "sid-echo-1"
        await manager.handle_connect("/test", sid, user_id="user1")

        result = await manager.route_event("/test", "echo", {"msg": "hello"}, sid)

        assert result is not None
        assert result["echo"] is True
        assert result["data"]["msg"] == "hello"

        # Verify handler recorded the event
        assert EchoHandler._last_instance is not None
        assert len(EchoHandler._last_instance.processed_events) == 1
        assert EchoHandler._last_instance.processed_events[0]["event"] == "echo"

    @pytest.mark.asyncio
    async def test_ping_returns_pong(self, manager, socketio_server):
        lock = asyncio.Lock()
        handler = EchoHandler.get_instance(socketio_server, lock)
        manager.register_handlers({"/test": [handler]})

        sid = "sid-ping-1"
        await manager.handle_connect("/test", sid, user_id="user1")

        result = await manager.route_event("/test", "ping", {"ts": 123}, sid)
        assert result["pong"] is True
        assert result["original"]["ts"] == 123

    @pytest.mark.asyncio
    async def test_fire_and_forget_returns_none(self, manager, socketio_server):
        lock = asyncio.Lock()
        handler = FireAndForgetHandler.get_instance(socketio_server, lock)
        manager.register_handlers({"/test": [handler]})

        sid = "sid-faf-1"
        await manager.handle_connect("/test", sid, user_id="user1")

        result = await manager.route_event("/test", "notify", {"message": "alert"}, sid)
        assert result is None

        # Handler still processed it
        assert FireAndForgetHandler._last_instance is not None
        assert "alert" in FireAndForgetHandler._last_instance.received

    @pytest.mark.asyncio
    async def test_unknown_event_returns_none(self, manager):
        sid = "sid-unknown-1"
        await manager.handle_connect("/test", sid, user_id="user1")

        result = await manager.route_event("/test", "nonexistent", {}, sid)
        assert result is None


class TestBroadcastAndEmit:
    @pytest.mark.asyncio
    async def test_emit_to_specific_sid(self, manager, socketio_server):
        lock = asyncio.Lock()
        handler = EchoHandler.get_instance(socketio_server, lock)
        manager.register_handlers({"/test": [handler]})

        sid = "sid-emit-1"
        await manager.handle_connect("/test", sid, user_id="user1")

        await manager.emit_to("/test", sid, "notification", {"text": "hi"}, handler_id="test")

        # Socket.IO server should have been called
        assert socketio_server.emit.called

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, manager, socketio_server):
        lock = asyncio.Lock()
        handler = EchoHandler.get_instance(socketio_server, lock)
        manager.register_handlers({"/test": [handler]})

        for i in range(3):
            await manager.handle_connect("/test", f"sid-bcast-{i}", user_id=f"user{i}")

        await manager.broadcast("/test", "announcement", {"text": "hello all"}, handler_id="test")

        assert socketio_server.emit.called


class TestRequestResponse:
    @pytest.mark.asyncio
    async def test_request_aggregates_results(self, manager, socketio_server):
        lock = asyncio.Lock()
        handler = EchoHandler.get_instance(socketio_server, lock)
        manager.register_handlers({"/test": [handler]})

        sid = "sid-req-1"
        await manager.handle_connect("/test", sid, user_id="user1")

        result = await manager.request_for_sid(
            namespace="/test",
            sid=sid,
            event_type="echo",
            data={"q": "test"},
            handler_id="test",
        )

        assert "results" in result
        assert len(result["results"]) >= 1
        assert result["results"][0]["ok"] is True
