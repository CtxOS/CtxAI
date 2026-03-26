"""Flask → FastAPI/Starlette compatibility shim.

Provides Flask-like interfaces backed by Starlette/FastAPI so that existing
handler code can migrate incrementally.  No Flask import required.
"""

from __future__ import annotations

import contextvars
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from starlette.datastructures import QueryParams
from starlette.requests import Request as StarletteRequest
from starlette.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.responses import Response as StarletteResponse

# ═══════════════════════════════════════════════════════════════════════════════
# Module-level secrets holder (populated at startup)
# ═══════════════════════════════════════════════════════════════════════════════
SESSION_SECRET: str = ""


def set_session_secret(secret: str) -> None:
    global SESSION_SECRET
    SESSION_SECRET = secret


# ═══════════════════════════════════════════════════════════════════════════════
# Response wrapper — Flask-compatible interface over Starlette Response
# ═══════════════════════════════════════════════════════════════════════════════
class Response(StarletteResponse):
    """Drop-in replacement for ``flask.Response``.

    Accepts the same keyword names Flask uses (``response``, ``mimetype``)
    and delegates to Starlette under the hood.
    """

    def __init__(
        self,
        response: Any = None,
        status: int = 200,
        headers: dict[str, str] | None = None,
        mimetype: str | None = None,
        content_type: str | None = None,
        direct_passthrough: bool = False,
        **_kw: Any,
    ) -> None:
        media_type = content_type or mimetype or "text/html"
        super().__init__(
            content=response if response is not None else b"",
            status_code=status,
            headers=headers,
            media_type=media_type,
        )

    # Flask compat — ``response.headers["X"] = "Y"`` already works via
    # Starlette's MutableHeaders, no shim needed.


# ═══════════════════════════════════════════════════════════════════════════════
# send_file — Flask ``send_file`` → Starlette ``FileResponse``
# ═══════════════════════════════════════════════════════════════════════════════
def send_file(
    file_or_path: Any,
    mimetype: str | None = None,
    as_attachment: bool = False,
    download_name: str | None = None,
    **_kw: Any,
) -> Response:
    """Replacement for ``flask.send_file`` using Starlette ``FileResponse``.

    Also accepts ``io.BytesIO`` objects (in-memory content).
    """
    import io

    if isinstance(file_or_path, io.BytesIO):
        file_or_path.seek(0)
        content = file_or_path.read()
        media_type = mimetype or "application/octet-stream"
        resp_headers: dict[str, str] = {}
        if as_attachment and download_name:
            resp_headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
        return Response(response=content, status=200, mimetype=media_type, headers=resp_headers)

    # File path → FileResponse
    path_str = str(file_or_path)
    filename = download_name or Path(path_str).name
    resp_kwargs: dict[str, Any] = {"path": path_str, "media_type": mimetype or "application/octet-stream"}
    if as_attachment:
        resp_kwargs["filename"] = filename
    return FileResponse(**resp_kwargs)  # type: ignore[return-value]


# ═══════════════════════════════════════════════════════════════════════════════
# redirect / url_for
# ═══════════════════════════════════════════════════════════════════════════════
def redirect(location: str, code: int = 302) -> RedirectResponse:
    return RedirectResponse(url=location, status_code=code)


def url_for(name: str, **values: Any) -> str:
    """Minimal ``url_for`` that maps known route names to paths."""
    _NAMES = {
        "login_handler": "/login",
        "logout_handler": "/logout",
        "serve_index": "/",
    }
    base = _NAMES.get(name, f"/{name}")
    if values:
        return f"{base}?{urlencode(values)}"
    return base


# ═══════════════════════════════════════════════════════════════════════════════
# render_template_string
# ═══════════════════════════════════════════════════════════════════════════════
def render_template_string(source: str, **context: Any) -> HTMLResponse:
    from jinja2 import Template

    return HTMLResponse(Template(source).render(**context))


# ═══════════════════════════════════════════════════════════════════════════════
# Request proxy — contextvars-based replacement for Flask's thread-local
# ═══════════════════════════════════════════════════════════════════════════════
_request_ctx: contextvars.ContextVar[StarletteRequest | None] = contextvars.ContextVar(
    "_flask_compat_request",
    default=None,
)
_form_data_cache: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "_flask_compat_form_data",
    default=None,
)


class _RequestProxy:
    """Lazy proxy that mirrors ``flask.request`` interface."""

    @property
    def _req(self) -> StarletteRequest | None:
        return _request_ctx.get()

    # --- identity ---
    @property
    def method(self) -> str:
        r = self._req
        return r.method if r else "GET"

    @property
    def path(self) -> str:
        r = self._req
        return r.url.path if r else "/"

    @property
    def remote_addr(self) -> str | None:
        r = self._req
        if r and r.client:
            return r.client.host
        return None

    @property
    def headers(self) -> Any:
        r = self._req
        return r.headers if r else {}

    @property
    def cookies(self) -> dict[str, str]:
        r = self._req
        return dict(r.cookies) if r else {}

    # --- body helpers ---
    @property
    def is_json(self) -> bool:
        r = self._req
        if not r:
            return False
        ct = r.headers.get("content-type", "")
        return "application/json" in ct

    @property
    def data(self) -> bytes:
        r = self._req
        if not r:
            return b""
        # NOTE: body may have been consumed already; see _body_cache
        return getattr(r, "_body", b"")

    @property
    def json(self) -> Any:
        """Cached JSON body (synchronous, like Flask)."""
        r = self._req
        if not r:
            return None
        body = getattr(r, "_body", None)
        if body is None:
            return None
        try:
            return json.loads(body)
        except Exception:
            return None

    async def get_json(self) -> dict[str, Any]:
        r = self._req
        if not r:
            return {}
        try:
            return await r.json()
        except Exception:
            return {}

    # --- query string ---
    @property
    def args(self) -> QueryParams:
        r = self._req
        return r.query_params if r else QueryParams()

    # --- form / files (async, call once then cache) ---
    async def _ensure_form(self) -> dict[str, Any]:
        cached = _form_data_cache.get()
        if cached is not None:
            return cached
        r = self._req
        if not r:
            return {}
        form = await r.form()
        result: dict[str, Any] = {}
        for key in form.keys():
            vals = form.getlist(key)
            result[key] = vals if len(vals) > 1 else vals[0] if vals else None
        _form_data_cache.set(result)
        return result

    @property
    def form(self) -> _FormAccessor:
        return _FormAccessor()

    @property
    def files(self) -> _FormAccessor:
        return _FormAccessor(files=True)


class _FormAccessor:
    """Lazy form/file accessor mimicking ``flask.request.form`` / ``request.files``."""

    def __init__(self, *, files: bool = False) -> None:
        self._files = files

    def get(self, key: str, default: Any = None) -> Any:
        """Synchronous get — works only after form has been loaded."""
        cached = _form_data_cache.get()
        if cached is None:
            return default
        val = cached.get(key)
        if val is None:
            return default
        return val

    def getlist(self, key: str) -> list[Any]:
        cached = _form_data_cache.get()
        if cached is None:
            return []
        val = cached.get(key)
        if val is None:
            return []
        return val if isinstance(val, list) else [val]

    def __contains__(self, key: str) -> bool:
        cached = _form_data_cache.get()
        if cached is None:
            return False
        return key in cached


request = _RequestProxy()


# ═══════════════════════════════════════════════════════════════════════════════
# Session proxy — replaces Flask's signed-cookie session
# ═══════════════════════════════════════════════════════════════════════════════
_SESSION_COOKIE_NAME = "session_"
_session_data: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "_flask_compat_session",
    default=None,
)
_session_dirty: contextvars.ContextVar[bool] = contextvars.ContextVar("_flask_compat_session_dirty", default=False)


def _get_session() -> dict[str, Any]:
    data = _session_data.get()
    return {} if data is None else data


class _SessionProxy:
    def get(self, key: str, default: Any = None) -> Any:
        return _get_session().get(key, default)

    def __getitem__(self, key: str) -> Any:
        return _get_session()[key]

    def __setitem__(self, key: str, value: Any) -> None:
        data = dict(_get_session())
        data[key] = value
        _session_data.set(data)
        _session_dirty.set(True)

    def __delitem__(self, key: str) -> None:
        data = dict(_get_session())
        del data[key]
        _session_data.set(data)
        _session_dirty.set(True)

    def pop(self, key: str, default: Any = None) -> Any:
        data = dict(_get_session())
        val = data.pop(key, default)
        _session_data.set(data)
        _session_dirty.set(True)
        return val

    def __contains__(self, key: str) -> bool:
        return key in _get_session()

    def __bool__(self) -> bool:
        return bool(_get_session())


session = _SessionProxy()


def _load_session_from_cookies(starlette_request: StarletteRequest) -> None:
    """Decode session cookie and populate the context var."""
    import itsdangerous

    cookie_name = _SESSION_COOKIE_NAME
    raw = starlette_request.cookies.get(cookie_name, "")
    if not raw:
        _session_data.set({})
        return
    try:
        signer = itsdangerous.TimestampSigner(SESSION_SECRET)
        payload = signer.unsign(raw, max_age=86400)
        data = json.loads(payload)
        _session_data.set(data if isinstance(data, dict) else {})
    except Exception:
        _session_data.set({})


def _save_session_to_cookies(response: StarletteResponse) -> None:
    """Sign session data and set cookie on the response."""
    import itsdangerous

    if not _session_dirty.get():
        return
    data = _session_data.get()
    if data:
        signer = itsdangerous.TimestampSigner(SESSION_SECRET)
        payload = signer.sign(json.dumps(data).encode())
        response.set_cookie(
            _SESSION_COOKIE_NAME,
            payload.decode(),
            httponly=True,
            samesite="lax",
            max_age=86400,
        )
    else:
        response.delete_cookie(_SESSION_COOKIE_NAME)


def get_session_from_environ(environ: dict[str, Any]) -> dict[str, Any]:
    """Decode session from WSGI/Socket.IO environ dict.

    Used by Socket.IO connect handlers that receive raw environ.
    """
    import itsdangerous

    raw_cookie = environ.get("HTTP_COOKIE", "")
    for part in raw_cookie.split(";"):
        part = part.strip()
        if part.startswith(_SESSION_COOKIE_NAME):
            raw = part.split("=", 1)[1]
            try:
                signer = itsdangerous.TimestampSigner(SESSION_SECRET)
                payload = signer.unsign(raw, max_age=86400)
                return json.loads(payload)
            except Exception:
                return {}
    return {}


# ═══════════════════════════════════════════════════════════════════════════════
# UploadFile → FileStorage adapter
# ═══════════════════════════════════════════════════════════════════════════════
class UploadFileAdapter:
    """Wraps FastAPI/Starlette ``UploadFile`` with a ``FileStorage``-like interface."""

    def __init__(self, upload_file: Any) -> None:
        self._uf = upload_file
        self._cached_content: bytes | None = None

    @property
    def filename(self) -> str | None:
        return self._uf.filename

    @property
    def content_type(self) -> str | None:
        return self._uf.content_type

    @property
    def stream(self) -> Any:
        return self

    def read(self, size: int = -1) -> bytes:
        if self._cached_content is None:
            raise RuntimeError("Call `await read_async()` first or use `await file.read()`")
        if size < 0:
            return self._cached_content
        return self._cached_content[:size]

    async def read_async(self) -> bytes:
        if self._cached_content is None:
            data = await self._uf.read()
            self._cached_content = data
            return data
        return self._cached_content

    def save(self, dst: Any) -> None:
        """Save file content to destination (path or file-like)."""
        import io as _io

        if self._cached_content is None:
            raise RuntimeError("Call `await read_async()` before save()")
        if isinstance(dst, str):
            with open(dst, "wb") as f:
                f.write(self._cached_content)
        elif isinstance(dst, _io.IOBase):
            dst.write(self._cached_content)
        elif hasattr(dst, "write"):
            dst.write(self._cached_content)


# ═══════════════════════════════════════════════════════════════════════════════
# secure_filename (from werkzeug, tiny re-implementation)
# ═══════════════════════════════════════════════════════════════════════════════
def secure_filename(filename: str) -> str:
    """Minimal re-implementation of ``werkzeug.utils.secure_filename``."""
    import re

    filename = filename.replace("\\", "/").split("/")[-1]
    filename = re.sub(r"[^\w.\-]", "_", filename)
    filename = filename.strip("._")
    return filename or "unnamed"
