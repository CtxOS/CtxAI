from datetime import datetime, timezone
from ctxai.helpers.extension import Extension
from ctxai.agent import LoopData
from ctxai.helpers.localization import Localization
from ctxai.helpers.errors import InterventionException
from ctxai.helpers import errors
from ctxai.helpers.print_style import PrintStyle


class HandleInterventionException(Extension):
    async def execute(self, data: dict = {}, **kwargs):
        if not self.agent:
            return

        if not data.get("exception"):
            return

        if isinstance(data["exception"], InterventionException):
            data["exception"] = None # skip the exception and continue message loop

        
