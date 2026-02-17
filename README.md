# marketplace-copilot

Marketplace Seller Intelligence Copilot is a FastAPI + LangGraph multi-agent backend for marketplace sellers (Amazon, Flipkart, Meesho, Myntra). It analyzes seller data, policy docs (RAG), and returns structured action plans.

## Local Architecture (default)

- API: FastAPI (`/api/v1/analyze`)
- Warehouse: DuckDB built from `data/seller/*.csv`
- RAG: OpenSearch local index seeded from `data/rag/index/chunks.jsonl`
- LLM: Hybrid provider
  - primary local Ollama (`qwen3:14b`)
  - fallback Groq API
- Observability (required local default): Alloy + Loki + Tempo + Prometheus + Grafana

## 1) Prerequisites

- Python 3.10+
- Docker + Docker Compose
- Ollama installed and running on host (`http://localhost:11434`)
- Optional Groq key for fallback

Install model:

```bash
ollama pull qwen3:14b
```

## 2) Environment

```bash
cp .env.example .env
```

Set at least:

- `COPILOT_LLM_PROVIDER=hybrid`
- `COPILOT_OLLAMA_MODEL=qwen3:14b`
- `COPILOT_GROQ_API_KEY=<optional-for-fallback>`
- `COPILOT_RAG_BACKEND=opensearch`
- `COPILOT_OPENSEARCH_URL=http://localhost:9200`

## 3) Install Python dependencies

```bash
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

## 4) Exact local run order

```bash
make init-warehouse
make build-rag-index
make os-up
make os-seed
docker compose up -d alloy loki tempo prometheus grafana
make api-run
```

## 5) Smoke checks

Health:

```bash
curl -sS http://localhost:8000/api/v1/health
```

Analyze:

```bash
make smoke-analyze
```

Metrics:

```bash
curl -sS http://localhost:8000/metrics
```

## 6) Full Docker mode

```bash
docker compose up --build
```

This runs warehouse init, RAG index build, OpenSearch seed, API, and observability stack.

## 7) Key endpoints

- `GET /api/v1/health`
- `POST /api/v1/analyze`
- `POST /api/v1/feedback`
- `POST /api/v1/debug/sql` (safe read-only SQL for demos)
- `GET /metrics`
- Docs: `/api/docs`

## 8) Custom evals (interview demo)

The repo includes custom eval fixtures in `eval/`:

- `eval/golden_scenarios.jsonl` for end-to-end copilot behavior
- `eval/rag_golden.jsonl` for RAG retrieval quality

Run:

```bash
make eval-custom
```

This prints a JSON report with pass/fail details per case.

## 9) Prompt management

Prompts are stored in Markdown under `prompts/` and loaded via `backend/app/core/prompt.py`.
No prompt text is hardcoded in agent code.
