
from backend.utils.errors import InterventionException
from backend.utils.extension import Extension


class HandleInterventionException(Extension):
    async def execute(self, data: dict = {}, **kwargs):
        if not self.agent:
            return

        if not data.get("exception"):
            return

        if isinstance(data["exception"], InterventionException):
            data["exception"] = None  # skip the exception and continue message loop
