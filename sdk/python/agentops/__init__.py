"""
agentops
========
AgentOps Platform SDK — observability, tracing, and evaluation for AI agents.

Public API
----------
The public surface of this package is intentionally small.  Import and
use the symbols below; everything prefixed with ``_`` is private.

Quick start
-----------
>>> import agentops
>>>
>>> # Initialise once at startup.
>>> tracer = agentops.init(api_key="ao_live_your_key_here")
>>>
>>> # Decorator usage
>>> @agentops.trace(agent_name="my-agent")
... def run(query: str) -> str:
...     return "result"
>>>
>>> # Context manager usage
>>> with tracer.start_trace("document-processor") as ctx:
...     with ctx.add_span("parse", span_type="tool") as s:
...         s.set_input("file.pdf")
...         s.set_output("text content")
>>>
>>> # Force flush before process exit
>>> agentops.flush()
"""

# ---------------------------------------------------------------------------
# Core classes (re-exported for direct import convenience)
# ---------------------------------------------------------------------------
from .client import AgentOpsClient
from .context import TraceContext
from .models import SDKConfig, SpanData, TraceData
from .span import SpanContext
from .tracer import Tracer

# ---------------------------------------------------------------------------
# Module-level functions
# ---------------------------------------------------------------------------
from .decorators import span, trace
from .globals import configure, flush, get_tracer, init

__all__ = [
    # Initialisation
    "init",
    "configure",
    "flush",
    "get_tracer",
    # Decorators
    "trace",
    "span",
    # Classes
    "AgentOpsClient",
    "Tracer",
    "TraceContext",
    "SpanContext",
    # Pydantic models
    "SDKConfig",
    "TraceData",
    "SpanData",
]

__version__ = "0.1.0"
