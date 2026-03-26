from ctxai.helpers.extension import Extension
from ctxai.helpers.print_style import PrintStyle
from ctxai.helpers.state_monitor import _ws_debug_enabled, get_state_monitor


class StateSync(Extension):
    async def execute(self, instance=None, sid: str = "", **kwargs):
        if instance is None:
            return

        get_state_monitor().unregister_sid(instance.namespace, sid)
        if _ws_debug_enabled():
            PrintStyle.debug(f"[WebuiHandler] disconnect sid={sid}")
