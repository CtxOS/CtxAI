from ctxai.agent import AgentContext
from ctxai.helpers.defer import DeferredTask
from ctxai.api.message import Message


class MessageAsync(Message):
    async def respond(self, task: DeferredTask, context: AgentContext):
        return {
            "message": "Message received.",
            "context": context.id,
        }
