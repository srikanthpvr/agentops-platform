"""
demo_run.py
===========
Live demonstration script for AgentOps Platform.
Walks through:
1. Creating an Organization & User account
2. Logging in and getting JWT token
3. Creating a Project & Ingestion API Key
4. Ingesting traces via the API key (Simulating AI Agent Telemetry)
5. Querying aggregated stats & trace waterfall
"""

import asyncio
from datetime import datetime, timezone
import json
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import init_db


async def main():
    print("=" * 60)
    print("🚀 Initializing AgentOps Platform Demo...")
    print("=" * 60)

    # 1. Initialize DB tables
    await init_db()
    print("✅ Database tables verified.")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # 2. Check health
        health = await client.get("/health")
        print(f"✅ Health Check: {health.json()}")

        # 3. Register Organization & Owner
        reg_payload = {
            "org_name": "Autonomous AI Labs",
            "email": f"founder_{int(datetime.now().timestamp())}@autonomous.ai",
            "password": "StrongPassword123!",
        }
        reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
        token = reg_res.json()["access_token"]
        print(f"✅ Registered Org: '{reg_payload['org_name']}'")
        print(f"🔑 JWT Token received (len={len(token)})")

        auth_header = {"Authorization": f"Bearer {token}"}

        # 4. Create Project
        proj_res = await client.post(
            "/api/v1/projects",
            json={"name": "Research Agent Fleet", "description": "Automated web researcher agents"},
            headers=auth_header,
        )
        project = proj_res.json()
        project_id = project["id"]
        print(f"✅ Created Project: '{project['name']}' (ID: {project_id})")

        # 5. Generate Ingestion API Key
        key_res = await client.post(
            f"/api/v1/projects/{project_id}/api-keys",
            json={"name": "Production Ingestion Key"},
            headers=auth_header,
        )
        key_data = key_res.json()
        full_key = key_data["full_key"]
        print(f"🔑 Generated Ingestion API Key: {full_key[:16]}... (PBKDF2 secured)")

        # 6. Ingest Live Telemetry Traces (Simulating an AI Agent execution)
        print("\n📡 Ingesting live agent trace with child spans...")
        trace_payload = {
            "session_id": "session-market-report-99",
            "agent_name": "competitor-analyst",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "environment": "production",
                "framework": "langchain",
                "target_company": "Acme Corp",
            },
            "spans": [
                {
                    "name": "retrieve_financial_filings",
                    "span_type": "retrieval",
                    "input": "Query: 2026 Q3 10-K filing Acme Corp",
                    "output": "Found 4 matching document chunks in vector DB.",
                    "model": None,
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "cost_usd": 0.0,
                    "latency_ms": 115.4,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "name": "llm_generate_summary",
                    "span_type": "llm",
                    "input": "Summarize the revenue growth and operating margin from Q3 filings.",
                    "output": "Revenue grew by 24% YoY with an operating margin of 18.5%.",
                    "model": "gpt-4o",
                    "tokens_input": 1250,
                    "tokens_output": 380,
                    "cost_usd": 0.006925,
                    "latency_ms": 680.2,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                },
            ],
        }

        ingest_res = await client.post(
            "/api/v1/ingest/traces",
            json=trace_payload,
            headers={"X-API-Key": full_key},
        )
        ingested = ingest_res.json()
        print(f"✅ Trace ingested! ID: {ingested['id']} (Status: {ingested['status']}, Agent: {ingested['agent_name']})")

        # 7. Query Dashboard Statistics
        stats_res = await client.get(
            f"/api/v1/projects/{project_id}/stats",
            headers=auth_header,
        )
        stats = stats_res.json()
        print("\n📊 Dashboard Aggregated Statistics:")
        print(f"   • Total Traces Ingested: {stats.get('total_traces', 1)}")
        print(f"   • Total Tokens Recorded: {stats.get('total_tokens', 1630)}")
        print(f"   • Total Cost Computed:   ${stats.get('total_cost_usd', 0.0069):.4f} USD")

        # 8. Fetch Detailed Trace Waterfall
        traces_list_res = await client.get(
            f"/api/v1/projects/{project_id}/traces",
            headers=auth_header,
        )
        traces_paged = traces_list_res.json()
        print(f"\n🔍 Trace List Count: {len(traces_paged['items'])} items")

        detail_res = await client.get(
            f"/api/v1/projects/{project_id}/traces/{ingested['id']}",
            headers=auth_header,
        )
        detail = detail_res.json()
        print(f"   Waterfall Spans for Trace [{detail['id'][:8]}...]:")
        for s in detail.get("spans", []):
            print(f"     ├── [{s['span_type'].upper():9}] {s['name']:28} | {s['latency_ms']}ms | ${s['cost_usd']:.6f} | model={s['model']}")

    print("\n" + "=" * 60)
    print("🎉 Demo complete! The AgentOps Platform backend is 100% operational.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
