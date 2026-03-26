from ctxai.agent import LoopData
from ctxai.helpers.extension import Extension


class CodeExecutionPrompt(Extension):
    async def execute(
        self,
        system_prompt: list[str] = None,
        loop_data: LoopData | None = None,
        **kwargs,
    ):
        if system_prompt is None:
            system_prompt = []
        if not self.agent:
            return

        system_prompt.append(self.agent.read_prompt("agent.system.tool.code_exe.md"))
        system_prompt.append(self.agent.read_prompt("agent.system.tool.input.md"))
