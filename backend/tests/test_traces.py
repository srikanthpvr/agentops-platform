"""
backend/tests/test_traces.py
============================
Tests for trace and span ingestion via API key and querying via JWT.
"""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from app.models.project import Project
from app.models.user import User


@pytest.mark.asyncio
async def test_trace_ingestion_and_retrieval(
    client: AsyncClient,
    test_project: Project,
    test_user: User,
    test_api_key: tuple,
):
    full_key, _ = test_api_key

    # 1. Ingest trace via SDK API key header
    trace_payload = {
        "session_id": "sess-xyz-123",
        "agent_name": "support-chat-agent",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {"user_id": "u456", "channel": "slack"},
        "spans": [
            {
                "name": "llm_generate_reply",
                "span_type": "llm",
                "input": "How do I reset my password?",
                "output": "Click the 'Forgot Password' link on login.",
                "model": "gpt-4o",
                "tokens_input": 25,
                "tokens_output": 12,
                "cost_usd": 0.00018,
                "latency_ms": 320.5,
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }

    ingest_res = await client.post(
        "/api/v1/ingest/traces",
        json=trace_payload,
        headers={"X-API-Key": full_key},
    )
    assert ingest_res.status_code == 201
    trace_data = ingest_res.json()
    assert trace_data["agent_name"] == "support-chat-agent"
    assert trace_data["session_id"] == "sess-xyz-123"
    trace_id = trace_data["id"]

    # 2. Query trace list via dashboard (JWT auth)
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "SuperSecret123!"},
    )
    token = login_res.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    list_res = await client.get(
        f"/api/v1/projects/{test_project.id}/traces",
        headers=auth_header,
    )
    assert list_res.status_code == 200
    paged = list_res.json()
    assert paged["total"] >= 1
    assert any(t["id"] == trace_id for t in paged["items"])

    # 3. Retrieve single trace detail with spans
    detail_res = await client.get(
        f"/api/v1/projects/{test_project.id}/traces/{trace_id}",
        headers=auth_header,
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == trace_id
    assert len(detail["spans"]) == 1
    assert detail["spans"][0]["model"] == "gpt-4o"
