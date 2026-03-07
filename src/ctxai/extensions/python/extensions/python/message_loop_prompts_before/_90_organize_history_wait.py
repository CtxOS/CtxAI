from extensions.python.message_loop_end._10_organize_history import DATA_NAME_TASK

from ctxai.core.agent import LoopData
from ctxai.utils.defer import DeferredTask
from ctxai.utils.extension import Extension


class OrganizeHistoryWait(Extension):
    async def execute(self, loop_data: LoopData | None = None, **kwargs):
        loop_data = loop_data or LoopData()
        if not self.agent:
            return

        # sync action only required if the history is too large, otherwise leave it in background
        while self.agent.history.is_over_limit():
            # get task
            task: DeferredTask | None = self.agent.get_data(DATA_NAME_TASK)

            # Check if the task is already done
            if task:
                if not task.is_ready():
                    self.agent.context.log.set_progress("Compressing history...")

                # Wait for the task to complete
                await task.result()

                # Clear the coroutine data after it's done
                self.agent.set_data(DATA_NAME_TASK, None)
            else:
                # no task was running, start and wait
                self.agent.context.log.set_progress("Compressing history...")
                await self.agent.history.compress()
