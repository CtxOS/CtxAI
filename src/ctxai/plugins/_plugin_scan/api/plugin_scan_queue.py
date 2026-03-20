from ctxai.agent import AgentContext
from ctxai.helpers import message_queue as mq
from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Input
from ctxai.helpers.api import Output
from ctxai.helpers.api import Request
from ctxai.helpers.api import Response


class PluginScanQueue(ApiHandler):
    """Log the scan prompt into a chat. Optionally set progress to 'Queued'."""

    async def process(self, input: Input, request: Request) -> Output:
        ctxid: str = input.get("context", "")
        text: str = input.get("text", "")
        queued: bool = input.get("queued", False)

        if not ctxid or not text:
            return Response("Missing 'context' or 'text'.", 400)

        context = AgentContext.get(ctxid)
        if context is None:
            return Response(f"Context {ctxid} not found.", 404)

        mq.log_user_message(context, text, [])

        if queued:
            context.log.set_progress("icon://hourglass_empty Queued - waiting for another scan to finish", 0, True)

        return {"ok": True, "context": ctxid}
