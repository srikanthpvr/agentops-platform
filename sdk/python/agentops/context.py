"""
agentops.context
================
``TraceContext`` — the central object users interact with during a single agent run.

A ``TraceContext`` is both a *synchronous* and *asynchronous* context manager.
When the ``with`` / ``async with`` block exits it:

1. Calculates the total trace duration.
2. Sets ``status = "error"`` if an unhandled exception propagated out.
3. Serialises the trace (including all registered child spans) to a Pydantic
   model and enqueues it on the :class:`~agentops.client.AgentOpsClient`.

Thread-local storage is used to maintain a stack of active trace contexts so
that nested traces work correctly without passing the context around explicitly.

Usage
-----
Via the :class:`~agentops.tracer.Tracer` helper (recommended):

>>> with tracer.start_trace("my-agent", metadata={"run_id": "r-1"}) as ctx:
...     with ctx.add_span("llm-call", span_type="llm") as span:
...         span.set_model("gpt-4o", tokens_input=100, tokens_output=50)

Async:

>>> async with tracer.start_trace("async-agent") as ctx:
...     async with ctx.add_span("async-tool", span_type="tool") as span:
...         span.set_input("some query")
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .models import TraceData
from .span import SpanContext

if TYPE_CHECKING:
    from .client import AgentOpsClient

logger = logging.getLogger(__name__)

# Thread-local stack of active TraceContext objects.
# Each thread maintains its own independent stack so nested traces are isolated.
_local = threading.local()


def _get_context_stack() -> List["TraceContext"]:
    """Return (and lazily initialise) the per-thread trace-context stack."""
    if not hasattr(_local, "stack"):
        _local.stack = []
    return _local.stack


def get_current_trace() -> Optional["TraceContext"]:
    """
    Return the innermost active :class:`TraceContext` for the current thread,
    or ``None`` if no trace is active.

    This is used by :mod:`agentops.decorators` to attach spans to the
    ambient trace without requiring explicit context passing.
    """
    stack = _get_context_stack()
    return stack[-1] if stack else None


class TraceContext:
    """
    Represents a single agent trace — the top-level unit of observability.

    Do not instantiate directly; use :meth:`~agentops.tracer.Tracer.start_trace`
    or the ``@agentops.trace`` decorator.

    Parameters
    ----------
    client:
        The :class:`~agentops.client.AgentOpsClient` used to ship the trace.
    trace_id:
        UUID string for this trace.
    agent_name:
        Display name of the agent.
    session_id:
        Optional caller-supplied grouping key (e.g. a user session ID).
    metadata:
        Initial metadata dict; can be mutated during the trace.

    Attributes
    ----------
    trace_id : str
        UUID string identifying this trace.
    agent_name : str
        Display name of the agent.
    session_id : Optional[str]
        Caller-supplied session identifier.
    metadata : dict
        Mutable key-value bag for arbitrary trace-level metadata.
    """

    def __init__(
        self,
        client: "AgentOpsClient",
        trace_id: str,
        agent_name: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._client = client
        self.trace_id = trace_id
        self.agent_name = agent_name
        self.session_id = session_id
        self.metadata: Dict[str, Any] = dict(metadata or {})

        # Timing (set by __enter__ / __aenter__)
        self._started_at: Optional[datetime] = None
        self._ended_at: Optional[datetime] = None

        # Status
        self._status: str = "ok"
        self._error_message: Optional[str] = None
        self._error_type: Optional[str] = None

        # Child spans — appended via _register_span()
        self._spans: List[SpanContext] = []

        # Tracks the "current" span for nesting purposes
        self._active_span_stack: List[SpanContext] = []

    # ------------------------------------------------------------------
    # Span factory
    # ------------------------------------------------------------------

    def add_span(
        self,
        name: str,
        span_type: str = "custom",
        **kwargs: Any,
    ) -> SpanContext:
        """
        Create a child :class:`~agentops.span.SpanContext`.

        The returned object is intended to be used as a context manager::

            with ctx.add_span("parse-pdf", span_type="tool") as span:
                span.set_input("document.pdf")
                ...

        Parameters
        ----------
        name:
            Human-readable label for the span.
        span_type:
            Category string.  Recommended values: ``"llm"``, ``"tool"``,
            ``"retrieval"``, ``"chain"``, ``"custom"``.
        **kwargs:
            Currently unused; reserved for future span options.

        Returns
        -------
        SpanContext
            An uninitialised span (timing starts on ``__enter__``).
        """
        # Determine the parent span ID from the active span stack.
        parent_span_id = (
            self._active_span_stack[-1].span_id if self._active_span_stack else None
        )
        span = SpanContext(
            trace_ctx=self,
            span_id=str(uuid.uuid4()),
            name=name,
            span_type=span_type,
            parent_span_id=parent_span_id,
        )
        # Push onto the active span stack when entering; popped when __exit__ is called.
        # We override __enter__/__exit__ on the returned span to manage the stack.
        span._on_enter_callback = lambda: self._active_span_stack.append(span)
        span._on_exit_callback = lambda: (
            self._active_span_stack.pop() if self._active_span_stack else None
        )
        return _WrappedSpan(span, self)

    def _register_span(self, span: SpanContext) -> None:
        """Called by :class:`~agentops.span.SpanContext.__exit__` to record a completed span."""
        self._spans.append(span)
        logger.debug("Span '%s' registered (total spans: %d).", span.name, len(self._spans))

    # ------------------------------------------------------------------
    # Synchronous context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "TraceContext":
        """Begin the trace: record start time and push onto the thread-local stack."""
        self._started_at = datetime.now(tz=timezone.utc)
        _get_context_stack().append(self)
        logger.debug("Trace '%s' (%s) started.", self.agent_name, self.trace_id)
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> bool:
        """
        End the trace, capture any exception, serialise the trace, and enqueue
        it for transmission.  Returns ``False`` so exceptions propagate normally.
        """
        self._ended_at = datetime.now(tz=timezone.utc)
        self._finalise(exc_type, exc_val)
        self._send()
        # Pop from the thread-local stack (guard against double-exit).
        stack = _get_context_stack()
        if self in stack:
            stack.remove(self)
        logger.debug(
            "Trace '%s' (%s) ended; status=%s",
            self.agent_name,
            self.trace_id,
            self._status,
        )
        return False

    # ------------------------------------------------------------------
    # Asynchronous context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "TraceContext":
        """Async version of ``__enter__``."""
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> bool:
        """Async version of ``__exit__``."""
        return self.__exit__(exc_type, exc_val, exc_tb)

    # ------------------------------------------------------------------
    # Serialisation & transmission
    # ------------------------------------------------------------------

    def to_model(self) -> TraceData:
        """
        Serialise this trace (and all registered child spans) to a
        :class:`~agentops.models.TraceData` Pydantic model.

        Returns
        -------
        TraceData
            Wire-format representation ready for JSON encoding.
        """
        return TraceData(
            trace_id=self.trace_id,
            session_id=self.session_id,
            agent_name=self.agent_name,
            started_at=self._started_at or datetime.now(tz=timezone.utc),
            ended_at=self._ended_at,
            duration_ms=self._duration_ms(),
            status=self._status,
            error_message=self._error_message,
            error_type=self._error_type,
            spans=[s.to_model() for s in self._spans],
            metadata=self.metadata,
        )

    def _send(self) -> None:
        """Serialise and enqueue the trace on the client's batch queue."""
        try:
            payload = self.to_model().model_dump(mode="json")
            self._client.enqueue(payload)
        except Exception as exc:  # pragma: no cover
            logger.warning("AgentOps: failed to serialise trace %s: %s", self.trace_id, exc)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _finalise(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
    ) -> None:
        """Capture error info from an unhandled exception if one occurred."""
        if exc_type is not None:
            self._status = "error"
            self._error_type = f"{exc_type.__module__}.{exc_type.__qualname__}"
            self._error_message = str(exc_val)

    def _duration_ms(self) -> Optional[float]:
        if self._started_at is None or self._ended_at is None:
            return None
        return (self._ended_at - self._started_at).total_seconds() * 1000


# ---------------------------------------------------------------------------
# Internal wrapper — manages the active-span stack transparently
# ---------------------------------------------------------------------------

class _WrappedSpan(SpanContext):
    """
    Internal subclass that hooks into ``__enter__``/``__exit__`` to push/pop
    the span on the trace's active-span stack (enabling correct parent_span_id
    for deeply nested spans).

    This is an implementation detail; users always interact with SpanContext.
    """

    def __init__(self, inner: SpanContext, trace_ctx: TraceContext) -> None:
        # Copy all state from the inner span
        super().__init__(
            trace_ctx=trace_ctx,
            span_id=inner.span_id,
            name=inner.name,
            span_type=inner.span_type,
            parent_span_id=inner._parent_span_id,
        )
        self._on_enter_callback = getattr(inner, "_on_enter_callback", lambda: None)
        self._on_exit_callback = getattr(inner, "_on_exit_callback", lambda: None)

    def __enter__(self) -> "SpanContext":
        result = super().__enter__()
        self._on_enter_callback()
        return result

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Any) -> bool:
        self._on_exit_callback()
        return super().__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self) -> "SpanContext":
        result = await super().__aenter__()
        self._on_enter_callback()
        return result

    async def __aexit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Any) -> bool:
        self._on_exit_callback()
        return await super().__aexit__(exc_type, exc_val, exc_tb)
