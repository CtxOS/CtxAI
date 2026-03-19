import asyncio
import random
import string
import threading

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Coroutine, Dict
from enum import Enum
import ctxai.models as models

from ctxai.helpers import (
    files,
    history,
    context as context_helper,
    subagents,
)
from ctxai.helpers import extension
from ctxai.helpers.print_style import PrintStyle

from langchain_core.messages import BaseMessage

import ctxai.helpers.log as Log
from ctxai.helpers.dirty_json import DirtyJson
from ctxai.helpers.defer import DeferredTask
from typing import Callable
from ctxai.helpers.localization import Localization
from ctxai.helpers.errors import InterventionException


class AgentContextType(Enum):
    USER = "user"
    TASK = "task"
    BACKGROUND = "background"


# Maximum number of concurrent agent contexts before eviction kicks in.
# Oldest non-running contexts are evicted first.
MAX_CONTEXTS = 64

# Maximum concurrent agent execution threads.
MAX_CONCURRENT_TASKS = 16


class AgentContext:
    _contexts: OrderedDict[str, "AgentContext"] = OrderedDict()
    _contexts_lock = threading.RLock()
    _counter: int = 0
    _notification_manager = None
    _task_semaphore = threading.Semaphore(MAX_CONCURRENT_TASKS)

    @extension.extensible
    def __init__(
        self,
        config: "AgentConfig",
        id: str | None = None,
        name: str | None = None,
        agent0: "Agent|None" = None,
        log: Log.Log | None = None,
        paused: bool = False,
        streaming_agent: "Agent|None" = None,
        created_at: datetime | None = None,
        type: AgentContextType = AgentContextType.USER,
        last_message: datetime | None = None,
        data: dict | None = None,
        output_data: dict | None = None,
        set_current: bool = False,
    ):
        # initialize context
        self.id = id or AgentContext.generate_id()
        existing = None
        with AgentContext._contexts_lock:
            existing = AgentContext._contexts.pop(self.id, None)
            AgentContext._contexts[self.id] = self
            # Evict oldest non-running contexts if over capacity
            AgentContext._evict_overflow()
        if existing and existing.task:
            existing.task.kill()
        if set_current:
            AgentContext.set_current(self.id)

        # initialize state
        self.name = name
        self.config = config
        self.data = data or {}
        self.output_data = output_data or {}
        self.log = log or Log.Log()
        self.log.context = self
        self.trace_id = self.log.guid  # correlation ID for observability
        self.paused = paused
        self.streaming_agent = streaming_agent
        self.task: DeferredTask | None = None
        self.created_at = created_at or datetime.now(timezone.utc)
        self.type = type
        AgentContext._counter += 1
        self.no = AgentContext._counter
        self.last_message = last_message or datetime.now(timezone.utc)

        # initialize agent at last (context is complete now)
        self.agent0 = agent0 or Agent(0, self.config, self)

    @staticmethod
    def get(id: str):
        with AgentContext._contexts_lock:
            return AgentContext._contexts.get(id, None)

    @staticmethod
    def use(id: str):
        context = AgentContext.get(id)
        if context:
            AgentContext.set_current(id)
        else:
            AgentContext.set_current("")
        return context

    @staticmethod
    def current():
        ctxid = context_helper.get_context_data("agent_context_id", "")
        if not ctxid:
            return None
        return AgentContext.get(ctxid)

    @staticmethod
    def set_current(ctxid: str):
        context_helper.set_context_data("agent_context_id", ctxid)

    @staticmethod
    def first():
        with AgentContext._contexts_lock:
            if not AgentContext._contexts:
                return None
            return list(AgentContext._contexts.values())[0]

    @staticmethod
    def all():
        with AgentContext._contexts_lock:
            return list(AgentContext._contexts.values())

    @staticmethod
    def generate_id():
        def generate_short_id():
            return "".join(random.choices(string.ascii_letters + string.digits, k=8))

        while True:
            short_id = generate_short_id()
            with AgentContext._contexts_lock:
                if short_id not in AgentContext._contexts:
                    return short_id

    @staticmethod
    def _evict_overflow():
        """Evict oldest non-running contexts when capacity is exceeded.

        Must be called while holding ``_contexts_lock``.
        """
        while len(AgentContext._contexts) > MAX_CONTEXTS:
            evicted = None
            # Walk from oldest to newest; prefer evicting non-running contexts
            for ctx_id, ctx in AgentContext._contexts.items():
                if not ctx.is_running():
                    evicted = ctx_id
                    break
            # If every context is running, evict the oldest regardless
            if evicted is None:
                evicted = next(iter(AgentContext._contexts))
            context = AgentContext._contexts.pop(evicted, None)
            if context and context.task:
                context.task.kill()

    @classmethod
    def get_notification_manager(cls):
        if cls._notification_manager is None:
            from ctxai.helpers.notification import NotificationManager  # type: ignore

            cls._notification_manager = NotificationManager()
        return cls._notification_manager

    @staticmethod
    @extension.extensible
    def remove(id: str):
        with AgentContext._contexts_lock:
            context = AgentContext._contexts.pop(id, None)
        if context and context.task:
            context.task.kill()
        return context

    def get_data(self, key: str, recursive: bool = True):
        # recursive is not used now, prepared for context hierarchy
        return self.data.get(key, None)

    def set_data(self, key: str, value: Any, recursive: bool = True):
        # recursive is not used now, prepared for context hierarchy
        self.data[key] = value

    def get_output_data(self, key: str, recursive: bool = True):
        # recursive is not used now, prepared for context hierarchy
        return self.output_data.get(key, None)

    def set_output_data(self, key: str, value: Any, recursive: bool = True):
        # recursive is not used now, prepared for context hierarchy
        self.output_data[key] = value

    @extension.extensible
    def output(self):
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "name": self.name,
            "created_at": (
                Localization.get().serialize_datetime(self.created_at)
                if self.created_at
                else Localization.get().serialize_datetime(datetime.fromtimestamp(0))
            ),
            "no": self.no,
            "log_guid": self.log.guid,
            "log_version": len(self.log.updates),
            "log_length": len(self.log.logs),
            "paused": self.paused,
            "last_message": (
                Localization.get().serialize_datetime(self.last_message)
                if self.last_message
                else Localization.get().serialize_datetime(datetime.fromtimestamp(0))
            ),
            "type": self.type.value,
            "running": self.is_running(),
            **self.output_data,
        }

    @staticmethod
    def log_to_all(
        type: Log.Type,
        heading: str | None = None,
        content: str | None = None,
        kvps: dict | None = None,
        update_progress: Log.ProgressUpdate | None = None,
        id: str | None = None,  # Add id parameter
        **kwargs,
    ) -> list[Log.LogItem]:
        items: list[Log.LogItem] = []
        for context in AgentContext.all():
            items.append(context.log.log(type, heading, content, kvps, update_progress, id, **kwargs))
        return items

    @extension.extensible
    def kill_process(self):
        if self.task:
            self.task.kill()

    @extension.extensible
    def reset(self):
        self.kill_process()
        self.log.reset()
        self.agent0 = Agent(0, self.config, self)
        self.streaming_agent = None
        self.paused = False

    @extension.extensible
    def nudge(self):
        self.kill_process()
        self.paused = False
        self.task = self.communicate(UserMessage(self.agent0.read_prompt("fw.msg_nudge.md")))
        return self.task

    @extension.extensible
    def get_agent(self):
        return self.streaming_agent or self.agent0

    def is_running(self) -> bool:
        return (self.task and self.task.is_alive()) or False

    @extension.extensible
    def communicate(self, msg: "UserMessage", broadcast_level: int = 1):
        self.paused = False  # unpause if paused

        current_agent = self.get_agent()

        if self.task and self.task.is_alive():
            # set intervention messages to agent(s):
            intervention_agent = current_agent
            while intervention_agent and broadcast_level != 0:
                intervention_agent.intervention = msg
                broadcast_level -= 1
                intervention_agent = intervention_agent.data.get(Agent.DATA_NAME_SUPERIOR, None)
        else:
            self.task = self.run_task(self._process_chain, current_agent, msg)

        return self.task

    @extension.extensible
    def run_task(self, func: Callable[..., Coroutine[Any, Any, Any]], *args: Any, **kwargs: Any):
        if not self.task:
            self.task = DeferredTask(
                thread_name=self.__class__.__name__,
            )

        async def _guarded(*a: Any, **kw: Any) -> Any:
            AgentContext._task_semaphore.acquire()
            try:
                return await func(*a, **kw)
            finally:
                AgentContext._task_semaphore.release()

        self.task.start_task(_guarded, *args, **kwargs)
        return self.task

    # this wrapper ensures that superior agents are called back if the chat was loaded from file and original callstack is gone
    @extension.extensible
    async def _process_chain(self, agent: "Agent", msg: "UserMessage|str", user=True):
        from ctxai.helpers.agent_orchestrator import run_process_chain

        try:
            return await run_process_chain(self, agent, msg, user=user)
        except Exception as e:
            await self.handle_exception("process_chain", e)

    @extension.extensible
    async def handle_exception(self, location: str, exception: Exception):
        if exception:
            raise exception  # exception handling is done by extensions


@dataclass
class AgentConfig:
    chat_model: models.ModelConfig
    utility_model: models.ModelConfig
    embeddings_model: models.ModelConfig
    browser_model: models.ModelConfig
    mcp_servers: str
    profile: str = ""
    knowledge_subdirs: list[str] = field(default_factory=lambda: ["default", "custom"])
    browser_http_headers: dict[str, str] = field(default_factory=dict)  # Custom HTTP headers for browser requests
    additional: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserMessage:
    message: str
    attachments: list[str] = field(default_factory=list[str])
    system_message: list[str] = field(default_factory=list[str])


class LoopData:
    def __init__(self, **kwargs):
        self.iteration = -1
        self.system = []
        self.user_message: history.Message | None = None
        self.history_output: list[history.OutputMessage] = []
        self.extras_temporary: OrderedDict[str, history.MessageContent] = OrderedDict()
        self.extras_persistent: OrderedDict[str, history.MessageContent] = OrderedDict()
        self.last_response = ""
        self.params_temporary: dict = {}
        self.params_persistent: dict = {}
        self.current_tool = None

        # override values with kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


class Agent:
    DATA_NAME_SUPERIOR = "_superior"
    DATA_NAME_SUBORDINATE = "_subordinate"
    DATA_NAME_CTX_WINDOW = "ctx_window"

    @extension.extensible
    def __init__(self, number: int, config: AgentConfig, context: AgentContext | None = None):
        # agent config
        self.config = config

        # agent context
        self.context = context or AgentContext(config=config, agent0=self)

        # non-config vars
        self.number = number
        self.agent_name = f"A{self.number}"

        self.history = history.History(self)  # type: ignore[abstract]
        self.last_user_message: history.Message | None = None
        self.intervention: UserMessage | None = None
        self.data: dict[str, Any] = {}  # free data object all the tools can use

        extension.call_extensions_sync("agent_init", self)

    @extension.extensible
    async def monologue(self):
        """Run the agent's reasoning loop.

        The outer layer (extension hooks, exception handling) stays here.
        The inner message-loop iteration is delegated to
        ``agent_orchestrator.run_monologue``.
        """
        from ctxai.helpers.agent_orchestrator import run_monologue

        while True:
            try:
                return await run_monologue(self)
            except Exception as e:
                await self.handle_exception("monologue", e)
            finally:
                self.context.streaming_agent = None

    @extension.extensible
    async def prepare_prompt(self, loop_data: LoopData) -> list[BaseMessage]:
        from ctxai.helpers.reasoning_engine import build_prompt

        return await build_prompt(self, loop_data)

    @extension.extensible
    async def handle_exception(self, location: str, exception: Exception):
        if exception:
            raise exception  # exception handling is done by extensions

        # exception_data = {"exception": exception}
        # await self.call_extensions(
        #     "message_loop_exception", exception_data=exception_data
        # )

        # # If extensions cleared the exception, continue.
        # if not exception_data.get("exception"):
        #     return

        # # Backwards-compatible fallback (should normally be handled by _90 extension).
        # exception = exception_data["exception"]
        # if isinstance(exception, HandledException):
        #     raise exception
        # elif isinstance(exception, asyncio.CancelledError):
        #     PrintStyle(font_color="white", background_color="red", padding=True).print(
        #         f"Context {self.context.id} terminated during message loop"
        #     )
        #     raise HandledException(exception)

        # else:
        #     error_text = errors.error_text(exception)
        #     error_message = errors.format_error(exception)

        #     # Mask secrets in error messages
        #     PrintStyle(font_color="red", padding=True).print(error_message)
        #     self.context.log.log(
        #         type="error",
        #         content=error_message,
        #     )
        #     PrintStyle(font_color="red", padding=True).print(
        #         f"{self.agent_name}: {error_text}"
        #     )

        #     raise HandledException(exception)  # Re-raise the exception to kill the loop

    @extension.extensible
    async def get_system_prompt(self, loop_data: LoopData) -> list[str]:
        system_prompt: list[str] = []
        await extension.call_extensions_async("system_prompt", self, system_prompt=system_prompt, loop_data=loop_data)
        return system_prompt

    @extension.extensible
    def parse_prompt(self, _prompt_file: str, **kwargs):
        dirs = subagents.get_paths(self, "prompts")

        prompt = files.parse_file(_prompt_file, _directories=dirs, _agent=self, **kwargs)
        return prompt

    @extension.extensible
    def read_prompt(self, file: str, **kwargs) -> str:
        dirs = subagents.get_paths(self, "prompts")

        prompt = files.read_prompt_file(file, _directories=dirs, _agent=self, **kwargs)
        if files.is_full_json_template(prompt):
            prompt = files.remove_code_fences(prompt)
        return prompt

    def get_data(self, field: str):
        return self.data.get(field, None)

    def set_data(self, field: str, value):
        self.data[field] = value

    @extension.extensible
    def hist_add_message(self, ai: bool, content: history.MessageContent, tokens: int = 0):
        self.last_message = datetime.now(timezone.utc)
        # Allow extensions to process content before adding to history
        content_data = {"content": content}
        extension.call_extensions_sync("hist_add_before", self, content_data=content_data, ai=ai)
        return self.history.add_message(ai=ai, content=content_data["content"], tokens=tokens)

    @extension.extensible
    def hist_add_user_message(self, message: UserMessage, intervention: bool = False):
        self.history.new_topic()  # user message starts a new topic in history

        # load message template based on intervention
        if intervention:
            content = self.parse_prompt(
                "fw.intervention.md",
                message=message.message,
                attachments=message.attachments,
                system_message=message.system_message,
            )
        else:
            content = self.parse_prompt(
                "fw.user_message.md",
                message=message.message,
                attachments=message.attachments,
                system_message=message.system_message,
            )

        # remove empty parts from template
        if isinstance(content, dict):
            content = {k: v for k, v in content.items() if v}

        # add to history
        msg = self.hist_add_message(False, content=content)  # type: ignore
        self.last_user_message = msg
        return msg

    @extension.extensible
    def hist_add_ai_response(self, message: str):
        self.loop_data.last_response = message
        content = self.parse_prompt("fw.ai_response.md", message=message)
        return self.hist_add_message(True, content=content)

    @extension.extensible
    def hist_add_warning(self, message: history.MessageContent):
        content = self.parse_prompt("fw.warning.md", message=message)
        return self.hist_add_message(False, content=content)

    @extension.extensible
    def hist_add_tool_result(self, tool_name: str, tool_result: str, **kwargs):
        data = {
            "tool_name": tool_name,
            "tool_result": tool_result,
            **kwargs,
        }
        extension.call_extensions_sync("hist_add_tool_result", self, data=data)
        return self.hist_add_message(False, content=data)

    def concat_messages(self, messages):  # TODO add param for message range, topic, history
        return self.history.output_text(human_label="user", ai_label="assistant")

    @extension.extensible
    def get_chat_model(self):
        return models.get_chat_model(
            self.config.chat_model.provider,
            self.config.chat_model.name,
            model_config=self.config.chat_model,
            **self.config.chat_model.build_kwargs(),
        )

    @extension.extensible
    def get_utility_model(self):
        return models.get_chat_model(
            self.config.utility_model.provider,
            self.config.utility_model.name,
            model_config=self.config.utility_model,
            **self.config.utility_model.build_kwargs(),
        )

    @extension.extensible
    def get_browser_model(self):
        return models.get_browser_model(
            self.config.browser_model.provider,
            self.config.browser_model.name,
            model_config=self.config.browser_model,
            **self.config.browser_model.build_kwargs(),
        )

    @extension.extensible
    def get_embedding_model(self):
        return models.get_embedding_model(
            self.config.embeddings_model.provider,
            self.config.embeddings_model.name,
            model_config=self.config.embeddings_model,
            **self.config.embeddings_model.build_kwargs(),
        )

    @extension.extensible
    async def call_utility_model(
        self,
        system: str,
        message: str,
        callback: Callable[[str], Awaitable[None]] | None = None,
        background: bool = False,
    ):
        from ctxai.helpers.reasoning_engine import call_utility_model

        return await call_utility_model(self, system, message, callback=callback, background=background)

    @extension.extensible
    async def call_chat_model(
        self,
        messages: list[BaseMessage],
        response_callback: Callable[[str, str], Awaitable[None]] | None = None,
        reasoning_callback: Callable[[str, str], Awaitable[None]] | None = None,
        background: bool = False,
        explicit_caching: bool = True,
    ):
        from ctxai.helpers.reasoning_engine import call_chat_model

        return await call_chat_model(
            self,
            messages,
            response_callback=response_callback,
            reasoning_callback=reasoning_callback,
            background=background,
            explicit_caching=explicit_caching,
        )

    @extension.extensible
    async def rate_limiter_callback(self, message: str, key: str, total: int, limit: int):
        # show the rate limit waiting in a progress bar, no need to spam the chat history
        self.context.log.set_progress(message, True)
        return False

    @extension.extensible
    async def handle_intervention(self, progress: str = ""):
        await self.wait_if_paused()
        if self.intervention:  # if there is an intervention message, but not yet processed
            msg = self.intervention
            self.intervention = None  # reset the intervention message
            # If a tool was running, save its progress to history
            last_tool = self.loop_data.current_tool
            if last_tool:
                tool_progress = last_tool.progress.strip()
                if tool_progress:
                    self.hist_add_tool_result(last_tool.name, tool_progress)
                    last_tool.set_progress(None)
            if progress.strip():
                self.hist_add_ai_response(progress)
            # append the intervention message
            self.hist_add_user_message(msg, intervention=True)
            raise InterventionException(msg)

    async def wait_if_paused(self):
        while self.context.paused:
            await asyncio.sleep(0.1)

    @extension.extensible
    async def process_tools(self, msg: str):
        """Parse, resolve, and execute tool requests from an agent message.

        Delegates resolution and execution to ``reasoning_engine``.
        """
        from ctxai.helpers.reasoning_engine import parse_tool_request, execute_tool
        from ctxai.helpers.tool import Response as ToolResponse

        raw_tool_name, tool_name, tool_args, tool, error = await parse_tool_request(self, msg)

        # No valid tool request at all
        if raw_tool_name is None and tool is None and error is None:
            warning_msg_misformat = self.read_prompt("fw.msg_misformat.md")
            self.hist_add_warning(warning_msg_misformat)
            PrintStyle(font_color="red", padding=True).print(warning_msg_misformat)
            self.context.log.log(
                type="warning",
                content=f"{self.agent_name}: Message misformat, no valid tool request found.",
            )
            return None

        if error:
            self.hist_add_warning(error)
            PrintStyle(font_color="red", padding=True).print(error)
            self.context.log.log(type="warning", content=f"{self.agent_name}: {error}")
            return None

        if tool:
            self.loop_data.current_tool = tool
            try:
                response: ToolResponse = await execute_tool(self, tool, tool_args, tool_name)
                if response.break_loop:
                    return response.message
            finally:
                self.loop_data.current_tool = None
        else:
            error_detail = f"Tool '{raw_tool_name}' not found or could not be initialized."
            self.hist_add_warning(error_detail)
            PrintStyle(font_color="red", padding=True).print(error_detail)
            self.context.log.log(type="warning", content=f"{self.agent_name}: {error_detail}")

        return None

    @extension.extensible
    async def validate_tool_request(self, tool_request: Any):
        if not isinstance(tool_request, dict):
            raise ValueError("Tool request must be a dictionary")
        if not tool_request.get("tool_name") or not isinstance(tool_request.get("tool_name"), str):
            raise ValueError("Tool request must have a tool_name (type string) field")
        if not tool_request.get("tool_args") or not isinstance(tool_request.get("tool_args"), dict):
            raise ValueError("Tool request must have a tool_args (type dictionary) field")

    async def handle_reasoning_stream(self, stream: str):
        await self.handle_intervention()
        await extension.call_extensions_async(
            "reasoning_stream",
            self,
            loop_data=self.loop_data,
            text=stream,
        )

    async def handle_response_stream(self, stream: str):
        await self.handle_intervention()
        try:
            if len(stream) < 25:
                return  # no reason to try
            response = DirtyJson.parse_string(stream)
            if isinstance(response, dict):
                await extension.call_extensions_async(
                    "response_stream",
                    self,
                    loop_data=self.loop_data,
                    text=stream,
                    parsed=response,
                )

        except Exception:
            pass

    @extension.extensible
    def get_tool(
        self,
        name: str,
        method: str | None,
        args: dict,
        message: str,
        loop_data: LoopData | None,
        **kwargs,
    ):
        from ctxai.helpers.reasoning_engine import resolve_tool

        return resolve_tool(self, name, method, args, message, loop_data)  # type: ignore[arg-type]
