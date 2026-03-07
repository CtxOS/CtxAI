from ctxai.core.agent import AgentContext
from ctxai.utils import persist_chat
from ctxai.utils.api import ApiHandler, Input, Output, Request
from ctxai.utils.task_scheduler import TaskScheduler


class RemoveChat(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        ctxid = input.get("context", "")

        scheduler = TaskScheduler.get()
        scheduler.cancel_tasks_by_context(ctxid, terminate_thread=True)

        context = AgentContext.use(ctxid)
        if context:
            # stop processing any tasks
            context.reset()

        AgentContext.remove(ctxid)
        persist_chat.remove_chat(ctxid)

        await scheduler.reload()

        tasks = scheduler.get_tasks_by_context_id(ctxid)
        for task in tasks:
            await scheduler.remove_task_by_uuid(task.uuid)

        # Context removal affects global chat/task lists in all tabs.
        from ctxai.utils.state_monitor_integration import mark_dirty_all

        mark_dirty_all(reason="ctxai.api.routers.chat.chat_remove.RemoveChat")

        return {
            "message": "Context removed.",
        }
