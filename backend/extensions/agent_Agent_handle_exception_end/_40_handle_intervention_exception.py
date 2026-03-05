from datetime import datetime, timezone

from backend.core.agent import LoopData
from backend.utils import errors
from backend.utils.errors import InterventionException
from backend.utils.extension import Extension
from backend.utils.localization import Localization
from backend.utils.print_style import PrintStyle


class HandleInterventionException(Extension):
    async def execute(self, data: dict = {}, **kwargs):
        if not self.agent:
            return

        if not data.get("exception"):
            return

        if isinstance(data["exception"], InterventionException):
            data["exception"] = None  # skip the exception and continue message loop
