from backend.infrastructure.system import process
from backend.utils.api import ApiHandler, Request, Response


class Restart(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        process.reload()
        return Response(status=200)
