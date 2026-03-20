"""Reasoning engine: prompt assembly, LLM invocation, tool execution.

This module is a *stateless service layer* — it receives data from
Agent / AgentOrchestrator and returns results.  It does **not** own
any mutable agent state; callers pass in everything the engine needs.

Separating this logic from Agent makes each piece independently
testable and keeps the Agent class as a thin coordinator.
"""

from __future__ import annotations

from typing import Any
from typing import Awaitable
from typing import Callable
from typing import TYPE_CHECKING

from ctxai.helpers import dirty_json
from ctxai.helpers import extension
from ctxai.helpers import extract_tools
from ctxai.helpers import history
from ctxai.helpers import subagents
from ctxai.helpers import tokens
from ctxai.helpers.print_style import PrintStyle
from langchain_core.messages import BaseMessage
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

if TYPE_CHECKING:
    from ctxai.agent import Agent, LoopData
    from ctxai.helpers.tool import Response as ToolResponse, Tool


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


async def build_prompt(agent: Agent, loop_data: "LoopData") -> list[BaseMessage]:
    """Assemble the full prompt list (system + history + extras).

    Mirrors the original ``Agent.prepare_prompt`` logic but lives in the
    engine layer so it can be unit-tested without a running Agent.
    """
    agent.context.log.set_progress("Building prompt")

    # Allow extensions to inject prompt content
    await extension.call_extensions_async("message_loop_prompts_before", agent, loop_data=loop_data)

    # System prompt (assembled by extensions via the "system_prompt" hook)
    loop_data.system = await _get_system_prompt(agent, loop_data)
    loop_data.history_output = agent.history.output()

    # Allow extensions to mutate assembled prompts
    await extension.call_extensions_async("message_loop_prompts_after", agent, loop_data=loop_data)

    # Concatenate system text
    system_text = "\n\n".join(loop_data.system)

    # Extras block
    extras = history.Message(
        False,
        content=agent.read_prompt(
            "agent.context.extras.md",
            extras=dirty_json.stringify({**loop_data.extras_persistent, **loop_data.extras_temporary}),
        ),
    ).output()
    loop_data.extras_temporary.clear()

    # Convert to LangChain messages
    history_langchain: list[BaseMessage] = history.output_langchain(loop_data.history_output + extras)

    full_prompt: list[BaseMessage] = [
        SystemMessage(content=system_text),
        *history_langchain,
    ]

    # Cache context-window info on the agent's data dict
    full_text = ChatPromptTemplate.from_messages(full_prompt).format()
    agent.set_data(
        Agent.DATA_NAME_CTX_WINDOW,
        {"text": full_text, "tokens": tokens.approximate_tokens(full_text)},
    )

    return full_prompt


async def _get_system_prompt(agent: Agent, loop_data: "LoopData") -> list[str]:
    """Collect system prompt fragments via extension hook."""
    system_prompt: list[str] = []
    await extension.call_extensions_async("system_prompt", agent, system_prompt=system_prompt, loop_data=loop_data)
    return system_prompt


# ---------------------------------------------------------------------------
# LLM invocation
# ---------------------------------------------------------------------------


async def call_chat_model(
    agent: Agent,
    messages: list[BaseMessage],
    response_callback: Callable[[str, str], Awaitable[None]] | None = None,
    reasoning_callback: Callable[[str, str], Awaitable[None]] | None = None,
    background: bool = False,
    explicit_caching: bool = True,
) -> tuple[str, str]:
    """Invoke the primary chat model and return (response, reasoning)."""
    model = agent.get_chat_model()
    response, reasoning = await model.unified_call(
        messages=messages,
        reasoning_callback=reasoning_callback,
        response_callback=response_callback,
        rate_limiter_callback=(agent.rate_limiter_callback if not background else None),
        explicit_caching=explicit_caching,
    )
    return response, reasoning


async def call_utility_model(
    agent: Agent,
    system: str,
    message: str,
    callback: Callable[[str], Awaitable[None]] | None = None,
    background: bool = False,
) -> str:
    """Invoke the utility (smaller) model and return the text response."""
    model = agent.get_utility_model()

    call_data: dict[str, Any] = {
        "model": model,
        "system": system,
        "message": message,
        "callback": callback,
        "background": background,
    }
    await extension.call_extensions_async("util_model_call_before", agent, call_data=call_data)

    async def stream_callback(chunk: str, total: str) -> None:
        if call_data["callback"]:
            await call_data["callback"](chunk)

    response, _reasoning = await call_data["model"].unified_call(
        system_message=call_data["system"],
        user_message=call_data["message"],
        response_callback=stream_callback if call_data["callback"] else None,
        rate_limiter_callback=(agent.rate_limiter_callback if not call_data["background"] else None),
    )

    await extension.call_extensions_async("util_model_call_after", agent, call_data=call_data, response=response)
    return response


# ---------------------------------------------------------------------------
# Tool resolution & execution
# ---------------------------------------------------------------------------


def resolve_tool(
    agent: Agent,
    name: str,
    method: str | None,
    args: dict,
    message: str,
    loop_data: "LoopData",
) -> "Tool":
    """Locate and instantiate a tool by name from the agent's path hierarchy."""
    from ctxai.tools.unknown import Unknown
    from ctxai.helpers.tool import Tool

    classes: list[type] = []
    paths = subagents.get_paths(agent, "tools", name + ".py")

    for path in paths:
        try:
            classes = extract_tools.load_classes_from_file(path, Tool)  # type: ignore[type-abstract]
            break
        except Exception:
            continue

    tool_class = classes[0] if classes else Unknown
    return tool_class(
        agent=agent,
        name=name,
        method=method,
        args=args,
        message=message,
        loop_data=loop_data,
    )


async def execute_tool(agent: Agent, tool: "Tool", tool_args: dict, tool_name: str) -> "ToolResponse":
    """Run the full tool lifecycle (before/execute/after) and return the response.

    This is the base single-attempt execution.  Use ``execute_tool_with_retry``
    when retry/fallback semantics are needed.
    """

    await tool.before_execution(**tool_args)
    await _check_intervention(agent)

    await extension.call_extensions_async(
        "tool_execute_before",
        agent,
        tool_args=tool_args or {},
        tool_name=tool_name,
    )

    response: ToolResponse = await tool.execute(**tool_args)
    await _check_intervention(agent)

    await extension.call_extensions_async(
        "tool_execute_after",
        agent,
        response=response,
        tool_name=tool_name,
    )

    await tool.after_execution(response)
    await _check_intervention(agent)

    # Record tool result in agent memory
    agent.memory.record_tool_result(tool_name, response.message)

    return response


async def execute_tool_with_retry(
    agent: Agent,
    tool: "Tool",
    tool_args: dict,
    tool_name: str,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    fallback_tool: "Tool | None" = None,
) -> "ToolResponse":
    """Execute a tool with retry logic and optional fallback.

    On failure the tool is retried up to *max_retries* times with
    exponential backoff (``retry_delay * attempt``).  If all retries
    fail and *fallback_tool* is provided, it is executed once with the
    same arguments.
    """
    import asyncio

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return await execute_tool(agent, tool, tool_args, tool_name)
        except Exception as e:
            last_error = e
            PrintStyle(font_color="orange", padding=True).print(
                f"Tool '{tool_name}' attempt {attempt}/{max_retries} failed: {e}",
            )
            agent.context.log.log(
                type="warning",
                content=f"Tool '{tool_name}' attempt {attempt}/{max_retries} failed: {e}",
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay * attempt)

    # All retries exhausted — try fallback
    if fallback_tool is not None:
        PrintStyle(font_color="yellow", padding=True).print(
            f"Tool '{tool_name}' exhausted retries, trying fallback '{fallback_tool.name}'",
        )
        agent.context.log.log(
            type="info",
            content=f"Trying fallback tool '{fallback_tool.name}' for '{tool_name}'",
        )
        try:
            return await execute_tool(agent, fallback_tool, tool_args, fallback_tool.name)
        except Exception as fallback_error:
            last_error = fallback_error

    # No fallback or fallback also failed
    raise last_error or RuntimeError(f"Tool '{tool_name}' failed after {max_retries} attempts")


async def parse_tool_request(agent: Agent, msg: str) -> tuple[str | None, str | None, dict, "Tool | None", str | None]:
    """Parse tool invocation from an agent message.

    Returns ``(raw_tool_name, tool_name, tool_args, tool_instance, error_message)``.
    ``tool_instance`` is ``None`` when the tool cannot be resolved.
    ``error_message`` is ``None`` on success.
    """
    tool_request = extract_tools.json_parse_dirty(msg)

    await _validate_tool_request(agent, tool_request)

    if tool_request is None:
        return None, None, {}, None, None  # signal: no valid tool request

    raw_tool_name = tool_request.get("tool_name", tool_request.get("tool", ""))
    tool_args = tool_request.get("tool_args", tool_request.get("args", {}))

    tool_name = raw_tool_name
    tool_method = None
    if ":" in raw_tool_name:
        tool_name, tool_method = raw_tool_name.split(":", 1)

    # MCP lookup first
    tool = None
    try:
        import ctxai.helpers.mcp_handler as mcp_helper

        mcp_tool_candidate = mcp_helper.MCPConfig.get_instance().get_tool(agent, tool_name)
        if mcp_tool_candidate:
            tool = mcp_tool_candidate
    except ImportError:
        PrintStyle(background_color="black", font_color="yellow", padding=True).print(
            "MCP helper module not found. Skipping MCP tool lookup.",
        )
    except Exception as e:
        PrintStyle(background_color="black", font_color="red", padding=True).print(
            f"Failed to get MCP tool '{tool_name}': {e}",
        )

    # Fallback to local tools
    if not tool:
        tool = resolve_tool(agent, tool_name, tool_method, tool_args, msg, agent.loop_data)

    return raw_tool_name, tool_name, tool_args, tool, None


async def _validate_tool_request(agent: Agent, tool_request: Any) -> None:
    """Basic validation + extension hook."""
    await extension.call_extensions_async(
        "validate_tool_request",
        agent,
        tool_request=tool_request,
    )
    if not isinstance(tool_request, dict):
        raise ValueError("Tool request must be a dictionary")
    if not tool_request.get("tool_name") or not isinstance(tool_request.get("tool_name"), str):
        raise ValueError("Tool request must have a tool_name (type string) field")
    if not tool_request.get("tool_args") or not isinstance(tool_request.get("tool_args"), dict):
        raise ValueError("Tool request must have a tool_args (type dictionary) field")


async def _check_intervention(agent: Agent) -> None:
    """Thin wrapper to reuse Agent's intervention logic."""
    await agent.handle_intervention()
