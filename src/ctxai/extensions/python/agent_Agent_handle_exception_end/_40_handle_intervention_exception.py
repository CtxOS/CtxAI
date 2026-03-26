from ctxai.helpers.errors import InterventionException
from ctxai.helpers.extension import Extension


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
