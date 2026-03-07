from ctxai.core.agent import LoopData
from ctxai.utils.extension import Extension


class LogForStream(Extension):
    async def execute(self, loop_data: LoopData | None = None, text: str = "", **kwargs):
        loop_data = loop_data or LoopData()
        if not self.agent:
            return

        # create log message and store it in loop data temporary params
        if "log_item_generating" not in loop_data.params_temporary:
            loop_data.params_temporary["log_item_generating"] = self.agent.context.log.log(
                type="agent",
                heading=build_default_heading(self.agent),
            )


def build_heading(agent, text: str, icon: str = "network_intelligence"):
    # Include agent identifier for all agents (CTX:, A1:, A2:, etc.)
    agent_prefix = f"{agent.agent_name}: "
    return f"{agent_prefix}{text}"


def build_default_heading(agent):
    return build_heading(agent, "Calling LLM...")
