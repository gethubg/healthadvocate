# HealthAdvocate

A production-grade **RAG application for personal bloodwork analysis**. Upload your lab
report PDFs, ask natural-language questions about your results, visualize how individual
attributes trend over time, and — when a value falls outside its reference range — get
live, web-sourced guidance on foods to avoid for that specific parameter.

> ⚠️ **Not medical advice.** HealthAdvocate is an informational tool. See
> [docs/SAFETY_DISCLAIMER.md](docs/SAFETY_DISCLAIMER.md). Always consult a qualified
> clinician about your results.

---

## What it does

1. **Upload** bloodwork PDFs with a user-entered **report date** (the blood-draw date).
   Files are stored on disk; structured lab values are parsed out; text chunks are
   embedded into Pinecone.
2. **Ask** questions about your bloodwork. Answers are grounded in your **latest report**
   (the one with the most recent `report_date`).
3. **Detect abnormalities** deterministically by comparing each value against the
   reference range printed in the report itself.
4. **Advise** — for any abnormal parameter, a LangChain agent runs a live DuckDuckGo
   search and synthesizes a cited "foods to avoid" list.
5. **Trends** — chart any attribute over a chosen date range, with the normal band
   shaded and out-of-range points highlighted.

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.12 |
| RAG / indexing | LlamaIndex |
| Vector store | Pinecone |
| Embeddings + LLM | OpenAI (`text-embedding-3-small` + a GPT-4-class model) |
| Agentic web search | LangChain + DuckDuckGo (no API key) |
| Structured store | SQLite (trends & analysis) |
| API | FastAPI |
| Frontend | React + Vite (Recharts for charts) |

## Architecture at a glance

Two stores, one source of truth for dates:

- **Pinecone** — semantic chunks for the **Ask** tab.
- **SQLite** — structured `(parameter, value, unit, report_date, ref_low, ref_high)`
  rows for the **Trends** tab and abnormality analysis.
- The user-entered **`report_date`** is the backbone for both "latest report" logic and
  the trend x-axis.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/DATA_FLOW.md](docs/DATA_FLOW.md).

## Tabs

| Tab | Purpose |
|-----|---------|
| **Upload** | Drag-drop a PDF + enter the report date (auto pre-filled from the PDF when detected). |
| **Ask** | Chat grounded in the latest report; abnormal findings + foods-to-avoid cards. |
| **Trends** | Pick a parameter and date range; line chart with shaded reference band. |

## Documentation

- [PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md) — use cases, diagrams, stack, lessons learned
- [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) — phased build plan and milestones
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — components, stores, and decisions
- [DATA_FLOW.md](docs/DATA_FLOW.md) — ingestion, query, and trend flows
- [API.md](docs/API.md) — REST endpoints
- [SAFETY_DISCLAIMER.md](docs/SAFETY_DISCLAIMER.md) — scope and limitations

## Running locally

You need an **OpenAI API key** and a **Pinecone API key** (create an index, default name
`healthadvocate`). DuckDuckGo needs no key.

### Option A — Docker Compose (everything at once)

```bash
cp backend/.env.example backend/.env   # fill in keys (or export them in your shell)
export OPENAI_API_KEY=sk-...
export PINECONE_API_KEY=...
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend API + docs: http://localhost:8000/docs

### Option B — Run the two services directly

**Backend** (Python 3.12):

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # fill in OPENAI_API_KEY and PINECONE_API_KEY
uvicorn healthadvocate.api.main:app --reload
```

**Frontend** (Node 20+):

```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_BASE defaults to http://localhost:8000
npm run dev                 # http://localhost:5173
```

## Testing & quality

```bash
cd backend
pytest                                   # full suite
pytest --cov=healthadvocate              # with coverage (86%+)
ruff check src tests                     # lint

cd ../frontend
npm run build                            # type-check + production build
```

## Status

✅ **Implemented.** Backend pipeline (ingestion → analysis → retrieval → advisory) and
the three-tab React frontend are complete and tested. Live OpenAI/Pinecone/DuckDuckGo
paths sit behind injectable seams and run with real keys.
