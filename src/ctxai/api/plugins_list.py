from ctxai.helpers import plugins
from ctxai.helpers.api import ApiHandler
from ctxai.helpers.api import Input
from ctxai.helpers.api import Output
from ctxai.helpers.api import Request


class PluginsList(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        filter = input.get("filter", {})

        custom = filter.get("custom", False)
        builtin = filter.get("builtin", False)

        plugin_list = plugins.get_enhanced_plugins_list(custom=custom, builtin=builtin)

        return {"ok": True, "plugins": [p.model_dump(mode="json") for p in plugin_list]}
