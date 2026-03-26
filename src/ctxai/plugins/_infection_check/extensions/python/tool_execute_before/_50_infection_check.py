from ctxai.helpers.extension import Extension
from ctxai.plugins._infection_check.helpers.checker import get_checker


class InfectionAwaitCheck(Extension):
    async def execute(self, tool_name="", tool_args=None, **kwargs):
        if tool_args is None:
            tool_args = {}
        if not self.agent:
            return
        await get_checker(self.agent).gate(self.agent, tool_name=tool_name, tool_args=tool_args)
