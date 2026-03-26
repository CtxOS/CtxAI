from ctxai.agent import LoopData
from ctxai.helpers.extension import Extension


class LogFromStream(Extension):
    async def execute(
        self,
        loop_data: LoopData | None = None,
        text: str = "",
        parsed: dict = None,
        **kwargs,
    ):
        # get log item from loop data temporary params
        if parsed is None:
            parsed = {}
        log_item = loop_data.params_temporary["log_item_generating"]
        if log_item is None:
            return

        # remove step parameter when done
        if log_item.kvps is not None and "step" in log_item.kvps:
            del log_item.kvps["step"]

        # update the log item
        log_item.update(kvps=log_item.kvps)
