from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Request
from ctxai.helpers.api import Response
from ctxai.plugins._memory.helpers.memory import Memory


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
