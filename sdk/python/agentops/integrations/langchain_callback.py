"""
agentops.integrations.langchain_callback
=========================================
LangChain callback handler that automatically instruments LangChain chains,
agents, and LLMs with AgentOps traces and spans.

Plug into any LangChain chain/agent::

    from agentops.integrations.langchain_callback import AgentOpsCallbackHandler

    handler = AgentOpsCallbackHandler(agent_name="my-langchain-agent")

    llm = ChatOpenAI(callbacks=[handler])
    chain = LLMChain(llm=llm, prompt=prompt, callbacks=[handler])
    result = chain.run(input="hello")

The handler creates one AgentOps **trace** per chain run and child **spans** for:

- Each LLM call (``span_type="llm"``)
- Each chain invocation (``span_type="chain"``)
- Each tool use (``span_type="tool"``)

Token usage is automatically extracted from the LLM response when available.

Requirements
------------
Install the langchain extra::

    pip install "agentops-sdk[langchain]"
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from agentops.context import TraceContext, get_current_trace
from agentops.globals import get_tracer
from agentops.span import SpanContext

logger = logging.getLogger(__name__)

try:
    from langchain.callbacks.base import BaseCallbackHandler
    from langchain.schema import AgentAction, AgentFinish, LLMResult
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The LangChain integration requires langchain to be installed. "
        "Run: pip install 'agentops-sdk[langchain]'"
    ) from exc


class AgentOpsCallbackHandler(BaseCallbackHandler):
    """
    LangChain ``BaseCallbackHandler`` that ships events to the AgentOps platform.

    Parameters
    ----------
    agent_name:
        Display name used for the top-level AgentOps trace created when a
        chain/agent run starts.
    session_id:
        Optional session ID to group related traces.
    metadata:
        Initial trace-level metadata key-value pairs.

    Usage
    -----
    ::

        import agentops
        from agentops.integrations.langchain_callback import AgentOpsCallbackHandler

        agentops.init(api_key="ao_live_xxx")
        handler = AgentOpsCallbackHandler(agent_name="research-agent")

        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(callbacks=[handler])
        result = llm.predict("What is 2+2?")

    Chain-level usage (creates a single trace around the entire chain)::

        from langchain.chains import LLMChain
        chain = LLMChain(llm=llm, prompt=prompt, callbacks=[handler])
        result = chain.run(text="hello")
    """

    def __init__(
        self,
        agent_name: str = "langchain-agent",
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__()
        self._agent_name = agent_name
        self._session_id = session_id
        self._base_metadata = metadata or {}

        # Maps run_id (str) → TraceContext or SpanContext
        self._traces: Dict[str, TraceContext] = {}
        self._spans: Dict[str, SpanContext] = {}

    # ------------------------------------------------------------------
    # LLM callbacks
    # ------------------------------------------------------------------

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM begins generating."""
        run_key = str(run_id)
        model_name = (serialized.get("kwargs") or {}).get("model_name", "unknown")
        logger.debug("on_llm_start: run_id=%s model=%s", run_key, model_name)

        ctx = self._get_or_create_trace(parent_run_id)
        span = ctx.add_span(f"llm:{model_name}", span_type="llm")
        span.__enter__()
        span.set_input("\n---\n".join(prompts))
        span.set_metadata("model", model_name)
        span.set_metadata("langchain_run_id", run_key)
        self._spans[run_key] = span

    def on_llm_end(
        self,
        response: "LLMResult",
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM finishes; extracts token usage if available."""
        run_key = str(run_id)
        span = self._spans.pop(run_key, None)
        if span is None:
            return

        # Extract the first generation text as output.
        try:
            generations = response.generations
            output_text = generations[0][0].text if generations and generations[0] else ""
        except (IndexError, AttributeError):
            output_text = ""

        span.set_output(output_text)

        # Extract token usage from LLM response metadata.
        llm_output = response.llm_output or {}
        token_usage = llm_output.get("token_usage") or {}
        prompt_tokens = token_usage.get("prompt_tokens") or token_usage.get("input_tokens")
        completion_tokens = token_usage.get("completion_tokens") or token_usage.get("output_tokens")
        model_name = llm_output.get("model_name") or span._model or "unknown"

        if prompt_tokens is not None and completion_tokens is not None:
            span.set_model(
                model=model_name,
                tokens_input=int(prompt_tokens),
                tokens_output=int(completion_tokens),
            )

        span.__exit__(None, None, None)
        logger.debug("on_llm_end: run_id=%s tokens_in=%s tokens_out=%s", run_key, prompt_tokens, completion_tokens)

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM raises an error."""
        run_key = str(run_id)
        span = self._spans.pop(run_key, None)
        if span is None:
            return
        span.__exit__(type(error), error, None)
        logger.debug("on_llm_error: run_id=%s error=%s", run_key, error)

    # ------------------------------------------------------------------
    # Chain callbacks
    # ------------------------------------------------------------------

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain begins.  Creates a new trace for root chains."""
        run_key = str(run_id)
        chain_name = serialized.get("id", ["unknown"])[-1]
        logger.debug("on_chain_start: run_id=%s chain=%s", run_key, chain_name)

        if parent_run_id is None:
            # Root chain — create a top-level trace.
            tracer = get_tracer()
            ctx = tracer.start_trace(
                agent_name=self._agent_name,
                session_id=self._session_id,
                metadata={**self._base_metadata, "chain_name": chain_name},
            )
            ctx.__enter__()
            self._traces[run_key] = ctx
        else:
            # Nested chain — create a child span.
            ctx = self._get_or_create_trace(parent_run_id)
            span = ctx.add_span(f"chain:{chain_name}", span_type="chain")
            span.__enter__()
            span.set_input(str(inputs))
            self._spans[run_key] = span

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a chain finishes."""
        run_key = str(run_id)

        # Check if this was a root chain (trace) or nested chain (span).
        if run_key in self._traces:
            ctx = self._traces.pop(run_key)
            ctx.__exit__(None, None, None)
            logger.debug("on_chain_end (root trace): run_id=%s", run_key)
        elif run_key in self._spans:
            span = self._spans.pop(run_key)
            span.set_output(str(outputs))
            span.__exit__(None, None, None)
            logger.debug("on_chain_end (nested span): run_id=%s", run_key)

    def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a chain raises an error."""
        run_key = str(run_id)
        if run_key in self._traces:
            ctx = self._traces.pop(run_key)
            ctx.__exit__(type(error), error, None)
        elif run_key in self._spans:
            span = self._spans.pop(run_key)
            span.__exit__(type(error), error, None)
        logger.debug("on_chain_error: run_id=%s error=%s", run_key, error)

    # ------------------------------------------------------------------
    # Tool callbacks
    # ------------------------------------------------------------------

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts executing."""
        run_key = str(run_id)
        tool_name = serialized.get("name", "unknown-tool")
        logger.debug("on_tool_start: run_id=%s tool=%s", run_key, tool_name)

        ctx = self._get_or_create_trace(parent_run_id)
        span = ctx.add_span(f"tool:{tool_name}", span_type="tool")
        span.__enter__()
        span.set_input(input_str)
        span.set_metadata("tool_name", tool_name)
        self._spans[run_key] = span

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a tool finishes."""
        run_key = str(run_id)
        span = self._spans.pop(run_key, None)
        if span is None:
            return
        span.set_output(output)
        span.__exit__(None, None, None)
        logger.debug("on_tool_end: run_id=%s", run_key)

    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a tool raises an error."""
        run_key = str(run_id)
        span = self._spans.pop(run_key, None)
        if span is None:
            return
        span.__exit__(type(error), error, None)
        logger.debug("on_tool_error: run_id=%s error=%s", run_key, error)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_or_create_trace(
        self, parent_run_id: Optional[uuid.UUID]
    ) -> TraceContext:
        """
        Return the trace associated with ``parent_run_id``, or fall back to
        the ambient trace on the current thread, or create a new orphan trace.
        """
        if parent_run_id is not None:
            parent_key = str(parent_run_id)
            if parent_key in self._traces:
                return self._traces[parent_key]

        # Try the ambient trace (e.g. from @agentops.trace on the caller).
        ambient = get_current_trace()
        if ambient is not None:
            return ambient

        # Last resort: create an orphan trace that closes immediately.
        # This can happen when LLM callbacks fire outside any chain context.
        tracer = get_tracer()
        ctx = tracer.start_trace(
            agent_name=f"{self._agent_name}:orphan",
            session_id=self._session_id,
            metadata=self._base_metadata,
        )
        ctx.__enter__()
        orphan_key = str(uuid.uuid4())
        self._traces[orphan_key] = ctx
        return ctx
