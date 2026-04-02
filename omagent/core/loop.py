import logging
import time
from typing import TYPE_CHECKING, AsyncGenerator, Any

from omagent.core.events import (
    AgentEvent,
    TextDeltaEvent,
    ToolCallEvent,
    ToolResultEvent,
    PermissionDeniedEvent,
    PermissionPromptEvent,
    ErrorEvent,
    DoneEvent,
)
from omagent.core.hooks import HookRunner
from omagent.core.permissions import Permission, PermissionPolicy
from omagent.core.registry import ToolRegistry
from omagent.core.session import Session, SessionStore
from omagent.core.tracker import ActivityTracker
from omagent.providers.litellm_provider import LiteLLMProvider

if TYPE_CHECKING:
    from omagent.core.journal import EventJournal
    from omagent.core.memory import ConversationSummarizer
    from omagent.core.workspace import Workspace

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 20  # guard against infinite tool loops


class AgentLoop:
    """
    The generic agentic tool loop.

    Flow per turn:
    1. Add user message to session
    2. Call LLM with session messages + tool schemas
    3. Stream response: yield TextDeltaEvents as they arrive
    4. After stream ends, collect all ToolCallEvents
    5. For each tool call:
       a. Check permission (auto / prompt / deny)
       b. If auto: execute, yield ToolResultEvent
       c. If prompt: yield PermissionPromptEvent (caller handles user confirmation)
       d. If deny: yield PermissionDeniedEvent
    6. Add tool results to session, loop back to step 2
    7. If no tool calls in a response: yield DoneEvent, stop
    """

    def __init__(
        self,
        session: Session,
        registry: ToolRegistry,
        provider: LiteLLMProvider,
        policy: PermissionPolicy,
        hooks: HookRunner,
        system_prompt: str = "",
        store: SessionStore | None = None,
        tracker: ActivityTracker | None = None,
        workspace: "Workspace | None" = None,
        journal: "EventJournal | None" = None,
        summarizer: "ConversationSummarizer | None" = None,
    ):
        self.session = session
        self.registry = registry
        self.provider = provider
        self.policy = policy
        self.hooks = hooks
        self.system_prompt = system_prompt
        self.store = store  # if set, auto-save after each turn
        self.tracker = tracker
        self.workspace = workspace
        self.journal = journal
        self.summarizer = summarizer
        self.mcp_manager = None  # set after async MCP connection

    async def run(
        self, user_message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Process a user message. Yields streaming events.
        Handles the full multi-step tool loop until LLM stops calling tools.
        """
        self.session.add_user_message(user_message)

        if self.journal:
            self.journal.log_user_message(user_message)

        _first_iteration = True

        for iteration in range(MAX_ITERATIONS):
            text_chunks: list[str] = []
            tool_calls: list[ToolCallEvent] = []

            if self.journal:
                self.journal.set_round(iteration)

            # --- Log session start on first iteration ---
            if _first_iteration and self.tracker:
                _first_iteration = False
                try:
                    await self.tracker.log_milestone(
                        self.session.id,
                        "Session started",
                        {"pack_name": self.session.pack_name},
                    )
                except Exception as e:
                    logger.warning("tracker.log_milestone failed: %s", e)

            # --- Compact messages if needed ---
            if self.summarizer and self.summarizer.needs_summarization(self.session.messages):
                try:
                    result = await self.summarizer.summarize(self.session.messages)
                    self.session.messages = result["messages"]
                    if self.journal and result.get("messages_summarized"):
                        self.journal.log_memory_summary(
                            result["messages_summarized"],
                            result.get("summary") or "",
                        )
                except Exception as e:
                    logger.warning("summarizer.summarize failed: %s", e)

            # --- Stream LLM response ---
            if self.journal:
                self.journal.log_llm_request(
                    model=getattr(self.provider, "model", "unknown"),
                    message_count=len(self.session.messages),
                )

            _llm_start = time.monotonic()
            async for event in self.provider.stream(
                messages=self.session.messages,
                tools=self.registry.get_schemas() if self.registry.names() else None,
                system=self.system_prompt,
            ):
                if isinstance(event, TextDeltaEvent):
                    text_chunks.append(event.content)
                    await self.hooks.on_text(event.content)
                    yield event

                elif isinstance(event, ToolCallEvent):
                    tool_calls.append(event)

                elif isinstance(event, ErrorEvent):
                    await self.hooks.on_error(Exception(event.message))
                    yield event

                elif isinstance(event, DoneEvent):
                    pass  # handled below

            _llm_duration_ms = int((time.monotonic() - _llm_start) * 1000)

            # --- Add assistant message to session ---
            full_text = "".join(text_chunks)
            assistant_msg = self.provider.build_assistant_message(full_text, tool_calls)
            self.session.add_assistant_message(
                assistant_msg.get("content"),
                tool_calls=assistant_msg.get("tool_calls"),
            )

            # --- Journal LLM response ---
            if self.journal:
                _usage = getattr(self.provider, "_last_usage", None)
                _tokens_in = _usage.get("prompt_tokens") if _usage else None
                _tokens_out = _usage.get("completion_tokens") if _usage else None
                self.journal.log_llm_response(
                    tokens_in=_tokens_in,
                    tokens_out=_tokens_out,
                    latency_ms=_llm_duration_ms,
                    tool_calls_count=len(tool_calls),
                )

            # --- Log LLM call ---
            if self.tracker:
                try:
                    await self.tracker.log_llm_call(
                        session_id=self.session.id,
                        model=getattr(self.provider, "model", "unknown"),
                        duration_ms=_llm_duration_ms,
                        tool_calls_count=len(tool_calls),
                    )
                except Exception as e:
                    logger.warning("tracker.log_llm_call failed: %s", e)

            # --- If no tool calls, we're done ---
            if not tool_calls:
                if self.journal:
                    self.journal.log_session_end(
                        turns=iteration + 1,
                        total_cost=getattr(self.session, "total_cost", 0.0) or 0.0,
                    )
                if self.store:
                    await self.store.save(self.session)
                yield DoneEvent()
                return

            # --- Process each tool call ---
            for tc in tool_calls:
                permission = self.policy.check(tc.name, tc.input)

                if permission == Permission.DENY:
                    logger.info("Tool denied: %s", tc.name)
                    if self.journal:
                        self.journal.log_tool_call(tc.name, tc.input)
                    yield PermissionDeniedEvent(tool_name=tc.name, reason="policy deny")
                    self.session.add_tool_result(
                        tc.id, {"error": "permission denied"}, is_error=True
                    )
                    if self.journal:
                        self.journal.log_tool_result(tc.name, is_error=True, duration_ms=None)

                elif permission == Permission.PROMPT:
                    # Yield the prompt event — the caller (CLI/server) will handle it
                    # For now we auto-execute (caller can override by subclassing)
                    yield PermissionPromptEvent(tool_name=tc.name, input=tc.input)
                    if self.journal:
                        self.journal.log_tool_call(tc.name, tc.input)
                    await self.hooks.pre_tool(tc.name, tc.input)
                    _tool_start = time.monotonic()
                    result = await self.registry.execute(tc.name, tc.input)
                    _tool_duration_ms = int((time.monotonic() - _tool_start) * 1000)
                    await self.hooks.post_tool(tc.name, result)
                    is_error = "error" in result
                    self.session.add_tool_result(tc.id, result, is_error=is_error)
                    if self.journal:
                        self.journal.log_tool_result(tc.name, is_error=is_error, duration_ms=_tool_duration_ms)
                    if self.tracker:
                        try:
                            await self.tracker.log_tool_call(
                                self.session.id, tc.name, tc.input, result, _tool_duration_ms
                            )
                        except Exception as e:
                            logger.warning("tracker.log_tool_call failed: %s", e)
                    yield ToolResultEvent(
                        tool_use_id=tc.id,
                        tool_name=tc.name,
                        result=result,
                        is_error=is_error,
                    )

                else:  # AUTO
                    if self.journal:
                        self.journal.log_tool_call(tc.name, tc.input)
                    await self.hooks.pre_tool(tc.name, tc.input)
                    _tool_start = time.monotonic()
                    result = await self.registry.execute(tc.name, tc.input)
                    _tool_duration_ms = int((time.monotonic() - _tool_start) * 1000)
                    await self.hooks.post_tool(tc.name, result)
                    is_error = "error" in result
                    self.session.add_tool_result(tc.id, result, is_error=is_error)
                    if self.journal:
                        self.journal.log_tool_result(tc.name, is_error=is_error, duration_ms=_tool_duration_ms)
                    if self.tracker:
                        try:
                            await self.tracker.log_tool_call(
                                self.session.id, tc.name, tc.input, result, _tool_duration_ms
                            )
                        except Exception as e:
                            logger.warning("tracker.log_tool_call failed: %s", e)
                    yield ToolResultEvent(
                        tool_use_id=tc.id,
                        tool_name=tc.name,
                        result=result,
                        is_error=is_error,
                    )

        # Safety: hit MAX_ITERATIONS
        logger.warning("AgentLoop hit MAX_ITERATIONS=%d, stopping", MAX_ITERATIONS)
        yield ErrorEvent(message=f"Reached maximum iterations ({MAX_ITERATIONS})")
        yield DoneEvent()
