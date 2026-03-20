from ctxai.helpers import persist_chat
from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Input
from ctxai.helpers.api import Output
from ctxai.helpers.api import Request


class LoadChats(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        chats = input.get("chats", [])
        if not chats:
            raise Exception("No chats provided")

        ctxids = persist_chat.load_json_chats(chats)

        return {
            "message": "Chats loaded.",
            "ctxids": ctxids,
        }
