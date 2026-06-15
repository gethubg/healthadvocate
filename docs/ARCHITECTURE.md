# Architecture

## Overview

HealthAdvocate is a RAG application with a **conditional agentic augmentation** path.
It is not pure retrieval-augmented generation: abnormal lab values trigger a live web
search for dietary guidance. The system is therefore three cooperating subsystems:

1. **Ingestion & indexing** — PDFs in, structured rows + vector chunks out.
2. **Retrieval & synthesis** — semantic Q&A grounded in the latest report.
3. **Analysis & advisory** — deterministic abnormality detection → conditional web advice.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Frontend (React + Vite)                           │
│   ┌──────────┐        ┌──────────┐         ┌──────────┐                    │
│   │ Upload   │        │   Ask    │         │  Trends  │                    │
│   │  tab     │        │   tab    │         │   tab    │                    │
│   └────┬─────┘        └────┬─────┘         └────┬─────┘                    │
└────────┼───────────────────┼────────────────────┼─────────────────────────┘
         │ POST /reports      │ POST /ask           │ GET /trends
┌────────▼───────────────────▼────────────────────▼─────────────────────────┐
│                            Backend (FastAPI)                               │
│                                                                            │
│  ┌──────────────┐     ┌───────────────┐     ┌──────────────────────────┐   │
│  │  Ingestion   │     │   Retrieval   │     │       Analysis            │   │
│  │              │     │               │     │                          │   │
│  │ pdf_store ───┼──┐  │ query_engine  │     │ analyzer (value vs range)│   │
│  │ parser       │  │  │  (latest =    │────▶│        │                 │   │
│  │ indexer      │  │  │  max report   │     │        ▼ abnormal?        │   │
│  └──────┬───────┘  │  │   _date)      │     │  ┌──────────────────────┐ │   │
│         │          │  └───────┬───────┘     │  │  food_advisor        │ │   │
│         ▼          │          │             │  │ (LangChain + DDG)    │ │   │
│  ┌────────────┐    │          ▼             │  └──────────────────────┘ │   │
│  │  Pinecone  │◀───┘   synthesis (OpenAI)   └──────────────────────────┘   │
│  │  (vectors) │                                                            │
│  └────────────┘    ┌────────────┐                                          │
│         ▲          │  SQLite    │◀── trends endpoint reads structured rows  │
│         └──────────│ (lab_store)│                                          │
│   indexer writes   └────────────┘                                          │
│   both stores                                                              │
└────────────────────────────────────────────────────────────────────────────┘
```

## Why two stores

| Store | Holds | Serves |
|-------|-------|--------|
| **Pinecone** | Embedded text chunks + metadata (`report_id`, `report_date`, `uploaded_at`, `filename`) | Semantic Q&A (Ask tab) |
| **SQLite (`lab_store`)** | Structured rows: `parameter, value, unit, report_date, ref_low, ref_high, flag` | Trends (chart) + deterministic abnormality analysis |

Semantic search is the wrong tool for "plot sodium over 6 months" — that needs exact,
filterable, ordered numeric rows. Conversely, structured rows are the wrong tool for
"explain what my results suggest." Each store does what it is good at.

## Component responsibilities

### Ingestion (`ingestion/`)
- **`pdf_store.py`** — persists the uploaded PDF to disk, writes a manifest entry
  (`report_id`, `filename`, `report_date`, `uploaded_at`, `path`). `report_date` comes
  from the user input field (auto pre-filled from the PDF when detectable).
- **`parser.py`** — extracts text and **structured lab rows** including the reference
  range printed in the report. Handles numeric ranges (`135–145`), inequality forms
  (`<140`), and units. Rows with no parseable range are kept but marked
  `range_available = false` (we never invent a range).
- **`indexer.py`** — chunks text, embeds via OpenAI, upserts to Pinecone with metadata;
  also writes structured rows to the SQLite lab_store.

### Storage (`storage/`)
- **`lab_store.py`** — SQLite access layer for structured lab rows. Powers `/trends` and
  feeds the analyzer.

### Retrieval (`retrieval/`)
- **`query_engine.py`** — LlamaIndex query engine. Applies a **latest-report metadata
  filter**: latest = `max(report_date)`, with `uploaded_at` as tiebreaker.
- **`synthesis.py`** — composes the grounded answer from retrieved nodes via OpenAI.

### Labs (`labs/`)
- **`analyzer.py`** — deterministic comparison of `value` against `ref_low/ref_high`
  from the report. Produces `AbnormalFinding` objects. **No LLM in this path** — it is
  rules-based, auditable, and unit-tested.

### Advisor (`advisor/`)
- **`ddg_search.py`** — DuckDuckGo search wrapper (no API key).
- **`food_advisor.py`** — LangChain agent invoked **only** for flagged parameters.
  Searches e.g. "foods to avoid high sodium", synthesizes a concise, cited list.

### API (`api/`)
- **`main.py`** — FastAPI app, CORS for the Vite dev server.
- **`routes_upload.py`** — `POST /reports` (multipart: file + `report_date`).
- **`routes_query.py`** — `POST /ask`.
- **`routes_trends.py`** — `GET /trends`.

## Key design decisions

1. **Deterministic abnormality detection, not LLM-judged.** The LLM is never asked
   whether a value is "abnormal." A value-vs-range comparison is rules-based and
   testable. This is the single most important safety/correctness decision.
2. **`report_date` (user input) is authoritative for recency and trends**, not upload
   time. A user may upload an old report late; the blood-draw date is what matters.
3. **Web augmentation is conditional and bounded.** DuckDuckGo is only called for
   parameters the analyzer flagged. No flags → no web calls.
4. **LangChain scoped to the advisor only.** RAG stays in LlamaIndex; the agentic web
   path is explicit and isolated, keeping each framework in its lane.
5. **Never fabricate reference ranges.** Per design, ranges come from the report. Absent
   ranges yield "no range available," not a guess.

## Configuration

Environment variables (see `.env.example`):

| Var | Purpose |
|-----|---------|
| `OPENAI_API_KEY` | embeddings + synthesis LLM |
| `PINECONE_API_KEY` | vector store |
| `PINECONE_INDEX_NAME` | index name |
| `PDF_STORAGE_DIR` | where uploaded PDFs are stored |
| `SQLITE_PATH` | lab_store database file |
| `CORS_ORIGINS` | allowed frontend origins |

(DuckDuckGo requires no key.)
