from ctxai.helpers.extension import Extension
from ctxai.agent import LoopData

# Direct import - this extension lives inside the memory plugin
from ctxai.plugins._memory.helpers import memory


class MemoryInit(Extension):

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent:
            return

        db = await memory.Memory.get(self.agent)
