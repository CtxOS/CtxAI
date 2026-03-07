from ctxai.utils.errors import InterventionException
from ctxai.utils.extension import Extension


class HandleInterventionException(Extension):
    async def execute(self, data: dict = None, **kwargs):
        if data is None:
            data = {}
        if not self.agent:
            return

        if not data.get("exception"):
            return

        if isinstance(data["exception"], InterventionException):
            data["exception"] = None  # skip the exception and continue message loop
