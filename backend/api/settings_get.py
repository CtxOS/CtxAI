from backend.utils import settings
from backend.utils.api import ApiHandler, Request, Response


class GetSettings(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        backend = settings.get_settings()
        out = settings.convert_out(backend)
        return dict(out)

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]
