import argparse
import asyncio
import inspect
import secrets
import sys
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, cast, overload

from ctxai.helpers import dotenv, files, rfc

# Thread pool for running async coroutines from sync contexts
_async_thread_pool: ThreadPoolExecutor | None = None
_async_thread_pool_lock = threading.Lock()


def _get_async_thread_pool() -> ThreadPoolExecutor:
    """Get or create a singleton thread pool for async bridging."""
    global _async_thread_pool
    if _async_thread_pool is None:
        with _async_thread_pool_lock:
            if _async_thread_pool is None:
                _async_thread_pool = ThreadPoolExecutor(
                    max_workers=4,
                    thread_name_prefix="async-bridge",
                )
    return _async_thread_pool


def safe_run_async[T](coro: Awaitable[T]) -> T:
    """Run an async coroutine safely from a synchronous context.

    Handles two cases:
    1. No running loop: uses asyncio.run() directly (most efficient).
    2. Running loop exists: delegates to a thread pool with its own event loop.

    This replaces nest_asyncio.apply() with a thread-safe alternative.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to use asyncio.run()
        return asyncio.run(coro)
    else:
        # Running loop exists — delegate to thread pool
        pool = _get_async_thread_pool()
        future = pool.submit(asyncio.run, coro)
        return future.result()


parser = argparse.ArgumentParser()
args: dict[str, Any] = {}
dockerman = None
runtime_id = None


def initialize():
    global args
    if args:
        return
    parser.add_argument("--port", type=int, default=None, help="Web UI port")
    parser.add_argument("--host", type=str, default=None, help="Web UI host")
    parser.add_argument(
        "--cloudflare_tunnel",
        type=bool,
        default=False,
        help="Use cloudflare tunnel for public URL",
    )
    parser.add_argument("--development", type=bool, default=False, help="Development mode")

    known, unknown = parser.parse_known_args()
    args = vars(known)
    for arg in unknown:
        if "=" in arg:
            key, value = arg.split("=", 1)
            key = key.lstrip("-")
            args[key] = value


def get_arg(name: str):
    global args
    return args.get(name, None)


def has_arg(name: str):
    global args
    return name in args


def is_dockerized() -> bool:
    return bool(get_arg("dockerized"))


def is_development() -> bool:
    return not is_dockerized()


def get_local_url():
    if is_dockerized():
        return "host.docker.internal"
    return "127.0.0.1"


def get_runtime_id() -> str:
    global runtime_id
    if not runtime_id:
        runtime_id = secrets.token_hex(8)
    return runtime_id


def get_persistent_id() -> str:
    id = dotenv.get_dotenv_value("A0_PERSISTENT_RUNTIME_ID")
    if not id:
        id = secrets.token_hex(16)
        dotenv.save_dotenv_value("A0_PERSISTENT_RUNTIME_ID", id)
    return id


@overload
async def call_development_function[T](func: Callable[..., Awaitable[T]], *args, **kwargs) -> T: ...


@overload
async def call_development_function[T](func: Callable[..., T], *args, **kwargs) -> T: ...


async def call_development_function[T](func: Callable[..., T] | Callable[..., Awaitable[T]], *args, **kwargs) -> T:
    if is_development():
        url = _get_rfc_url()
        password = _get_rfc_password()
        # Normalize path components to build a valid Python module path across OSes
        module_path = Path(files.deabsolute_path(func.__code__.co_filename)).with_suffix("")
        module = ".".join(module_path.parts)  # __module__ is not reliable
        result = await rfc.call_rfc(
            url=url,
            password=password,
            module=module,
            function_name=func.__name__,
            args=list(args),
            kwargs=kwargs,
        )
        return cast(T, result)
    else:
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)  # type: ignore


async def handle_rfc(rfc_call: rfc.RFCCall):
    return await rfc.handle_rfc(rfc_call=rfc_call, password=_get_rfc_password())


def _get_rfc_password() -> str:
    password = dotenv.get_dotenv_value(dotenv.KEY_RFC_PASSWORD)
    if not password:
        raise Exception("No RFC password, cannot handle RFC calls.")
    return password


def _get_rfc_url() -> str:
    from ctxai.helpers import settings

    set = settings.get_settings()
    url = set["rfc_url"]
    if "://" not in url:
        url = "http://" + url
    if url.endswith("/"):
        url = url[:-1]
    url = url + ":" + str(set["rfc_port_http"])
    url += "/api/rfc"
    return url


def call_development_function_sync[T](func: Callable[..., T] | Callable[..., Awaitable[T]], *args, **kwargs) -> T:
    # run async function in sync manner using thread pool to avoid thread explosion
    pool = _get_async_thread_pool()
    future = pool.submit(asyncio.run, call_development_function(func, *args, **kwargs))
    try:
        return cast(T, future.result(timeout=30))
    except TimeoutError as err:
        raise TimeoutError("Function call timed out after 30 seconds") from err


def get_web_ui_port():
    web_ui_port = get_arg("port") or int(dotenv.get_dotenv_value("WEB_UI_PORT", 0)) or 5000
    return web_ui_port


def get_tunnel_api_port():
    tunnel_api_port = get_arg("tunnel_api_port") or int(dotenv.get_dotenv_value("TUNNEL_API_PORT", 0)) or 55520
    return tunnel_api_port


def get_platform():
    return sys.platform


def is_windows():
    return get_platform() == "win32"


def get_terminal_executable():
    if is_windows():
        return "powershell.exe"
    else:
        return "/bin/bash"
