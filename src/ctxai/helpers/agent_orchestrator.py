"""Agent orchestrator: process chain, message loop, intervention handling.

Extracted from AgentContext and Agent so that scheduling / lifecycle
logic lives in one place and the Agent class stays focused on its
domain role (prompt templates, tool invocation, history management).

The orchestrator is a *thin coordinator* — it calls into
``reasoning_engine`` for the heavy lifting and into the extension
system for plugin hooks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ctxai.helpers import extension
from ctxai.helpers.event_bus import EventBus
from ctxai.helpers.event_bus import EventType
from ctxai.helpers.print_style import PrintStyle

if TYPE_CHECKING:
    from ctxai.agent import Agent, AgentContext, UserMessage


# ---------------------------------------------------------------------------
# Process chain (top-level entry point)
# ---------------------------------------------------------------------------


async def run_process_chain(
    context: "AgentContext",
    agent: "Agent",
    msg: "UserMessage | str",
    user: bool = True,
) -> str:
    """Execute one process-chain iteration and recurse to superior if needed.

    This is the coroutine that ``AgentContext.run_task`` kicks off.
    """
    from ctxai.agent import Agent as _Agent  # local import to avoid circular

    bus = EventBus.get()

    try:
        if user:
            agent.hist_add_user_message(msg)  # type: ignore[arg-type]
        else:
            agent.hist_add_tool_result(
                tool_name="call_subordinate",
                tool_result=str(msg),
            )

        response = await run_monologue(agent)

        # Bubble up to superior agent if there is one
        superior = agent.data.get(_Agent.DATA_NAME_SUPERIOR, None)
        if superior:
            response = await run_process_chain(context, superior, response, user=False)

        await extension.call_extensions_async("process_chain_end", agent=context.get_agent(), data={})
        bus.emit(EventType.PROCESS_CHAIN_END, agent=context.get_agent())

        return response
    except Exception as e:
        await context.handle_exception("process_chain", e)
        raise  # handle_exception re-raises unless extension clears it


# ---------------------------------------------------------------------------
# Monologue (inner message loop)
# ---------------------------------------------------------------------------


async def run_monologue(agent: "Agent") -> str:
    """Run one iteration of the agent's reasoning loop.

    The *outer* monologue_start/monologue_end extension hooks are handled by
    the ``@extension.extensible`` decorator on ``Agent.monologue``.  This
    function manages the *inner* message-loop lifecycle hooks and delegates
    prompt assembly / model calls / tool execution to the reasoning engine.
    """
    from ctxai.agent import LoopData as _LoopData

    bus = EventBus.get()
    printer = PrintStyle(italic=True, font_color="#b3ffd9", padding=False)

    try:
        agent.loop_data = _LoopData(user_message=agent.last_user_message)
        # Inner lifecycle hook — fires once per monologue iteration
        await extension.call_extensions_async("monologue_start", agent, loop_data=agent.loop_data)
        bus.emit(EventType.MONOLOGUE_START, agent=agent)

        while True:
            agent.context.streaming_agent = agent
            agent.loop_data.iteration += 1
            agent.loop_data.params_temporary = {}

            await extension.call_extensions_async("message_loop_start", agent, loop_data=agent.loop_data)
            bus.emit(EventType.LOOP_START, agent=agent, iteration=agent.loop_data.iteration)
            await agent.handle_intervention()

            try:
                # --- prompt assembly ---
                from ctxai.helpers import reasoning_engine

                prompt = await reasoning_engine.build_prompt(agent, agent.loop_data)

                await extension.call_extensions_async("before_main_llm_call", agent, loop_data=agent.loop_data)
                bus.emit(EventType.BEFORE_LLM_CALL, agent=agent)
                await agent.handle_intervention()

                # --- stream callbacks ---
                async def reasoning_callback(chunk: str, full: str) -> None:
                    await agent.handle_intervention()
                    if chunk == full:
                        printer.print("Reasoning: ")
                    stream_data = {"chunk": chunk, "full": full}
                    await extension.call_extensions_async(
                        "reasoning_stream_chunk",
                        agent,
                        loop_data=agent.loop_data,
                        stream_data=stream_data,
                    )
                    bus.emit(
                        EventType.REASONING_CHUNK,
                        agent=agent,
                        chunk=stream_data["chunk"],
                        full=stream_data["full"],
                    )
                    if stream_data.get("chunk"):
                        printer.stream(stream_data["chunk"])
                    await agent.handle_reasoning_stream(stream_data["full"])

                async def stream_callback(chunk: str, full: str) -> None:
                    await agent.handle_intervention()
                    if chunk == full:
                        printer.print("Response: ")
                    stream_data = {"chunk": chunk, "full": full}
                    await extension.call_extensions_async(
                        "response_stream_chunk",
                        agent,
                        loop_data=agent.loop_data,
                        stream_data=stream_data,
                    )
                    bus.emit(
                        EventType.RESPONSE_CHUNK,
                        agent=agent,
                        chunk=stream_data["chunk"],
                        full=stream_data["full"],
                    )
                    if stream_data.get("chunk"):
                        printer.stream(stream_data["chunk"])
                    await agent.handle_response_stream(stream_data["full"])

                # --- LLM call ---
                agent_response, _reasoning = await reasoning_engine.call_chat_model(
                    agent,
                    messages=prompt,
                    response_callback=stream_callback,
                    reasoning_callback=reasoning_callback,
                )
                await agent.handle_intervention(agent_response)

                await extension.call_extensions_async("reasoning_stream_end", agent, loop_data=agent.loop_data)
                bus.emit(EventType.REASONING_END, agent=agent)
                await agent.handle_intervention(agent_response)

                await extension.call_extensions_async("response_stream_end", agent, loop_data=agent.loop_data)
                bus.emit(EventType.RESPONSE_END, agent=agent)
                await agent.handle_intervention(agent_response)

                # --- post-processing ---
                if agent.loop_data.last_response == agent_response:
                    agent.hist_add_ai_response(agent_response)
                    warning_msg = agent.read_prompt("fw.msg_repeat.md")
                    agent.hist_add_warning(message=warning_msg)
                    PrintStyle(font_color="orange", padding=True).print(warning_msg)
                    agent.context.log.log(type="warning", content=warning_msg)
                else:
                    agent.hist_add_ai_response(agent_response)
                    tools_result = await _process_tools(agent, agent_response)
                    if tools_result:
                        return tools_result

            except Exception as e:
                await agent.handle_exception("message_loop", e)

            finally:
                if agent.context.task and agent.context.task.is_alive():
                    await extension.call_extensions_async("message_loop_end", agent, loop_data=agent.loop_data)
                    bus.emit(EventType.LOOP_END, agent=agent, iteration=agent.loop_data.iteration)

    finally:
        agent.context.streaming_agent = None
        if agent.context.task and agent.context.task.is_alive():
            await extension.call_extensions_async("monologue_end", agent, loop_data=agent.loop_data)
            bus.emit(EventType.MONOLOGUE_END, agent=agent)


# ---------------------------------------------------------------------------
# Tool processing (delegates to reasoning_engine for resolution + execution)
# ---------------------------------------------------------------------------


async def _process_tools(agent: "Agent", msg: str) -> str | None:
    """Parse tool request from *msg*, resolve, execute, return final answer or None."""
    from ctxai.helpers import reasoning_engine
    from ctxai.helpers.tool import Response as ToolResponse

    raw_tool_name, tool_name, tool_args, tool, error = await reasoning_engine.parse_tool_request(agent, msg)

    # error from validation – handled by extensions
    if raw_tool_name is None and tool is None and error is None:
        # No valid tool request at all
        warning_msg_misformat = agent.read_prompt("fw.msg_misformat.md")
        agent.hist_add_warning(warning_msg_misformat)
        PrintStyle(font_color="red", padding=True).print(warning_msg_misformat)
        agent.context.log.log(
            type="warning",
            content=f"{agent.agent_name}: Message misformat, no valid tool request found.",
        )
        return None

    if error:
        agent.hist_add_warning(error)
        PrintStyle(font_color="red", padding=True).print(error)
        agent.context.log.log(type="warning", content=f"{agent.agent_name}: {error}")
        return None

    if tool:
        agent.loop_data.current_tool = tool
        try:
            response: ToolResponse = await reasoning_engine.execute_tool(agent, tool, tool_args, tool_name)
            if response.break_loop:
                return response.message
        finally:
            agent.loop_data.current_tool = None
    else:
        error_detail = f"Tool '{raw_tool_name}' not found or could not be initialized."
        agent.hist_add_warning(error_detail)
        PrintStyle(font_color="red", padding=True).print(error_detail)
        agent.context.log.log(type="warning", content=f"{agent.agent_name}: {error_detail}")

    return None
