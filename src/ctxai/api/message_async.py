from ctxai.agent import AgentContext
from ctxai.shared.defer import DeferredTask
from api.message import Message


class MessageAsync(Message):
    async def respond(self, task: DeferredTask, context: AgentContext):
        return {
            "message": "Message received.",
            "context": context.id,
        }
