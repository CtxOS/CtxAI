from ctxai.shared.api import ApiHandler, Request, Response

from ctxai.shared import process

class Restart(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        process.reload()
        return Response(status=200)