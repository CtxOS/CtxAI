from ctxai.utils.extension import Extension

DATA_NAME_COUNTER = "_plugin.error_retry.critical_exception_counter"


class ResetCriticalExceptionCounter(Extension):
    async def execute(self, exception_data: dict = None, **kwargs):
        if exception_data is None:
            exception_data = {}
        if not self.agent:
            return

        self.agent.set_data(DATA_NAME_COUNTER, 0)
