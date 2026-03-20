from ctxai.agent import AgentContextType
from ctxai.agent import LoopData
from ctxai.helpers import persist_chat
from ctxai.helpers.extension import Extension


class SaveChat(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent:
            return

        # Skip saving BACKGROUND contexts as they should be ephemeral
        if self.agent.context.type == AgentContextType.BACKGROUND:
            return

        persist_chat.save_tmp_chat(self.agent.context)
