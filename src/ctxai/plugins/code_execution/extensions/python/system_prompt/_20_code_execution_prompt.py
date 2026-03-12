from ctxai.shared.extension import Extension
from ctxai.agent import LoopData


class CodeExecutionPrompt(Extension):

    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs,
    ):
        system_prompt.append(self.agent.read_prompt("agent.system.tool.code_exe.md"))
        system_prompt.append(self.agent.read_prompt("agent.system.tool.input.md"))
