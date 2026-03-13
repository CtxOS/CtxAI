from ctxai.helpers.api import ApiHandler, Request, Response

from ctxai.helpers import process


class Restart(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        process.reload()
        return Response(status=200)
