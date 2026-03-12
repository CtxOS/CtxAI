import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from uvicorn.middleware.wsgi import WSGIMiddleware
from starlette.routing import Mount
import uvicorn
import socketio
import engineio.async_server

from ctxai.shared import compat
compat.apply_asyncio_patch()

# Import core initialization from the legacy entry point
from run_ui import (
    webapp,
    socketio_server,
    websocket_manager,
    configure_websocket_namespaces,
    _build_websocket_handlers_by_namespace,
    init_ctxai,
    wait_for_health,
    lock,
)
from ctxai.shared import runtime, dotenv, process, mcp_server, fasta2a_server
from ctxai.shared.print_style import PrintStyle

# Track flush state
flush_ran = False
def _run_flush(reason: str) -> None:
    global flush_ran
    if flush_ran:
        return
    flush_ran = True
    try:
        # flush logic
        pass
    except Exception as e:
        PrintStyle.warning(f"Shutdown flush failed ({reason}): {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    PrintStyle().print("Initializing framework via FastAPI...")
    import initialize
    initialize.initialize_migration()
    init_ctxai()
    yield
    # Shutdown actions
    _run_flush("server_exit")


# Create native FastAPI application
app = FastAPI(
    title="Ctx AI API",
    description="FastAPI Gateway for Ctx AI",
    lifespan=lifespan
)

# ---------------------------------------------------------
# Phase 1: Native FastAPI Endpoints
# ---------------------------------------------------------
@app.get("/fastapi-health", tags=["System"])
async def fastapi_health_check():
    return {"status": "ok", "message": "FastAPI is running the gateway"}

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}

@app.get("/metrics", tags=["System"])
async def metrics_endpoint():
    from ctxai.core.common.metrics import metrics
    from fastapi.responses import Response
    return Response(content=metrics.get_prometheus_metrics(), media_type="text/plain")

# ---------------------------------------------------------
# Phase 8: Multi-User & Workspace Isolation
# ---------------------------------------------------------
from pydantic import BaseModel
from ctxai.core.auth.service import AuthService
from ctxai.core.auth.middleware import get_current_user, get_optional_user

class LoginRequest(BaseModel):
    username: str
    password_hash: str # Send hashed from frontend for safety

@app.post("/auth/login", tags=["Auth"])
async def login(request: LoginRequest):
    token = AuthService.login(request.username, request.password_hash)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/me", tags=["Auth"])
async def get_me(user = Depends(get_current_user)):
    return user

# ---------------------------------------------------------
# Legacy Mounts
# ---------------------------------------------------------
# Convert Flask webapp to ASGI
legacy_wsgi_app = WSGIMiddleware(webapp)

app.mount("/mcp", app=mcp_server.DynamicMcpProxy.get_instance())
app.mount("/a2a", app=fasta2a_server.DynamicA2AProxy.get_instance())
app.mount("/", app=legacy_wsgi_app)

# Wrap the FastAPI app with the SocketIO ASGI app to handle WebSocket upgrades
sio_asgi_app = socketio.ASGIApp(
    socketio_server, 
    other_asgi_app=app
)


def run_fastapi():
    port = runtime.get_web_ui_port()
    host = runtime.get_arg("host") or dotenv.get_dotenv_value("WEB_UI_HOST") or "localhost"
    
    # Configure websocket namespaces
    handlers_by_namespace = _build_websocket_handlers_by_namespace(socketio_server, lock)
    configure_websocket_namespaces(
        webapp=webapp,
        socketio_server=socketio_server,
        websocket_manager=websocket_manager,
        handlers_by_namespace=handlers_by_namespace,
    )
    
    import threading
    threading.Thread(target=wait_for_health, args=(host, port), daemon=True).start()
    
    config = uvicorn.Config(
        sio_asgi_app,
        host=host,
        port=port,
        log_level="info",
        ws="wsproto",
        loop="asyncio",
        http="h11",
    )
    server = uvicorn.Server(config)
    
    class _UvicornServerWrapper:
        def __init__(self, server: uvicorn.Server):
            self._server = server
        def shutdown(self) -> None:
            _run_flush("shutdown")
            self._server.should_exit = True

    process.set_server(_UvicornServerWrapper(server))
    
    PrintStyle().print(f"Starting FastAPI Gateway at http://{host}:{port} ...")
    server.run()

if __name__ == "__main__":
    runtime.initialize()
    dotenv.load_dotenv()
    run_fastapi()
