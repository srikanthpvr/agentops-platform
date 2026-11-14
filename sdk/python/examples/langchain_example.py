"""
langchain_example.py
====================
AgentOps SDK — LangChain integration example using a mock LLM.

This example demonstrates how to use ``AgentOpsCallbackHandler`` with a real
LangChain ``LLMChain`` pipeline **without** needing a real OpenAI API key.
It uses LangChain's ``FakeListLLM`` as a drop-in mock LLM.

Prerequisites
-------------
Install the langchain extra::

    pip install "agentops-sdk[langchain]"
    pip install langchain langchain-community

Run with::

    python langchain_example.py

Replace "ao_live_REPLACE_ME" with your real AgentOps API key to ship traces
to the platform.
"""

from __future__ import annotations

import logging

logging.basicConfig(level=logging.WARNING)

# ---------------------------------------------------------------------------
# Imports — guard against missing langchain
# ---------------------------------------------------------------------------
try:
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    from langchain_community.llms.fake import FakeListLLM
except ImportError:
    print(
        "LangChain packages not found.  Install with:\n"
        "  pip install langchain langchain-community\n"
        "  pip install 'agentops-sdk[langchain]'"
    )
    raise SystemExit(1)

import agentops
from agentops.integrations.langchain_callback import AgentOpsCallbackHandler

# ---------------------------------------------------------------------------
# Initialise the AgentOps SDK
# ---------------------------------------------------------------------------
agentops.init(
    api_key="ao_live_REPLACE_ME",   # ← replace with your real API key
    flush_interval=1.0,
    debug=False,
)

print("=" * 60)
print("AgentOps + LangChain Integration Example")
print("=" * 60)

# ---------------------------------------------------------------------------
# Build the callback handler
# ---------------------------------------------------------------------------
handler = AgentOpsCallbackHandler(
    agent_name="langchain-poet-agent",
    metadata={"example": "langchain_example.py", "task": "poetry-generation"},
)

# ---------------------------------------------------------------------------
# Example 1 — Simple LLMChain with FakeListLLM
# ---------------------------------------------------------------------------
print("\n--- Example 1: Simple LLMChain ---")

# FakeListLLM cycles through the given responses deterministically.
fake_responses = [
    "Roses are red,\nAgentOps is blue,\nTracing your agents,\nIs easy to do.",
    "Bytes flow like rivers,\nModels dream in math,\nAgentOps records,\nEvery neural path.",
]

fake_llm = FakeListLLM(responses=fake_responses)

prompt = PromptTemplate(
    input_variables=["topic"],
    template="Write a short poem about {topic}.",
)

chain = LLMChain(
    llm=fake_llm,
    prompt=prompt,
    callbacks=[handler],  # attach the AgentOps callback handler
    verbose=False,
)

topics = ["artificial intelligence", "machine learning"]
for topic in topics:
    result = chain.run({"topic": topic})
    print(f"\nTopic: {topic}")
    print(f"Poem:\n{result}")

# ---------------------------------------------------------------------------
# Example 2 — Nested chains (chain-of-thought pattern)
# ---------------------------------------------------------------------------
print("\n--- Example 2: Nested Chain-of-Thought ---")

thought_responses = ["First, let me think about the key themes...", "The main concept is observability."]
answer_responses = ["AgentOps provides real-time observability for AI agents."]

thought_llm = FakeListLLM(responses=thought_responses)
answer_llm = FakeListLLM(responses=answer_responses)

thought_prompt = PromptTemplate(
    input_variables=["question"],
    template="Think step by step about: {question}",
)
answer_prompt = PromptTemplate(
    input_variables=["question", "thoughts"],
    template="Given these thoughts: {thoughts}\nAnswer concisely: {question}",
)

thought_chain = LLMChain(
    llm=thought_llm,
    prompt=thought_prompt,
    output_key="thoughts",
    callbacks=[handler],
)
answer_chain = LLMChain(
    llm=answer_llm,
    prompt=answer_prompt,
    output_key="answer",
    callbacks=[handler],
)

from langchain.chains import SequentialChain  # noqa: E402

sequential = SequentialChain(
    chains=[thought_chain, answer_chain],
    input_variables=["question"],
    output_variables=["thoughts", "answer"],
    callbacks=[handler],
    verbose=False,
)

cot_result = sequential({"question": "What is AgentOps?"})
print(f"\nQuestion: What is AgentOps?")
print(f"Thoughts: {cot_result['thoughts']}")
print(f"Answer: {cot_result['answer']}")

# ---------------------------------------------------------------------------
# Flush and finish
# ---------------------------------------------------------------------------
print("\n--- Flushing traces ---")
agentops.flush()
print("All LangChain traces flushed.  Example complete.")
