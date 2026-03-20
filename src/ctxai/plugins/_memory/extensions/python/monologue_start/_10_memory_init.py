from ctxai.agent import LoopData
from ctxai.helpers.extension import Extension
from ctxai.plugins._memory.helpers import memory

# Direct import - this extension lives inside the memory plugin


class MemoryInit(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent:
            return

        db = await memory.Memory.get(self.agent)
