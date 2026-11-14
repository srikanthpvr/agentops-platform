"""
agentops.decorators
===================
Standalone module-level decorators that work with the global tracer singleton.

These are thin wrappers around the global :class:`~agentops.tracer.Tracer`
returned by :func:`~agentops.globals.init`.  Import and use them directly::

    import agentops

    agentops.init(api_key="ao_live_xxx")

    @agentops.trace(agent_name="my-agent")
    def run_agent(query: str) -> str:
        return "result"

    @agentops.span(name="fetch-docs", span_type="retrieval")
    def fetch_docs(query: str) -> list:
        return []

Both decorators support *synchronous* and *async* functions transparently
using :func:`inspect.iscoroutinefunction`.

.. important::
   ``@agentops.span`` attaches the span to the **ambient** trace in the
   current thread.  It must be called inside an active trace context (either
   via ``@agentops.trace``, ``tracer.start_trace()``, or manually via
   ``with tracer.start_trace(...) as ctx``).  If there is no active trace,
   a ``RuntimeError`` is raised at call time.
"""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable, Dict, Optional, TypeVar

from .context import get_current_trace
from .globals import get_tracer

logger = logging.getLogger(__name__)

_F = TypeVar("_F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# @agentops.trace
# ---------------------------------------------------------------------------

def trace(
    agent_name: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Callable[[_F], _F]:
    """
    Module-level decorator factory that traces an entire function call.

    Equivalent to ``tracer.trace(...)`` but uses the global tracer singleton.
    Call :func:`agentops.init` before using this decorator.

    Parameters
    ----------
    agent_name:
        Display name for this agent in the AgentOps UI.
    session_id:
        Optional session ID to group related traces.
    metadata:
        Initial trace-level metadata dict.

    Returns
    -------
    Callable
        A decorator that wraps sync/async functions with a trace.

    Raises
    ------
    RuntimeError
        At decoration time if :func:`agentops.init` has not been called,
        **or** at call time if the tracer was cleaned up.

    Example
    -------
    >>> @agentops.trace(agent_name="summariser", session_id="s-1")
    ... def summarise(text: str) -> str:
    ...     return text[:100]

    >>> @agentops.trace(agent_name="async-agent")
    ... async def async_agent(prompt: str) -> str:
    ...     return await some_async_op(prompt)
    """
    def decorator(func: _F) -> _F:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = get_tracer()
                call_meta = dict(metadata or {})
                ctx = tracer.start_trace(agent_name, session_id=session_id, metadata=call_meta)
                async with ctx:
                    return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = get_tracer()
                call_meta = dict(metadata or {})
                ctx = tracer.start_trace(agent_name, session_id=session_id, metadata=call_meta)
                with ctx:
                    return func(*args, **kwargs)

            return sync_wrapper  # type: ignore[return-value]

    return decorator  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# @agentops.span
# ---------------------------------------------------------------------------

def span(
    name: str,
    span_type: str = "custom",
    metadata: Optional[Dict[str, Any]] = None,
) -> Callable[[_F], _F]:
    """
    Module-level decorator factory that wraps a function in a child span.

    The span is attached to the **currently active** trace context in the
    calling thread.  You must have an active trace (started via
    ``@agentops.trace``, ``tracer.start_trace()``, or ``agentops.init()``)
    before this decorator's wrapped function is *called* (not at definition
    time).

    Parameters
    ----------
    name:
        Human-readable label for this span.
    span_type:
        Category string.  Recommended values: ``"llm"``, ``"tool"``,
        ``"retrieval"``, ``"chain"``, ``"custom"``.
    metadata:
        Initial span-level metadata key-value pairs.

    Returns
    -------
    Callable
        A decorator that wraps sync/async functions with a span.

    Raises
    ------
    RuntimeError
        At call time if there is no active trace context in the current thread.

    Example
    -------
    >>> @agentops.span(name="fetch-context", span_type="retrieval")
    ... def fetch_context(query: str) -> list:
    ...     return []

    >>> @agentops.span(name="async-llm", span_type="llm")
    ... async def call_llm(prompt: str) -> str:
    ...     return await llm.acomplete(prompt)
    """
    def decorator(func: _F) -> _F:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                ctx = get_current_trace()
                if ctx is None:
                    raise RuntimeError(
                        f"@agentops.span('{name}') was called but there is no active trace. "
                        "Ensure the calling function is wrapped with @agentops.trace or "
                        "called inside a 'with tracer.start_trace(...)' block."
                    )
                span_ctx = ctx.add_span(name, span_type=span_type)
                async with span_ctx:
                    for k, v in (metadata or {}).items():
                        span_ctx.set_metadata(k, v)
                    return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                ctx = get_current_trace()
                if ctx is None:
                    raise RuntimeError(
                        f"@agentops.span('{name}') was called but there is no active trace. "
                        "Ensure the calling function is wrapped with @agentops.trace or "
                        "called inside a 'with tracer.start_trace(...)' block."
                    )
                span_ctx = ctx.add_span(name, span_type=span_type)
                with span_ctx:
                    for k, v in (metadata or {}).items():
                        span_ctx.set_metadata(k, v)
                    return func(*args, **kwargs)

            return sync_wrapper  # type: ignore[return-value]

    return decorator  # type: ignore[return-value]
