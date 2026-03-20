from ctxai.agent import LoopData
from ctxai.helpers import plugins
from ctxai.helpers.extension import Extension
from ctxai.plugins._memory.extensions.python.message_loop_prompts_after._50_recall_memories import (
    DATA_NAME_ITER as DATA_NAME_ITER_MEMORIES,
)
from ctxai.plugins._memory.extensions.python.message_loop_prompts_after._50_recall_memories import (
    DATA_NAME_TASK as DATA_NAME_TASK_MEMORIES,
)


class RecallWait(Extension):
    async def execute(self, loop_data: LoopData | None = None, **kwargs):
        if not self.agent:
            return

        set = plugins.get_plugin_config("_memory", self.agent)
        if not set:
            return None

        task = self.agent.get_data(DATA_NAME_TASK_MEMORIES)
        iter = self.agent.get_data(DATA_NAME_ITER_MEMORIES) or 0

        if task and not task.done():
            # if memory recall is set to delayed mode, do not await on the iteration it was called
            if set["memory_recall_delayed"]:
                if iter == loop_data.iteration:
                    # insert info about delayed memory to extras
                    delay_text = self.agent.read_prompt("memory.recall_delay_msg.md")
                    loop_data.extras_temporary["memory_recall_delayed"] = delay_text
                    return

            # otherwise await the task
            await task
