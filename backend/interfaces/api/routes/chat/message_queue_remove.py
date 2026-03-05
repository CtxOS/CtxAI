from backend.core.agent import AgentContext
from backend.utils import message_queue as mq
from backend.utils.api import ApiHandler, Request, Response
from backend.utils.state_monitor_integration import mark_dirty_for_context


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
