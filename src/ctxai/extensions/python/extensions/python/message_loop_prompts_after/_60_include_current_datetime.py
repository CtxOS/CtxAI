from datetime import UTC, datetime

from ctxai.core.agent import LoopData
from ctxai.utils.extension import Extension
from ctxai.utils.localization import Localization


class IncludeCurrentDatetime(Extension):
    async def execute(self, loop_data: LoopData | None = None, **kwargs):
        loop_data = loop_data or LoopData()
        if not self.agent:
            return

        # get current datetime
        current_datetime = Localization.get().utc_dt_to_localtime_str(
            datetime.now(UTC), sep=" ", timespec="seconds"
        )
        # remove timezone offset
        if current_datetime and "+" in current_datetime:
            current_datetime = current_datetime.split("+")[0]

        # read prompt
        datetime_prompt = self.agent.read_prompt(
            "agent.system.datetime.md", date_time=current_datetime
        )

        # add current datetime to the loop data
        loop_data.extras_temporary["current_datetime"] = datetime_prompt
