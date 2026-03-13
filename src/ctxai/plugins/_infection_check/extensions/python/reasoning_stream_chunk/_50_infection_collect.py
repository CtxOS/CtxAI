from ctxai.helpers.extension import Extension
from ctxai.agent import LoopData
from ctxai.plugins._infection_check.helpers.checker import get_checker


class InfectionCollectReasoning(Extension):
    async def execute(self, loop_data=LoopData(), stream_data=None, **kwargs):
        if not self.agent or stream_data is None:
            return
        get_checker(self.agent).collect_reasoning(stream_data.get("full", ""))
