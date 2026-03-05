from datetime import datetime, timezone
from backend.utils.extension import Extension
from backend.core.agent import LoopData
from backend.utils.localization import Localization
from backend.utils.errors import RepairableException
from backend.utils import errors
from backend.utils.print_style import PrintStyle

DATA_NAME_COUNTER = "_plugin.error_retry.critical_exception_counter"

class ResetCriticalExceptionCounter(Extension):
    async def execute(self, exception_data: dict = {}, **kwargs):
        if not self.agent:
            return
        
        self.agent.set_data(DATA_NAME_COUNTER, 0)

        