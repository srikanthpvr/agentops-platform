# AgentOps SDK

**Observability, tracing, and evaluation for AI agents — zero-friction Python SDK.**

[![PyPI](https://img.shields.io/pypi/v/agentops-sdk)](https://pypi.org/project/agentops-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/agentops-sdk)](https://pypi.org/project/agentops-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Decorator Usage](#decorator-usage)
- [Context Manager Usage](#context-manager-usage)
- [Manual Span Instrumentation](#manual-span-instrumentation)
- [Async Support](#async-support)
- [LangChain Integration](#langchain-integration)
- [OpenAI Auto-Patching](#openai-auto-patching)
- [Configuration Options](#configuration-options)
- [Public API Reference](#public-api-reference)

---

## Installation

```bash
pip install agentops-sdk
```

**With LangChain integration:**

```bash
pip install "agentops-sdk[langchain]"
```

**With OpenAI auto-patching:**

```bash
pip install "agentops-sdk[openai]"
```

**With all extras:**

```bash
pip install "agentops-sdk[langchain,openai]"
```

---

## Quick Start

```python
import agentops

# Initialize once at application startup.
# The API key can also be provided via the AGENTOPS_API_KEY environment variable.
tracer = agentops.init(api_key="ao_live_your_key_here")

@agentops.trace(agent_name="summariser-agent")
def summarise(text: str) -> str:
    # Your agent logic here
    return f"Summary of: {text[:50]}..."

result = summarise("Long document text goes here...")
print(result)

# Always flush/close at the end of your process to ensure all traces are sent.
agentops.flush()
```

---

## Decorator Usage

The `@agentops.trace` decorator is the simplest way to instrument an entire agent run.

```python
import agentops

agentops.init(api_key="ao_live_your_key_here")

@agentops.trace(agent_name="research-agent", session_id="session-abc-123")
def research_agent(query: str) -> dict:
    """Agent that researches a topic."""
    # Simulate LLM calls, tool use, etc.
    return {"query": query, "result": "...", "sources": []}

# Works identically for async functions:
@agentops.trace(agent_name="async-research-agent")
async def async_research_agent(query: str) -> dict:
    import asyncio
    await asyncio.sleep(0.1)  # Simulated async I/O
    return {"query": query, "result": "..."}
```

You can also use the `@agentops.span` decorator for sub-operations:

```python
@agentops.span(name="fetch-context", span_type="retrieval")
def fetch_context(query: str) -> list:
    # e.g. vector-store lookup
    return ["doc1", "doc2"]

@agentops.span(name="call-llm", span_type="llm")
def call_llm(prompt: str) -> str:
    return "LLM response"
```

---

## Context Manager Usage

For fine-grained control, use the `TraceContext` as a context manager:

```python
import agentops

tracer = agentops.init(api_key="ao_live_your_key_here")

with tracer.start_trace("document-processor", metadata={"doc_id": "d-42"}) as ctx:
    # Add custom metadata at any point
    ctx.metadata["page_count"] = 10

    with ctx.add_span("parse-pdf", span_type="tool") as span:
        span.set_input("document.pdf")
        # ... parse logic ...
        span.set_output("Extracted 1000 tokens")
        span.set_metadata("pages_processed", 10)

    with ctx.add_span("generate-summary", span_type="llm") as span:
        span.set_input("Summarise this document...")
        # ... LLM call ...
        span.set_output("This document describes...")
        span.set_model("gpt-4o", tokens_input=800, tokens_output=200)

# Trace is automatically sent to the platform when the `with` block exits.
```

---

## Manual Span Instrumentation

```python
import agentops

tracer = agentops.init(api_key="ao_live_your_key_here")

ctx = tracer.start_trace("pipeline-agent")
try:
    span = ctx.add_span("step-1", span_type="tool")
    span.__enter__()
    span.set_input("input data")
    span.set_output("output data")
    span.__exit__(None, None, None)
finally:
    ctx.__exit__(None, None, None)
```

---

## Async Support

All APIs have full async counterparts:

```python
import asyncio
import agentops

async def main():
    tracer = agentops.init(api_key="ao_live_your_key_here")

    async with tracer.start_trace("async-agent") as ctx:
        async with ctx.add_span("async-llm-call", span_type="llm") as span:
            span.set_input("What is the capital of France?")
            await asyncio.sleep(0.5)  # async LLM call
            span.set_output("Paris")
            span.set_model("gpt-4o-mini", tokens_input=15, tokens_output=5)

asyncio.run(main())
```

---

## LangChain Integration

```python
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

import agentops
from agentops.integrations.langchain_callback import AgentOpsCallbackHandler

agentops.init(api_key="ao_live_your_key_here")

handler = AgentOpsCallbackHandler(agent_name="langchain-summariser")

llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])
prompt = PromptTemplate.from_template("Summarise: {text}")
chain = LLMChain(llm=llm, prompt=prompt, callbacks=[handler])

result = chain.run(text="AgentOps makes AI observable.")
```

The callback handler automatically creates a trace and spans for every LLM call,
chain invocation, and tool use — no manual instrumentation needed.

---

## OpenAI Auto-Patching

```python
import openai
import agentops
from agentops.integrations.openai_patch import patch_openai, unpatch_openai

agentops.init(api_key="ao_live_your_key_here")

# Monkey-patch openai so every call is auto-traced
patch_openai()

client = openai.OpenAI(api_key="sk-...")
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Restore original behaviour
unpatch_openai()
```

---

## Configuration Options

| Option | Environment Variable | Type | Default | Description |
|---|---|---|---|---|
| `api_key` | `AGENTOPS_API_KEY` | `str` | — | **Required.** Your AgentOps API key. |
| `base_url` | `AGENTOPS_BASE_URL` | `str` | `https://api.agentops.io` | Backend endpoint. |
| `timeout` | `AGENTOPS_TIMEOUT` | `float` | `30.0` | HTTP request timeout in seconds. |
| `batch_size` | `AGENTOPS_BATCH_SIZE` | `int` | `10` | Number of traces to batch before flushing. |
| `flush_interval` | `AGENTOPS_FLUSH_INTERVAL` | `float` | `5.0` | Background flush interval in seconds. |
| `max_retries` | — | `int` | `3` | Max HTTP retry attempts with exponential back-off. |
| `debug` | `AGENTOPS_DEBUG` | `bool` | `False` | Enable verbose SDK logging. |

---

## Public API Reference

### Module-level functions

| Function | Signature | Description |
|---|---|---|
| `init` | `(api_key, base_url, **kwargs) -> Tracer` | Initialise the global SDK. Call once at startup. |
| `configure` | `(**kwargs)` | Update configuration after init. |
| `trace` | `(agent_name, session_id, metadata) -> Callable` | Decorator factory for tracing a function. |
| `span` | `(name, span_type, metadata) -> Callable` | Decorator factory for a single span. |
| `flush` | `()` | Force-flush all buffered traces to the backend. |
| `get_tracer` | `() -> Tracer` | Return the global `Tracer` instance. |

### `Tracer`

| Method | Description |
|---|---|
| `start_trace(agent_name, session_id, metadata)` | Begin a new trace; returns `TraceContext`. |
| `trace(agent_name, session_id, metadata)` | Decorator factory (sync + async). |

### `TraceContext`

| Attribute / Method | Description |
|---|---|
| `trace_id` | UUID of this trace. |
| `metadata` | Mutable dict attached to the trace. |
| `add_span(name, span_type, **kwargs)` | Create a child `SpanContext`. |
| `__enter__` / `__exit__` | Synchronous context manager. |
| `__aenter__` / `__aexit__` | Asynchronous context manager. |

### `SpanContext`

| Attribute / Method | Description |
|---|---|
| `span_id` | UUID of this span. |
| `set_input(text)` | Record the input to this span. |
| `set_output(text)` | Record the output of this span. |
| `set_model(model, tokens_input, tokens_output)` | Record model usage and auto-calculate cost. |
| `set_metadata(key, value)` | Attach arbitrary metadata. |
| `__enter__` / `__exit__` | Synchronous context manager. |
| `__aenter__` / `__aexit__` | Asynchronous context manager. |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Run the test suite with:

```bash
pip install -e ".[dev]"
pytest
```
