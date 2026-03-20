from ctxai.agent import AgentContext
from ctxai.api.message import Message
from ctxai.helpers.defer import DeferredTask


class MessageAsync(Message):
    async def respond(self, task: DeferredTask, context: AgentContext):
        return {
            "message": "Message received.",
            "context": context.id,
        }
