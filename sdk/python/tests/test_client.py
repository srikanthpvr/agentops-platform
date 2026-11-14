"""
tests/test_client.py
====================
Unit tests for the AgentOps Python SDK.
"""

import pytest
from unittest.mock import MagicMock, patch
import agentops
from agentops.client import AgentOpsClient
from agentops.tracer import Tracer


def test_sdk_init():
    tracer = agentops.init(api_key="ao_live_testkey12345678901234567890", base_url="http://localhost:8000")
    assert tracer is not None
    assert agentops.globals._client is not None
    assert agentops.globals._client.api_key == "ao_live_testkey12345678901234567890"


def test_sync_trace_decorator():
    tracer = agentops.init(api_key="ao_live_testkey12345678901234567890")

    with patch.object(tracer.client, "enqueue") as mock_enqueue:
        @tracer.trace("calculator-agent")
        def add(a: int, b: int) -> int:
            return a + b

        result = add(2, 3)
        assert result == 5
        assert mock_enqueue.called
        trace_payload = mock_enqueue.call_args[0][0]
        assert trace_payload["agent_name"] == "calculator-agent"
        assert trace_payload["status"] == "ok"


def test_context_manager_manual_spans():
    tracer = agentops.init(api_key="ao_live_testkey12345678901234567890")

    with patch.object(tracer.client, "enqueue") as mock_enqueue:
        with tracer.start_trace("custom-agent", session_id="test-sess-1") as ctx:
            with ctx.add_span("llm-call", span_type="llm") as span:
                span.set_model("gpt-4o", tokens_input=50, tokens_output=20)
                span.set_input("What is 1+1?")
                span.set_output("2")

        assert mock_enqueue.called
        trace_payload = mock_enqueue.call_args[0][0]
        assert trace_payload["agent_name"] == "custom-agent"
        assert trace_payload["session_id"] == "test-sess-1"
        assert len(trace_payload["spans"]) == 1
        assert trace_payload["spans"][0]["model"] == "gpt-4o"
        assert trace_payload["spans"][0]["tokens_input"] == 50
