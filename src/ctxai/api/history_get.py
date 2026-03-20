from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Request
from ctxai.helpers.api import Response


class GetHistory(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("context", [])
        context = self.use_context(ctxid)
        agent = context.streaming_agent or context.agent0
        history = agent.history.output_text()
        size = agent.history.get_tokens()

        return {"history": history, "tokens": size}
