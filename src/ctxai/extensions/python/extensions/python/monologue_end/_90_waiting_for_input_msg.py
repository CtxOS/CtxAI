from ctxai.core.agent import LoopData
from ctxai.utils.extension import Extension


class WaitingForInputMsg(Extension):
    async def execute(self, loop_data: LoopData | None = None, **kwargs):
        loop_data = loop_data or LoopData()
        if not self.agent:
            return

        # show temp info message
        if self.agent.number == 0:
            self.agent.context.log.set_initial_progress()
