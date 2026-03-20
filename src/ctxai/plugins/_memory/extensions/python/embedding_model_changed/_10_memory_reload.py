from ctxai.helpers.extension import Extension
from ctxai.plugins._memory.helpers.memory import reload as memory_reload
# Direct import - this extension lives inside the memory plugin


class MemoryReload(Extension):
    async def execute(self, **kwargs):
        memory_reload()
