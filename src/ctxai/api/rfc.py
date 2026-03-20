from ctxai.helpers import runtime
from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Request
from ctxai.helpers.api import Response


class RFC(ApiHandler):
    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        result = await runtime.handle_rfc(input)  # type: ignore
        return result
