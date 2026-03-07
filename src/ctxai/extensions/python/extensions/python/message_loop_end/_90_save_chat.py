from ctxai.core.agent import AgentContextType, LoopData
from ctxai.utils import persist_chat
from ctxai.utils.extension import Extension


class SaveChat(Extension):
    async def execute(self, loop_data: LoopData | None = None, **kwargs):
        loop_data = loop_data or LoopData()
        if not self.agent:
            return

        # Skip saving BACKGROUND contexts as they should be ephemeral
        if self.agent.context.type == AgentContextType.BACKGROUND:
            return

        persist_chat.save_tmp_chat(self.agent.context)
