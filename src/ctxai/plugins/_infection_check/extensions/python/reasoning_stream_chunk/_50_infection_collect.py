from ctxai.agent import LoopData
from ctxai.helpers.extension import Extension
from ctxai.plugins._infection_check.helpers.checker import get_checker


class InfectionCollectReasoning(Extension):
    async def execute(self, loop_data: LoopData | None = None, stream_data=None, **kwargs):
        if loop_data is None:
            loop_data = LoopData()
        if not self.agent or stream_data is None:
            return
        get_checker(self.agent).collect_reasoning(stream_data.get("full", ""))
