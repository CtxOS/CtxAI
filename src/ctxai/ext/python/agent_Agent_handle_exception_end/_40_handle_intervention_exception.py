from datetime import datetime, timezone
from ctxai.shared.extension import Extension
from ctxai.agent import LoopData
from ctxai.shared.localization import Localization
from ctxai.shared.errors import InterventionException
from ctxai.shared import errors
from ctxai.shared.print_style import PrintStyle


class HandleInterventionException(Extension):
    async def execute(self, data: dict = {}, **kwargs):
        if not self.agent:
            return

        if not data.get("exception"):
            return

        if isinstance(data["exception"], InterventionException):
            data["exception"] = None # skip the exception and continue message loop

        
