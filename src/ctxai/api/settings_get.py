from ctxai.helpers import settings
from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Request
from ctxai.helpers.api import Response


class GetSettings(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        backend = settings.get_settings()
        out = settings.convert_out(backend)
        return dict(out)

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]
