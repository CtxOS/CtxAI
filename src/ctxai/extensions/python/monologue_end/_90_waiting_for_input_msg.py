from ctxai.agent import LoopData
from ctxai.helpers.extension import Extension


class WaitingForInputMsg(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent:
            return

        # show temp info message
        if self.agent.number == 0:
            self.agent.context.log.set_initial_progress()
