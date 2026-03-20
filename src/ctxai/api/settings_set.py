from typing import Any

from ctxai.helpers import settings
from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Request
from ctxai.helpers.api import Response


class SetSettings(ApiHandler):
    async def process(self, input: dict[Any, Any], request: Request) -> dict[Any, Any] | Response:
        frontend = input.get("settings", input)
        backend = settings.convert_in(settings.Settings(**frontend))  # type: ignore[typeddict-item]
        backend = settings.set_settings(backend)
        out = settings.convert_out(backend)
        return dict(out)
