
from backend.utils import errors
from backend.utils.errors import RepairableException
from backend.utils.extension import Extension
from backend.utils.print_style import PrintStyle


class HandleRepairableException(Extension):
    async def execute(self, data: dict = {}, **kwargs):
        if not self.agent:
            return

        if not data.get("exception"):
            return

        if isinstance(data["exception"], RepairableException):
            msg = {"message": errors.format_error(data["exception"])}
            await self.agent.call_extensions("error_format", msg=msg)
            self.agent.hist_add_warning(msg["message"])
            PrintStyle(font_color="red", padding=True).print(msg["message"])
            self.agent.context.log.log(type="warning", content=msg["message"])
            data["exception"] = None
