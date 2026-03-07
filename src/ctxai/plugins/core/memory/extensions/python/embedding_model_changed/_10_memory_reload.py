# Direct import - this extension lives inside the memory plugin
from ctxai.plugins.core.memory.helpers.memory import (
    reload as memory_reload,
)
from ctxai.utils.extension import Extension


class MemoryReload(Extension):
    async def execute(self, **kwargs):
        memory_reload()
