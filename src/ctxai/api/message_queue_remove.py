from ctxai.agent import AgentContext
from ctxai.helpers import message_queue as mq
from ctxai.helpers.api import ApiHandler, Request, Response
from ctxai.helpers.state_monitor_integration import mark_dirty_for_context


class MessageQueueRemove(ApiHandler):
    """Remove message(s) from queue."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        context = AgentContext.get(input.get("context", ""))
        if not context:
            return Response("Context not found", status=404)

        item_id = input.get("item_id")  # None means clear all
        remaining = mq.remove(context, item_id)
        mark_dirty_for_context(context.id, reason="message_queue_remove")

        return {"ok": True, "remaining": remaining}
