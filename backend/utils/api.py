import json
import socket
import struct
import threading
from abc import abstractmethod
from functools import wraps
from pathlib import Path
from typing import Any, TypedDict, Union

from flask import (
    Flask,
    Request,
    Response,
    redirect,
    request,
    session,
    url_for,
)
from werkzeug.wrappers.response import Response as BaseResponse

from backend.core.agent import AgentContext
from backend.utils import cache, files
from backend.utils.errors import format_error
from backend.utils.print_style import PrintStyle
from initialize import initialize_agent

ThreadLockType = Union[threading.Lock, threading.RLock]

CACHE_AREA = "api_handlers(api)(plugins)"
cache.toggle_area(CACHE_AREA, False)  # cache off for now

Input = dict
Output = Union[dict[str, Any], Response, TypedDict]  # type: ignore


class ApiHandler:
    def __init__(self, app: Flask, thread_lock: ThreadLockType):
        self.app = app
        self.thread_lock = thread_lock

    @classmethod
    def requires_loopback(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return False

    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return cls.requires_auth()

    @abstractmethod
    async def process(self, input: Input, request: Request) -> Output:
        pass

    async def handle_request(self, request: Request) -> Response:
        try:
            # input data from request based on type
            input_data: Input = {}
            if request.is_json:
                try:
                    if request.data:  # Check if there's any data
                        input_data = request.get_json()
                    # If empty or not valid JSON, use empty dict
                except Exception as e:
                    # Just log the error and continue with empty input
                    PrintStyle().print(f"Error parsing JSON: {str(e)}")
                    input_data = {}
            else:
                # input_data = {"data": request.get_data(as_text=True)}
                input_data = {}

            # process via handler
            output = await self.process(input_data, request)

            # return output based on type
            if isinstance(output, Response):
                return output
            else:
                response_json = json.dumps(output)
                return Response(response=response_json, status=200, mimetype="application/json")

            # return exceptions with 500
        except Exception as e:
            error = format_error(e)
            PrintStyle.error(f"API error: {error}")
            return Response(response=error, status=500, mimetype="text/plain")

    # get context to run ctx ai in
    def use_context(self, ctxid: str, create_if_not_exists: bool = True):
        with self.thread_lock:
            if not ctxid:
                first = AgentContext.first()
                if first:
                    AgentContext.use(first.id)
                    return first
                context = AgentContext(config=initialize_agent(), set_current=True)
                return context
            got = AgentContext.use(ctxid)
            if got:
                return got
            if create_if_not_exists:
                context = AgentContext(config=initialize_agent(), id=ctxid, set_current=True)
                return context
            else:
                raise Exception(f"Context {ctxid} not found")


def is_loopback_address(address: str) -> bool:
    loopback_checker = {
        socket.AF_INET: lambda x: (
            (struct.unpack("!I", socket.inet_aton(x))[0] >> (32 - 8)) == 127
        ),
        socket.AF_INET6: lambda x: x == "::1",
    }
    address_type = "hostname"
    try:
        socket.inet_pton(socket.AF_INET6, address)
        address_type = "ipv6"
    except OSError:
        try:
            socket.inet_pton(socket.AF_INET, address)
            address_type = "ipv4"
        except OSError:
            address_type = "hostname"

    if address_type == "ipv4":
        return loopback_checker[socket.AF_INET](address)
    elif address_type == "ipv6":
        return loopback_checker[socket.AF_INET6](address)
    else:
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                r = socket.getaddrinfo(address, None, family, socket.SOCK_STREAM)
            except socket.gaierror:
                return False
            for family, _, _, _, sockaddr in r:
                if not loopback_checker[family](sockaddr[0]):
                    return False
        return True


def requires_api_key(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        from backend.utils.settings import get_settings

        valid_api_key = get_settings()["mcp_server_token"]

        if api_key := request.headers.get("X-API-KEY"):
            if api_key != valid_api_key:
                return Response("Invalid API key", 401)
        elif request.json and request.json.get("api_key"):
            api_key = request.json.get("api_key")
            if api_key != valid_api_key:
                return Response("Invalid API key", 401)
        else:
            return Response("API key required", 401)
        return await f(*args, **kwargs)

    return decorated


def requires_loopback(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        if not is_loopback_address(str(request.remote_addr)):
            return Response("Access denied.", 403, {})
        return await f(*args, **kwargs)

    return decorated


def requires_auth(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        from backend.utils import login

        user_pass_hash = login.get_credentials_hash()
        if not user_pass_hash:
            return await f(*args, **kwargs)
        if session.get("authentication") != user_pass_hash:
            return redirect(url_for("login_handler"))
        return await f(*args, **kwargs)

    return decorated


def csrf_protect(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        from backend.utils import runtime

        token = session.get("csrf_token")
        header = request.headers.get("X-CSRF-Token")
        cookie = request.cookies.get("csrf_token_" + runtime.get_runtime_id())
        sent = header or cookie
        if not token or not sent or token != sent:
            return Response("CSRF token missing or invalid", 403)
        return await f(*args, **kwargs)

    return decorated


def register_api_route(app: Flask, lock: ThreadLockType) -> None:
    from backend.utils import plugins
    from backend.utils.extract_tools import load_classes_from_file

    async def _dispatch(path: str) -> BaseResponse:
        # Return cached wrapped handler if available
        cached = cache.get(CACHE_AREA, path)
        if cached is not None:
            return await cached()

        # Resolve file path for the handler
        # Try built-in api folders first, then plugin api folders
        handler_cls: type[ApiHandler] | None = None

        # Check built-in backend/api/<path>.py (Legacy) or backend/interfaces/api/routes/<path>.py
        locations = [
            files.get_abs_path("backend/api"),
            files.get_abs_path("backend/interfaces/api/routes"),
        ]

        # Search for file in locations, potentially in subdirectories
        for base_dir in locations:
            # First try direct match
            builtin_file = Path(base_dir) / f"{path}.py"
            if builtin_file.is_file():
                classes = load_classes_from_file(str(builtin_file), ApiHandler)
                if classes:
                    handler_cls = classes[0]
                    break

            # If path has no extension and not found, try searching subdirectories
            # This allows /api/message to find /api/chat/message.py
            if handler_cls is None:
                # Use glob to find file with this name in any subdirectory
                matches = list(Path(base_dir).glob(f"**/{path}.py"))
                if matches:
                    # Take first match
                    classes = load_classes_from_file(str(matches[0]), ApiHandler)
                    if classes:
                        handler_cls = classes[0]
                        break

        # Check plugin api folders: path format plugins/<plugin_name>/<handler>
        if handler_cls is None and path.startswith("plugins/"):
            parts = path.split("/", 2)
            if len(parts) == 3:
                _, plugin_name, handler_name = parts
                plugin_dir = plugins.find_plugin_dir(plugin_name)
                if plugin_dir:
                    plugin_file = Path(plugin_dir) / "api" / f"{handler_name}.py"
                    if plugin_file.is_file():
                        classes = load_classes_from_file(str(plugin_file), ApiHandler)
                        if classes:
                            handler_cls = classes[0]

        if handler_cls is None:
            return Response(f"API endpoint not found: {path}", 404)

        # Check method is allowed
        if request.method not in handler_cls.get_methods():
            return Response(f"Method {request.method} not allowed for: {path}", 405)

        # Build handler call, wrapping with security decorators as required
        async def call_handler() -> BaseResponse:
            instance = handler_cls(app, lock)
            return await instance.handle_request(request=request)

        handler_fn = call_handler
        if handler_cls.requires_csrf():
            handler_fn = csrf_protect(handler_fn)
        if handler_cls.requires_api_key():
            handler_fn = requires_api_key(handler_fn)
        if handler_cls.requires_auth():
            handler_fn = requires_auth(handler_fn)
        if handler_cls.requires_loopback():
            handler_fn = requires_loopback(handler_fn)

        cache.add(CACHE_AREA, path, handler_fn)
        return await handler_fn()

    app.add_url_rule(
        "/api/<path:path>",
        "api_dispatch",
        _dispatch,
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
