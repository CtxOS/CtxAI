from ctxai.helpers import subagents
from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Input
from ctxai.helpers.api import Output
from ctxai.helpers.api import Request


class Agents(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        action = input.get("action", "")

        try:
            if action == "list":
                data = subagents.get_all_agents_list()
            else:
                raise Exception("Invalid action")

            return {
                "ok": True,
                "data": data,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }
