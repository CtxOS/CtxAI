from ctxai.shared.extension import Extension
from ctxai.agent import LoopData
from plugins.infection_check.helpers.checker import get_checker


class InfectionAnalyzeEnd(Extension):
    async def execute(self, loop_data=LoopData(), **kwargs):
        if not self.agent:
            return
        get_checker(self.agent).start_analysis(self.agent)
