from datetime import datetime, timezone
from ctxai.shared.extension import Extension
from ctxai.agent import LoopData
from ctxai.shared.localization import Localization
from ctxai.shared.errors import RepairableException
from ctxai.shared import errors
from ctxai.shared.print_style import PrintStyle

DATA_NAME_COUNTER = "_plugin.error_retry.critical_exception_counter"

class ResetCriticalExceptionCounter(Extension):
    async def execute(self, exception_data: dict = {}, **kwargs):
        if not self.agent:
            return
        
        self.agent.set_data(DATA_NAME_COUNTER, 0)

        