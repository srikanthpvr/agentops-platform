# 🚀 AgentOps Platform

> Production-grade AI Agent Observability, Evaluation Sandbox & Governance System.

AgentOps is an end-to-end operations platform purpose-built for autonomous AI agents, multi-agent frameworks (LangGraph, CrewAI, AutoGen), and LLM pipelines.

---

## 🌟 The Three Core Pillars

| Pillar | Capability | Key Features |
|---|---|---|
| 🔭 **AgentOps** | Distributed Agent Observability | Sub-millisecond trace ingestion, execution waterfall timeline, LLM token & cost calculations per prompt/session. |
| 🧪 **EvalBox** | Evaluation & Benchmarking Sandbox | Automated datasets, LLM-as-a-Judge grading (relevance, faithfulness, hallucination), side-by-side model comparisons. |
| 🛡️ **GovernAI** | Enterprise Guardrails & Compliance | Real-time PII detection (Presidio), prompt injection filtering, immutable audit logs with severity levels. |

---

## 🏗️ Architecture & Technology Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (Async), PostgreSQL, Redis, Celery, SlowAPI, Pydantic v2.
- **Frontend**: React 18, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Zustand, Recharts, Lucide Icons.
- **SDK**: Ergonomic Python SDK (`agentops-sdk`) supporting `@agentops.trace` decorators, context managers, and LangChain callbacks.
- **Deployment**: Docker, Docker Compose, Nginx.

---

## 📁 Repository Structure

```
AgentOps_platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/         # REST API endpoints (auth, projects, traces, evals, governance)
│   │   ├── core/           # Security, config, database sessions, auth deps
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic v2 schemas & request validation
│   │   ├── services/       # Token pricing & cost computation
│   │   ├── workers/        # Celery background tasks
│   │   └── main.py         # Application factory, CORS, Rate limiting
│   ├── alembic/            # Database schema migrations
│   ├── tests/              # Pytest test suite (auth, traces, API keys)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # shadcn/ui components & layout shell
│   │   ├── hooks/          # React Query custom hooks
│   │   ├── lib/            # Axios API client, formatting utils
│   │   ├── pages/          # Dashboard, Traces, TraceDetail, Evaluations, Governance, Settings
│   │   ├── stores/         # Zustand stores (authStore, projectStore)
│   │   └── router.tsx      # Protected route management
│   ├── Dockerfile
│   └── nginx.conf
├── sdk/python/
│   ├── agentops/           # Core Python client, decorators, context managers
│   ├── agentops/integrations/ # LangChain callback handler & OpenAI auto-patch
│   ├── examples/           # Quickstart and integration guides
│   ├── tests/              # SDK test harness
│   └── pyproject.toml
└── docker-compose.yml       # Orchestrates Postgres, Redis, Backend, Celery & Frontend
```

---

## 🚀 Getting Started

### 1. Start with Docker Compose
```bash
docker-compose up --build
```

- **Frontend Dashboard**: `http://localhost:3000`
- **FastAPI API & Docs**: `http://localhost:8000/docs`
- **Health check**: `http://localhost:8000/health`

---

### 2. Instrumenting your AI Agent with Python SDK

```bash
pip install agentops-sdk
```

```python
import agentops

# Initialize once at application start
tracer = agentops.init(
    api_key="ao_live_your_project_key_here",
    base_url="http://localhost:8000"
)

# Option A: Function decorator
@tracer.trace(agent_name="research-agent")
def run_research(query: str):
    return "Market insights report..."

# Option B: Context manager with sub-spans
with tracer.start_trace(agent_name="support-bot", session_id="user-123") as trace:
    with trace.add_span("llm_call", span_type="llm") as span:
        span.set_model("gpt-4o", tokens_input=120, tokens_output=45)
        span.set_input("How to upgrade?")
        span.set_output("Navigate to Settings > Plan & Billing.")
```

---

## 🧪 Running Automated Tests

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### SDK Tests
```bash
cd sdk/python
pytest tests/ -v
```

---

## 💳 Business & Monetization Architecture

- **Freemium Tier**: Free for up to 10,000 traces/mo, 1 project.
- **Pro Tier (\$49/mo)**: 500,000 traces, custom evaluation suites, Slack webhook alerts.
- **Enterprise Tier (Custom)**: Dedicated database instance, custom data retention policies, SSO / SAML, on-prem deployment.
