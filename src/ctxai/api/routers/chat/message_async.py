from ctxai.api.routers.chat.message import Message
from ctxai.core.agent import AgentContext
from ctxai.utils.defer import DeferredTask


class MessageAsync(Message):
    async def respond(self, task: DeferredTask, context: AgentContext):
        return {
            "message": "Message received.",
            "context": context.id,
        }
