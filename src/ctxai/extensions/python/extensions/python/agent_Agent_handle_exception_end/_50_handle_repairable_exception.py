from ctxai.utils import errors, extension
from ctxai.utils.errors import RepairableException
from ctxai.utils.extension import Extension
from ctxai.utils.print_style import PrintStyle


class HandleRepairableException(Extension):
    async def execute(self, data: dict = None, **kwargs):
        if data is None:
            data = {}
        if not self.agent:
            return

        if not data.get("exception"):
            return

        if isinstance(data["exception"], RepairableException):
            msg = {"message": errors.format_error(data["exception"])}
            await extension.call_extensions_async("error_format", agent=self.agent, msg=msg)
            self.agent.hist_add_warning(msg["message"])
            PrintStyle(font_color="red", padding=True).print(msg["message"])
            self.agent.context.log.log(type="warning", content=msg["message"])
            data["exception"] = None
