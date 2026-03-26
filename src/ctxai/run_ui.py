from __future__ import annotations

import asyncio
import os
import secrets
import sys
import threading
import time
import urllib.request
from collections.abc import Iterable
from typing import cast

import socketio  # type: ignore[import-untyped]
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from socketio import ASGIApp, packet
from starlette.middleware.sessions import SessionMiddleware

import ctxai.initialize as initialize
from ctxai.helpers import cache, dotenv, extension, fasta2a_server, files, git, login, mcp_server, process, runtime
from ctxai.helpers import settings as settings_helper
from ctxai.helpers.api import register_api_route, requires_auth
from ctxai.helpers.files import get_abs_path
from ctxai.helpers.flask_compat import (
    Response as CompatResponse,
)
from ctxai.helpers.flask_compat import (
    get_session_from_environ,
    redirect,
    render_template_string,
    send_file,
    set_session_secret,
    url_for,
)
from ctxai.helpers.flask_compat import (
    session as compat_session,
)
from ctxai.helpers.opentelemetry_instrumentation import setup_tracing
from ctxai.helpers.print_style import PrintStyle
from ctxai.helpers.prometheus_metrics import metrics
from ctxai.helpers.structured_logging import setup_structured_logging
from ctxai.helpers.websocket import WebSocketHandler, validate_ws_origin

# Simple in-memory rate limiter for login attempts
_login_attempts: dict[str, list[float]] = {}
_LOGIN_MAX_ATTEMPTS = 10
_LOGIN_WINDOW_SECONDS = 300  # 5 minutes

# General API rate limiter
_api_attempts: dict[str, list[float]] = {}
_API_MAX_ATTEMPTS = 100  # 100 requests per minute
_API_WINDOW_SECONDS = 60  # 1 minute


def _check_login_rate_limit(remote_addr: str) -> bool:
    """Return True if the request is allowed, False if rate-limited."""
    now = time.monotonic()
    window_start = now - _LOGIN_WINDOW_SECONDS
    attempts = _login_attempts.get(remote_addr, [])
    attempts = [t for t in attempts if t > window_start]
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        _login_attempts[remote_addr] = attempts
        return False
    attempts.append(now)
    _login_attempts[remote_addr] = attempts
    return True


def _check_api_rate_limit(remote_addr: str) -> bool:
    """Return True if the API request is allowed, False if rate-limited."""
    now = time.monotonic()
    window_start = now - _API_WINDOW_SECONDS
    attempts = _api_attempts.get(remote_addr, [])
    attempts = [t for t in attempts if t > window_start]
    if len(attempts) >= _API_MAX_ATTEMPTS:
        _api_attempts[remote_addr] = attempts
        return False
    attempts.append(now)
    _api_attempts[remote_addr] = attempts
    return True


# disable logging
import logging

from ctxai.helpers.websocket_manager import WebSocketManager
from ctxai.helpers.websocket_namespace_discovery import discover_websocket_namespaces

logging.getLogger().setLevel(logging.WARNING)


# Set the new timezone to 'UTC'
os.environ["TZ"] = "UTC"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Apply the timezone change
if hasattr(time, "tzset"):
    time.tzset()

# ─── Generate session secret ───────────────────────────────────────────────────
_session_secret = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
set_session_secret(_session_secret)

# ─── Initialize FastAPI app ────────────────────────────────────────────────────
UPLOAD_LIMIT_BYTES = 5 * 1024 * 1024 * 1024

app = FastAPI(
    title="CtxAI",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Mount static files — prefer Vite build output (dist/) when available, fall back to raw webui/
_webui_dir = get_abs_path("./webui")
_dist_dir = os.path.join(_webui_dir, "dist")
_static_dir = _dist_dir if os.path.isdir(_dist_dir) else _webui_dir
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# Add session middleware (same signing key as the compat layer)
app.add_middleware(SessionMiddleware, secret_key=_session_secret, same_site="lax", max_age=86400)

lock = asyncio.Lock()

socketio_server = socketio.AsyncServer(
    async_mode="asgi",
    namespaces="*",
    cors_allowed_origins=lambda _origin, environ: validate_ws_origin(environ)[0],
    logger=False,
    engineio_logger=False,
    ping_interval=25,
    ping_timeout=20,
    max_http_buffer_size=50 * 1024 * 1024,
)

websocket_manager = WebSocketManager(socketio_server, lock)
_settings = settings_helper.get_settings()
settings_helper.set_runtime_settings_snapshot(_settings)
websocket_manager.set_server_restart_broadcast(_settings.get("websocket_server_restart_enabled", True))


# ═══════════════════════════════════════════════════════════════════════════════
# Security headers middleware
# ═══════════════════════════════════════════════════════════════════════════════
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none';"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    path = request.url.path or ""
    if any(
        path.endswith(ext)
        for ext in (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".woff", ".woff2", ".ttf", ".eot")
    ):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path.endswith(".html") or path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    elif path.startswith("/api/") or path.startswith("/poll") or path.startswith("/message"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    if os.environ.get("HTTPS") == "1" or request.headers.get("x-forwarded-proto") == "https":
        pass  # Session middleware handles secure cookies
    return response


# ═══════════════════════════════════════════════════════════════════════════════
# Session context middleware — populates compat_session + compat_request
# ═══════════════════════════════════════════════════════════════════════════════
@app.middleware("http")
async def session_context_middleware(request: Request, call_next):
    from ctxai.helpers.flask_compat import _form_data_cache, _request_ctx, _session_data, _session_dirty

    _request_ctx.set(request)
    # Load session from Starlette's SessionMiddleware (stored in request.state.session)
    star_session = getattr(request.state, "session", None)
    _session_data.set(dict(star_session) if star_session else {})
    _session_dirty.set(False)
    _form_data_cache.set(None)

    response = await call_next(request)

    # Save session back
    if _session_dirty.get() and star_session is not None:
        star_session.clear()
        star_session.update(_session_data.get())

    _request_ctx.set(None)
    _form_data_cache.set(None)
    return response


# ═══════════════════════════════════════════════════════════════════════════════
# Auth routes
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/login", methods=["GET", "POST"])
@extension.extensible
async def login_handler(request: Request):
    error = None
    if request.method == "POST":
        form = await request.form()
        remote_addr = request.client.host if request.client else "unknown"
        if not _check_login_rate_limit(remote_addr):
            await asyncio.sleep(2)
            error = "Too many login attempts. Please wait before trying again."
        else:
            user = dotenv.get_dotenv_value("AUTH_LOGIN")
            password = dotenv.get_dotenv_value("AUTH_PASSWORD")
            username = form.get("username", "")

            if username == user and form.get("password", "") == password:
                compat_session["authentication"] = login.get_credentials_hash()
                return redirect(url_for("serve_index"))
            else:
                await asyncio.sleep(1)
                error = "Invalid Credentials. Please try again."

    login_page_content = files.read_file("webui/login.html")
    return render_template_string(login_page_content, error=error)


@app.route("/logout")
@extension.extensible
async def logout_handler(request: Request):
    compat_session.pop("authentication", None)
    return redirect(url_for("login_handler"))


# ═══════════════════════════════════════════════════════════════════════════════
# Index route
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/", methods=["GET"])
@requires_auth
@extension.extensible
async def serve_index(request: Request):
    gitinfo = None
    try:
        gitinfo = git.get_git_info()
    except Exception:
        gitinfo = {"version": "unknown", "commit_time": "unknown"}

    # Prefer Vite-built index.html when dist/ exists
    dist_index = os.path.join(_dist_dir, "index.html")
    if os.path.isfile(dist_index):
        with open(dist_index) as f:
            index = f.read()
    else:
        index = files.read_file("webui/index.html")

    index = files.replace_placeholders_text(
        _content=index,
        version_no=gitinfo["version"],
        version_time=gitinfo["commit_time"],
        runtime_id=runtime.get_runtime_id(),
        runtime_is_development=("true" if runtime.is_development() else "false"),
        logged_in=("true" if login.get_credentials_hash() else "false"),
    )
    return CompatResponse(response=index, status=200, mimetype="text/html")


# ═══════════════════════════════════════════════════════════════════════════════
# Plugin / Extension asset serving
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/plugins/{plugin_name}/{asset_path:path}", methods=["GET"])
@requires_auth
async def serve_builtin_plugin_asset(request: Request, plugin_name: str, asset_path: str):
    return await _serve_plugin_asset(plugin_name, asset_path)


@app.route("/usr/plugins/{plugin_name}/{asset_path:path}", methods=["GET"])
@requires_auth
async def serve_plugin_asset(request: Request, plugin_name: str, asset_path: str):
    return await _serve_plugin_asset(plugin_name, asset_path)


@app.route("/extensions/webui/{asset_path:path}", methods=["GET"])
@requires_auth
async def serve_extension_asset(request: Request, asset_path: str):
    path = files.get_abs_path("extensions/webui", asset_path)
    if not files.is_in_dir(path, "extensions/webui"):
        return CompatResponse("Access denied", 403)
    return send_file(path)


@extension.extensible
async def _serve_plugin_asset(plugin_name: str, asset_path: str):
    from ctxai.helpers import plugins

    plugin_dir = plugins.find_plugin_dir(plugin_name)
    if not plugin_dir:
        return CompatResponse("Plugin not found", 404)

    try:
        asset_file = files.get_abs_path(plugin_dir, asset_path)
        webui_dir = files.get_abs_path(plugin_dir, "webui")
        webui_extensions_dir = files.get_abs_path(plugin_dir, "extensions/webui")

        if not files.is_in_dir(str(asset_file), str(webui_dir)) and not files.is_in_dir(
            str(asset_file),
            str(webui_extensions_dir),
        ):
            return CompatResponse("Access denied", 403)

        if not files.is_file(asset_file):
            return CompatResponse("Asset not found", 404)

        return send_file(str(asset_file))
    except Exception as e:
        PrintStyle.error(f"Error serving plugin asset: {e}")
        return CompatResponse("Error serving asset", 500)


# ═══════════════════════════════════════════════════════════════════════════════
# WebSocket namespace configuration
# ═══════════════════════════════════════════════════════════════════════════════
def _build_websocket_handlers_by_namespace(
    socketio_server: socketio.AsyncServer,
    lock: threading.RLock | asyncio.Lock,
) -> dict[str, list[WebSocketHandler]]:
    discoveries = discover_websocket_namespaces(
        handlers_folder="python/websocket_handlers",
        include_root_default=True,
    )
    handlers_by_namespace: dict[str, list[WebSocketHandler]] = {}
    for discovery in discoveries:
        namespace = discovery.namespace
        for handler_cls in discovery.handler_classes:
            handler = handler_cls.get_instance(socketio_server, lock)
            handlers_by_namespace.setdefault(namespace, []).append(handler)
    return handlers_by_namespace


def configure_websocket_namespaces(
    *,
    socketio_server: socketio.AsyncServer,
    websocket_manager: WebSocketManager,
    handlers_by_namespace: dict[str, list[WebSocketHandler]],
) -> set[str]:
    namespace_map: dict[str, list[WebSocketHandler]] = {
        namespace: list(handlers) for namespace, handlers in handlers_by_namespace.items()
    }
    namespace_map.setdefault("/", [])

    websocket_manager.register_handlers(cast(dict[str, Iterable[WebSocketHandler]], namespace_map))

    allowed_namespaces = set(namespace_map.keys())
    original_handle_connect = socketio_server._handle_connect  # type: ignore[attr-defined]

    async def _handle_connect_with_namespace_gatekeeper(eio_sid, namespace, data):
        requested = namespace or "/"
        if requested not in allowed_namespaces:
            await socketio_server._send_packet(
                eio_sid,
                socketio_server.packet_class(
                    packet.CONNECT_ERROR,
                    data={
                        "message": "UNKNOWN_NAMESPACE",
                        "data": {"code": "UNKNOWN_NAMESPACE", "namespace": requested},
                    },
                    namespace=requested,
                ),
            )
            return
        await original_handle_connect(eio_sid, namespace, data)

    socketio_server._handle_connect = _handle_connect_with_namespace_gatekeeper  # type: ignore[assignment]

    def _register_namespace_handlers(namespace: str, namespace_handlers: list[WebSocketHandler]) -> None:
        auth_required = False
        csrf_required = False
        if namespace_handlers:
            auth_required = bool(namespace_handlers[0].requires_auth())
            csrf_required = bool(namespace_handlers[0].requires_csrf())
            for handler in namespace_handlers[1:]:
                if bool(handler.requires_auth()) != auth_required or bool(handler.requires_csrf()) != csrf_required:
                    raise ValueError(
                        f"WebSocket namespace {namespace!r} has mixed auth/csrf requirements across handlers",
                    )

        @socketio_server.on("connect", namespace=namespace)
        async def _connect(  # type: ignore[override]
            sid,
            environ,
            _auth,
            _namespace: str = namespace,
            _auth_required: bool = auth_required,
            _csrf_required: bool = csrf_required,
        ):
            # Validate origin (no Flask context needed)
            origin_ok, origin_reason = validate_ws_origin(environ)
            if not origin_ok:
                PrintStyle.warning(
                    f"WebSocket origin validation failed for {_namespace} {sid}: {origin_reason or 'invalid'}",
                )
                return False

            # Parse session from raw cookie (no Flask context needed)
            sess = get_session_from_environ(environ)

            if _auth_required:
                credentials_hash = login.get_credentials_hash()
                if credentials_hash:
                    if sess.get("authentication") != credentials_hash:
                        PrintStyle.warning(
                            f"WebSocket authentication failed for {_namespace} {sid}: session not valid",
                        )
                        return False
                else:
                    PrintStyle.debug("WebSocket authentication required but credentials not configured; proceeding")

            if _csrf_required:
                expected_token = sess.get("csrf_token")
                if not isinstance(expected_token, str) or not expected_token:
                    PrintStyle.warning(
                        f"WebSocket CSRF validation failed for {_namespace} {sid}: csrf_token not initialized",
                    )
                    return False

                auth_token = None
                if isinstance(_auth, dict):
                    auth_token = _auth.get("csrf_token") or _auth.get("csrfToken")
                if not isinstance(auth_token, str) or not auth_token:
                    PrintStyle.warning(
                        f"WebSocket CSRF validation failed for {_namespace} {sid}: missing csrf_token in auth",
                    )
                    return False
                if auth_token != expected_token:
                    PrintStyle.warning(
                        f"WebSocket CSRF validation failed for {_namespace} {sid}: csrf_token mismatch",
                    )
                    return False

                # Parse CSRF cookie from raw environ
                raw_cookie = environ.get("HTTP_COOKIE", "")
                cookie_name = f"csrf_token_{runtime.get_runtime_id()}"
                cookie_token = None
                for part in raw_cookie.split(";"):
                    part = part.strip()
                    if part.startswith(cookie_name + "="):
                        cookie_token = part.split("=", 1)[1]
                        break
                if cookie_token != expected_token:
                    PrintStyle.warning(
                        f"WebSocket CSRF validation failed for {_namespace} {sid}: csrf cookie mismatch",
                    )
                    return False

            user_id = sess.get("user_id") or "single_user"
            await websocket_manager.handle_connect(_namespace, sid, user_id=user_id)
            return True

        @socketio_server.on("disconnect", namespace=namespace)
        async def _disconnect(sid, _namespace: str = namespace):  # type: ignore[override]
            await websocket_manager.handle_disconnect(_namespace, sid)

        def _register_socketio_event(event_type: str) -> None:
            @socketio_server.on(event_type, namespace=namespace)
            async def _event_handler(
                sid,
                data,
                _event_type: str = event_type,
                _namespace: str = namespace,
            ):
                payload = data or {}
                return await websocket_manager.route_event(_namespace, _event_type, payload, sid)

        for _event_type in websocket_manager.iter_event_types(namespace):
            _register_socketio_event(_event_type)

        @socketio_server.on("*", namespace=namespace)
        async def _catch_all(event, sid, data, _namespace: str = namespace):
            payload = data or {}
            return await websocket_manager.route_event(_namespace, event, payload, sid)

    for namespace, namespace_handlers in namespace_map.items():
        _register_namespace_handlers(namespace, namespace_handlers)

    return allowed_namespaces


# ═══════════════════════════════════════════════════════════════════════════════
# Server startup
# ═══════════════════════════════════════════════════════════════════════════════
def run():
    # Use uvloop on Linux for 2-4x async throughput improvement
    if sys.platform != "win32":
        try:
            import uvloop

            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except ImportError:
            pass

    PrintStyle().print("Initializing framework...")

    # migrate data before anything else
    initialize.initialize_migration()

    # Configure in-memory cache: 500 entries per area, 1-hour TTL
    cache.configure(max_size=500, ttl_seconds=3600)

    # Initialize observability
    setup_structured_logging(level=logging.INFO)
    setup_tracing()

    # Warn if authentication is not configured
    if not login.is_login_required():
        PrintStyle(background_color="yellow", font_color="black", padding=True).print(
            "WARNING: No authentication configured. Set AUTH_LOGIN and AUTH_PASSWORD in usr/.env to secure access.",
        )

    PrintStyle().print("Starting server...")

    # Get configuration from environment
    port = runtime.get_web_ui_port()
    host = runtime.get_arg("host") or dotenv.get_dotenv_value("WEB_UI_HOST") or "localhost"

    # Set metrics server info now that host/port are known
    metrics.set_server_info(
        {
            "version": dotenv.get_dotenv_value("CTXAI_VERSION", "dev"),
            "pid": str(os.getpid()),
            "host": host,
            "port": str(port),
        },
    )

    register_api_route(app, lock)

    handlers_by_namespace = _build_websocket_handlers_by_namespace(socketio_server, lock)
    configure_websocket_namespaces(
        socketio_server=socketio_server,
        websocket_manager=websocket_manager,
        handlers_by_namespace=handlers_by_namespace,
    )

    init_ctx()

    # Mount MCP and A2A sub-applications directly on FastAPI
    app.mount("/mcp", app=mcp_server.DynamicMcpProxy.get_instance())
    app.mount("/a2a", app=fasta2a_server.DynamicA2AProxy.get_instance())

    # Wrap the entire FastAPI app with Socket.IO
    asgi_app = ASGIApp(socketio_server, other_asgi_app=app)

    def flush_and_shutdown_callback() -> None:
        """TODO(dev): add cleanup + flush-to-disk logic here."""
        return

    flush_ran = False

    def _run_flush(reason: str) -> None:
        nonlocal flush_ran
        if flush_ran:
            return
        flush_ran = True
        try:
            flush_and_shutdown_callback()
        except Exception as e:
            PrintStyle.warning(f"Shutdown flush failed ({reason}): {e}")

    if sys.platform != "win32":
        try:
            import uvloop

            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except ImportError:
            pass

    config = uvicorn.Config(
        asgi_app,
        host=host,
        port=port,
        log_level="info",
        access_log=_settings.get("uvicorn_access_logs_enabled", False),
        ws="wsproto",
    )
    server = uvicorn.Server(config)

    class _UvicornServerWrapper:
        def __init__(self, server: uvicorn.Server):
            self._server = server

        def shutdown(self) -> None:
            _run_flush("shutdown")
            self._server.should_exit = True

    process.set_server(_UvicornServerWrapper(server))

    PrintStyle().debug(f"Starting server at http://{host}:{port} ...")
    threading.Thread(target=wait_for_health, args=(host, port), daemon=True).start()
    try:
        server.run()
    finally:
        _run_flush("server_exit")


def wait_for_health(host: str, port: int):
    url = f"http://{host}:{port}/health"
    while True:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    PrintStyle().print("Ctx AI is running.")
                    return
        except Exception:
            pass
        time.sleep(1)


@extension.extensible
def init_ctx():
    # initialize contexts and MCP
    init_chats = initialize.initialize_chats()
    # only wait for init chats, otherwise they would seem to disappear for a while on restart
    init_chats.result_sync()

    initialize.initialize_mcp()
    # start job loop
    initialize.initialize_job_loop()
    # preload
    initialize.initialize_preload()


# run the internal server
if __name__ == "__main__":
    runtime.initialize()
    dotenv.load_dotenv()
    run()
