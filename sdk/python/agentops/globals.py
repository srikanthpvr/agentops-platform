"""
agentops.globals
================
Module-level singleton state and the top-level ``init()`` / ``configure()``
convenience functions that are re-exported from the ``agentops`` package root.

Call :func:`init` once at application startup.  All subsequent calls to
``agentops.trace()``, ``agentops.span()``, etc. will use the global tracer
created here.

Thread safety
-------------
The global ``_client`` and ``_tracer`` variables are written only during
``init()`` / ``configure()``, which are expected to be called from the main
thread before any worker threads start.  Reads from worker threads are safe
because CPython's GIL ensures reference reads are atomic.

Example
-------
>>> import agentops
>>> tracer = agentops.init(api_key="ao_live_xxx")
>>> agentops.configure(debug=True)
>>> tracer2 = agentops.get_tracer()
>>> assert tracer is tracer2
"""

from __future__ import annotations

import atexit
import logging
from typing import Optional

from .client import AgentOpsClient
from .tracer import Tracer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons — intentionally mutable globals
# ---------------------------------------------------------------------------

_client: Optional[AgentOpsClient] = None
_tracer: Optional[Tracer] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init(
    api_key: str,
    base_url: str = "https://api.agentops.io",
    *,
    timeout: float = 30.0,
    batch_size: int = 10,
    flush_interval: float = 5.0,
    max_retries: int = 3,
    debug: bool = False,
) -> Tracer:
    """
    Initialise the AgentOps SDK global singleton.

    Call this **once** at application startup before any agents run.  Returns
    the global :class:`~agentops.tracer.Tracer` instance for convenience, but
    you can also use the module-level ``agentops.trace()`` / ``agentops.span()``
    decorators directly after calling ``init()``.

    Parameters
    ----------
    api_key:
        Your AgentOps API key.  Can also be set via the ``AGENTOPS_API_KEY``
        environment variable.
    base_url:
        Root URL of the AgentOps ingest endpoint.
    timeout:
        HTTP request timeout in seconds (default: ``30.0``).
    batch_size:
        Traces to buffer before an automatic flush (default: ``10``).
    flush_interval:
        Seconds between background flush sweeps (default: ``5.0``).
    max_retries:
        Max retry attempts with exponential back-off (default: ``3``).
    debug:
        When ``True``, the SDK logs at ``DEBUG`` level (default: ``False``).

    Returns
    -------
    Tracer
        The global tracer instance.

    Raises
    ------
    ValueError
        If ``api_key`` is empty.

    Example
    -------
    >>> import agentops
    >>> tracer = agentops.init(api_key="ao_live_xxx", debug=True)
    """
    global _client, _tracer

    if _client is not None:
        logger.warning(
            "agentops.init() called more than once; reinitialising. "
            "Previous client will be closed."
        )
        _client.close()

    _client = AgentOpsClient(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        batch_size=batch_size,
        flush_interval=flush_interval,
        max_retries=max_retries,
        debug=debug,
    )
    _tracer = Tracer(client=_client)

    # Register cleanup so traces aren't dropped on normal process exit.
    atexit.register(_client.close)

    logger.debug("AgentOps SDK initialised (base_url=%s, debug=%s).", base_url, debug)
    return _tracer


def configure(**kwargs) -> None:
    """
    Update SDK configuration after :func:`init` has been called.

    Re-creates the underlying client with the merged configuration.
    Flushes the existing client before replacing it so no traces are lost.

    Supported keyword arguments mirror :func:`init` parameters:
    ``base_url``, ``timeout``, ``batch_size``, ``flush_interval``,
    ``max_retries``, ``debug``.

    .. note::
        ``api_key`` cannot be changed after init for security reasons.
        Call :func:`init` again with the new key to rotate.

    Parameters
    ----------
    **kwargs:
        Configuration overrides.

    Raises
    ------
    RuntimeError
        If called before :func:`init`.

    Example
    -------
    >>> agentops.configure(debug=True, flush_interval=2.0)
    """
    global _client, _tracer

    if _client is None:
        raise RuntimeError(
            "agentops.configure() called before agentops.init(). "
            "Call agentops.init(api_key=...) first."
        )

    # Grab the existing api_key (can't be changed via configure).
    current_api_key = _client._config.api_key

    # Flush and close the old client gracefully.
    _client.flush()
    _client.close()

    # Merge existing config with overrides.
    old_cfg = _client._config.model_dump()
    old_cfg.pop("api_key", None)  # remove so we re-use current_api_key
    old_cfg.update(kwargs)

    _client = AgentOpsClient(api_key=current_api_key, **old_cfg)
    _tracer = Tracer(client=_client)
    logger.debug("AgentOps SDK reconfigured: %s", kwargs)


def get_tracer() -> Tracer:
    """
    Return the global :class:`~agentops.tracer.Tracer` instance.

    Raises
    ------
    RuntimeError
        If :func:`init` has not been called yet.

    Returns
    -------
    Tracer
        The global tracer.

    Example
    -------
    >>> tracer = agentops.get_tracer()
    >>> with tracer.start_trace("agent") as ctx:
    ...     pass
    """
    if _tracer is None:
        raise RuntimeError(
            "AgentOps SDK is not initialised. Call agentops.init(api_key=...) first."
        )
    return _tracer


def flush() -> None:
    """
    Force an immediate flush of all buffered traces to the backend.

    Blocks until all HTTP requests complete (or retries are exhausted).
    Safe to call at the end of a script or test to ensure traces are sent.

    Raises
    ------
    RuntimeError
        If :func:`init` has not been called yet.

    Example
    -------
    >>> agentops.flush()
    """
    if _client is None:
        raise RuntimeError(
            "AgentOps SDK is not initialised. Call agentops.init(api_key=...) first."
        )
    _client.flush()
