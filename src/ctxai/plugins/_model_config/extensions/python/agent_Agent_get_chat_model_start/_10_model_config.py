from helpers.extension import Extension
from plugins._model_config.helpers.model_config import build_chat_model


class ChatModelProvider(Extension):
    def execute(self, data: dict = None, **kwargs):
        if data is None:
            data = {}
        if self.agent:
            data["result"] = build_chat_model(self.agent)
