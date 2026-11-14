"""
agentops.tracer
===============
``Tracer`` — the primary high-level interface for creating traces.

Instances are created by :func:`agentops.init` and stored in the global
singleton.  Users can also instantiate ``Tracer`` directly when they need
multiple independent tracers (e.g. in a multi-tenant service).

Usage
-----
Via the global singleton (most common):

>>> import agentops
>>> tracer = agentops.init(api_key="ao_live_xxx")
>>> with tracer.start_trace("my-agent") as ctx:
...     ...

Via decorator:

>>> @tracer.trace("research-agent", session_id="s-123")
... def research(query: str) -> str:
...     return "result"
"""

from __future__ import annotations

import functools
import inspect
import logging
import uuid
from typing import Any, Callable, Dict, Optional, TypeVar

from .client import AgentOpsClient
from .context import TraceContext

logger = logging.getLogger(__name__)

# Generic type variable used for the decorator to preserve type signatures.
_F = TypeVar("_F", bound=Callable[..., Any])


class Tracer:
    """
    High-level interface for creating and managing traces.

    Parameters
    ----------
    client:
        The :class:`~agentops.client.AgentOpsClient` used to send traces.

    Example
    -------
    >>> client = AgentOpsClient(api_key="ao_live_xxx")
    >>> tracer = Tracer(client=client)
    >>> with tracer.start_trace("my-agent") as ctx:
    ...     pass
    """

    def __init__(self, client: AgentOpsClient) -> None:
        if not isinstance(client, AgentOpsClient):
            raise TypeError(
                f"client must be an AgentOpsClient instance; got {type(client).__name__}"
            )
        self._client = client

    @property
    def client(self) -> AgentOpsClient:
        """The underlying HTTP client."""
        return self._client

    # ------------------------------------------------------------------
    # start_trace — imperative API
    # ------------------------------------------------------------------

    def start_trace(
        self,
        agent_name: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceContext:
        """
        Begin a new trace and return its :class:`~agentops.context.TraceContext`.

        The returned context is a *sync and async* context manager.  When the
        ``with`` block exits the trace is automatically sent.

        Parameters
        ----------
        agent_name:
            Display name for the agent (shown in the AgentOps UI).
        session_id:
            Optional caller-supplied identifier for grouping related traces
            (e.g. a user session ID or request ID).
        metadata:
            Initial metadata key-value pairs.  The ``TraceContext.metadata``
            dict can be mutated during the trace to add more context.

        Returns
        -------
        TraceContext
            An uninitialised trace context.  Call ``__enter__`` (or use ``with``)
            to begin timing.

        Example
        -------
        >>> with tracer.start_trace("document-processor", session_id="s-42") as ctx:
        ...     ctx.metadata["doc_id"] = "d-999"
        ...     with ctx.add_span("parse", span_type="tool") as span:
        ...         span.set_input("document.pdf")
        """
        if not agent_name or not agent_name.strip():
            raise ValueError("agent_name must be a non-empty string.")

        trace_id = str(uuid.uuid4())
        logger.debug(
            "Creating TraceContext for agent='%s' session_id=%s trace_id=%s",
            agent_name,
            session_id,
            trace_id,
        )
        return TraceContext(
            client=self._client,
            trace_id=trace_id,
            agent_name=agent_name,
            session_id=session_id,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # trace — decorator factory
    # ------------------------------------------------------------------

    def trace(
        self,
        agent_name: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Callable[[_F], _F]:
        """
        Decorator factory that wraps a *sync* or *async* function with a trace.

        The decorated function behaves identically to the original but its
        execution is automatically captured as an AgentOps trace.  Exceptions
        are recorded and re-raised.

        Parameters
        ----------
        agent_name:
            Display name for this agent trace.
        session_id:
            Optional grouping session ID.
        metadata:
            Initial trace metadata.

        Returns
        -------
        Callable
            A decorator that accepts a function and returns a wrapped version.

        Example
        -------
        Synchronous:

        >>> @tracer.trace("summariser", session_id="s-1")
        ... def summarise(text: str) -> str:
        ...     return text[:100]

        Asynchronous:

        >>> @tracer.trace("async-summariser")
        ... async def async_summarise(text: str) -> str:
        ...     await asyncio.sleep(0)
        ...     return text[:100]
        """
        def decorator(func: _F) -> _F:
            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    # Build fresh metadata dict per call so it's not shared.
                    call_metadata = dict(metadata or {})
                    ctx = self.start_trace(agent_name, session_id=session_id, metadata=call_metadata)
                    async with ctx:
                        result = await func(*args, **kwargs)
                    return result

                return async_wrapper  # type: ignore[return-value]
            else:
                @functools.wraps(func)
                def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                    call_metadata = dict(metadata or {})
                    ctx = self.start_trace(agent_name, session_id=session_id, metadata=call_metadata)
                    with ctx:
                        result = func(*args, **kwargs)
                    return result

                return sync_wrapper  # type: ignore[return-value]

        return decorator  # type: ignore[return-value]
