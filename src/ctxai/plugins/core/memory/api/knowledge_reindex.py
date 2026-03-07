from ctxai.plugins.core.memory.helpers.memory import Memory
from ctxai.utils.api import ApiHandler, Request, Response


class ReindexKnowledge(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("ctxid", "")
        if not ctxid:
            raise Exception("No context id provided")
        context = self.use_context(ctxid)

        # reload memory to re-import knowledge
        await Memory.reload(context.agent0)
        context.log.set_initial_progress()

        return {
            "ok": True,
            "message": "Knowledge re-indexed",
        }
