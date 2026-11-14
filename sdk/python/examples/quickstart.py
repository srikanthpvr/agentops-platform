"""
quickstart.py
=============
AgentOps SDK — complete quick-start example.

This script demonstrates every major feature of the SDK using only the
agentops package itself (no real API key or external services required for
the structural demonstration).  Network calls are skipped because the fake
API key will produce a client-side error that is logged as a warning (not
raised), so the script still runs end-to-end.

Run with:
    python quickstart.py

To actually ship data to AgentOps, replace "ao_live_REPLACE_ME" with your
real API key from https://app.agentops.io.
"""

from __future__ import annotations

import asyncio
import logging

# ---------------------------------------------------------------------------
# Step 0 — optional verbose SDK logging (remove in production)
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.WARNING)

# ---------------------------------------------------------------------------
# Step 1 — Initialise the SDK once at startup
# ---------------------------------------------------------------------------
import agentops

tracer = agentops.init(
    api_key="ao_live_REPLACE_ME",   # ← replace with your real key
    debug=False,                     # set True to see verbose SDK logs
    flush_interval=1.0,              # flush quickly for demo purposes
)

print("=" * 60)
print("AgentOps SDK Quick-Start Demo")
print("=" * 60)


# ===========================================================================
# Example 1 — Decorator usage (simplest pattern)
# ===========================================================================

@agentops.trace(agent_name="summariser-agent", metadata={"version": "v1"})
def run_summariser(text: str) -> str:
    """Fake summariser agent wrapped with the @agentops.trace decorator."""
    # Simulate some work
    words = text.split()
    summary = " ".join(words[:10]) + "..." if len(words) > 10 else text
    return f"Summary: {summary}"


print("\n--- Example 1: Decorator ---")
result = run_summariser(
    "AgentOps makes it trivially easy to add production-grade observability "
    "to any Python AI agent without boilerplate."
)
print(f"Result: {result}")


# ===========================================================================
# Example 2 — Context manager with manual spans
# ===========================================================================

print("\n--- Example 2: Context Manager + Spans ---")

with tracer.start_trace("document-processor", metadata={"doc_id": "doc-42"}) as ctx:
    # Mutate metadata at any point during the trace
    ctx.metadata["page_count"] = 5

    # Span 1 — simulated PDF parsing
    with ctx.add_span("parse-pdf", span_type="tool") as span:
        span.set_input("quarterly_report.pdf")
        # ... real parsing would happen here ...
        span.set_output("Extracted 1,200 tokens from 5 pages")
        span.set_metadata("pages", 5)
        span.set_metadata("file_size_kb", 128)
        print("  [span] parse-pdf completed")

    # Span 2 — simulated LLM call
    with ctx.add_span("generate-summary", span_type="llm") as span:
        prompt = "Summarise the following financial report in 3 bullet points..."
        span.set_input(prompt)
        # ... real LLM call would happen here ...
        span.set_output("• Revenue grew 12%\n• Net income +8%\n• New markets entered")
        span.set_model("gpt-4o", tokens_input=800, tokens_output=120)
        print(f"  [span] generate-summary completed (cost: ${span._cost_usd:.6f} USD)")

print("Trace sent (or queued) for document-processor.")


# ===========================================================================
# Example 3 — @agentops.span sub-decorator inside a @agentops.trace
# ===========================================================================

print("\n--- Example 3: Nested @span decorator ---")


@agentops.span(name="fetch-context", span_type="retrieval")
def fetch_context(query: str) -> list:
    """Retrieves relevant documents (simulated)."""
    return [f"doc-{i}" for i in range(3)]


@agentops.span(name="call-llm", span_type="llm")
def call_llm(prompt: str) -> str:
    """Calls an LLM (simulated)."""
    return "The capital of France is Paris."


@agentops.trace(agent_name="qa-agent")
def qa_agent(question: str) -> str:
    """Question-answering agent using nested span decorators."""
    docs = fetch_context(question)
    answer = call_llm(f"Context: {docs}\nQuestion: {question}")
    return answer


answer = qa_agent("What is the capital of France?")
print(f"QA answer: {answer}")


# ===========================================================================
# Example 4 — Async usage
# ===========================================================================

print("\n--- Example 4: Async ---")


async def async_main() -> None:
    @agentops.trace(agent_name="async-research-agent")
    async def async_research(query: str) -> dict:
        """Async agent — uses async context manager internally."""
        # Simulate async I/O (e.g. database lookups, HTTP calls)
        await asyncio.sleep(0.05)
        return {"query": query, "result": "Found 42 relevant papers."}

    result = await async_research("quantum computing applications")
    print(f"Async result: {result}")

    # Explicit async context manager usage:
    async with tracer.start_trace("async-pipeline") as ctx:
        async with ctx.add_span("async-fetch", span_type="retrieval") as span:
            span.set_input("embeddings query")
            await asyncio.sleep(0.01)
            span.set_output("Retrieved 5 chunks")
            span.set_metadata("vector_db", "pinecone")
        print("  Async pipeline trace completed.")


asyncio.run(async_main())


# ===========================================================================
# Example 5 — LangChain callback handler (mock)
# ===========================================================================

print("\n--- Example 5: LangChain Callback Handler (mock) ---")

try:
    from agentops.integrations.langchain_callback import AgentOpsCallbackHandler

    handler = AgentOpsCallbackHandler(
        agent_name="langchain-summariser",
        metadata={"chain_type": "stuff"},
    )

    # Simulate the lifecycle that LangChain would call internally:
    import uuid as _uuid
    root_run_id = _uuid.uuid4()

    # Simulate chain start (root)
    handler.on_chain_start(
        serialized={"id": ["langchain", "chains", "LLMChain"]},
        inputs={"text": "AgentOps is great"},
        run_id=root_run_id,
        parent_run_id=None,
    )

    # Simulate LLM call inside the chain
    llm_run_id = _uuid.uuid4()
    handler.on_llm_start(
        serialized={"kwargs": {"model_name": "gpt-4o-mini"}},
        prompts=["Summarise: AgentOps is great"],
        run_id=llm_run_id,
        parent_run_id=root_run_id,
    )

    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.generations = [[MagicMock(text="AgentOps simplifies AI observability.")]]
    mock_response.llm_output = {
        "token_usage": {"prompt_tokens": 10, "completion_tokens": 8},
        "model_name": "gpt-4o-mini",
    }
    handler.on_llm_end(mock_response, run_id=llm_run_id)

    # Simulate chain end
    handler.on_chain_end(outputs={"output": "Done"}, run_id=root_run_id)
    print("  LangChain callback handler lifecycle completed successfully.")

except RuntimeError as e:
    # SDK not initialised is re-raised as RuntimeError; fine in demo context.
    print(f"  LangChain example skipped (SDK state): {e}")
except Exception as e:
    print(f"  LangChain example skipped: {e}")


# ===========================================================================
# Step 6 — Flush and exit
# ===========================================================================

print("\n--- Flushing traces ---")
agentops.flush()
print("All traces flushed.  Demo complete.")
