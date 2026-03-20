from helpers.extension import Extension
from plugins._model_config.helpers.model_config import build_browser_model


class BrowserModelProvider(Extension):
    def execute(self, data: dict = None, **kwargs):
        if data is None:
            data = {}
        if self.agent:
            data["result"] = build_browser_model(self.agent)
