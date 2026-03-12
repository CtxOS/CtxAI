from ctxai.shared.api import ApiHandler, Request, Response
from ctxai.shared import message_queue as mq
from ctxai.agent import AgentContext
from ctxai.shared.state_monitor_integration import mark_dirty_for_context


class MessageQueueAdd(ApiHandler):
    """Add a message to the queue."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        context = AgentContext.get(input.get("context", ""))
        if not context:
            return Response("Context not found", status=404)

        text = input.get("text", "").strip()
        attachments = input.get("attachments", [])  # filenames from /upload API
        item_id = input.get("item_id")

        if not text and not attachments:
            return Response("Empty message", status=400)

        item = mq.add(context, text, attachments, item_id)
        mark_dirty_for_context(context.id, reason="message_queue_add")
        return {"ok": True, "item_id": item["id"], "queue_length": len(mq.get_queue(context))}
