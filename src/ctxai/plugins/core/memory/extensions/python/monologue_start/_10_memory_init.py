# Direct import - this extension lives inside the memory plugin
from ctxai.core.agent import LoopData
from ctxai.plugins.core.memory.helpers import memory
from ctxai.utils.extension import Extension


class MemoryInit(Extension):
    async def execute(self, loop_data: LoopData | None = None, **kwargs):
        loop_data = loop_data or LoopData()
        if not self.agent:
            return

        await memory.Memory.get(self.agent)
