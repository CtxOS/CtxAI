from datetime import datetime, timezone
from ctxai.shared.extension import Extension
from ctxai.agent import LoopData
from ctxai.shared.localization import Localization
from ctxai.shared.errors import RepairableException
from ctxai.shared import errors, extension
from ctxai.shared.print_style import PrintStyle

class HandleRepairableException(Extension):
    async def execute(self, data: dict = {}, **kwargs):
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

        
