from ctxai.agent import LoopData
from ctxai.helpers.extension import Extension
from ctxai.plugins._infection_check.helpers.checker import get_checker


class InfectionAnalyzeEnd(Extension):
    async def execute(self, loop_data: LoopData | None = None, **kwargs):
        if loop_data is None:
            loop_data = LoopData()
        if not self.agent:
            return
        get_checker(self.agent).start_analysis(self.agent)
