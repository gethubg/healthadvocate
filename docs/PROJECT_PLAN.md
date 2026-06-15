# Project Plan

## Goal

A production-grade RAG application that ingests bloodwork PDFs, answers questions about
the latest report, charts attribute trends over time, and provides web-sourced
"foods to avoid" guidance for abnormal values.

## Confirmed decisions

| Decision | Choice |
|----------|--------|
| Codebase | Fresh `healthadvocate/` directory |
| Frontend | React + Vite (Recharts for charts) |
| Web search | DuckDuckGo (no API key) via LangChain |
| Abnormality detection | PDF's own printed reference ranges |
| "Latest report" | `max(report_date)`, `uploaded_at` as tiebreaker |
| Upload | Requires a user-entered `report_date` (auto pre-filled from PDF when detected) |
| Trends | Third tab; line chart over a date range with shaded reference band |

## Tech stack

Python 3.12 · LlamaIndex · Pinecone · OpenAI · LangChain · SQLite · FastAPI ·
React + Vite + Recharts.

## Non-goals (v1)

- No multi-user auth / accounts (single-user local tool).
- No automatic reference-range invention (ranges come from the report only).
- No EHR/clinical integrations.
- No mobile app.

## Phased build

### Phase 0 — Documentation ✅ (this phase)
- README, ARCHITECTURE, DATA_FLOW, API, SAFETY_DISCLAIMER, PROJECT_PLAN.

### Phase 1 — Backend scaffold
- `pyproject.toml` (Python 3.12, pinned deps), `.env.example`, `config.py`.
- Pydantic models: `Report`, `LabValue`, `AbnormalFinding`, `AskResponse`,
  `TrendPoint`, `TrendSeries`.
- FastAPI app + CORS + `/health`.

### Phase 2 — Storage layer
- `storage/lab_store.py` — SQLite schema + access layer for structured rows.
- Tests: insert/query by parameter and date range.

### Phase 3 — Ingestion
- `pdf_store.py` (save + manifest with `report_date`/`uploaded_at`).
- `parser.py` (text + structured rows + reference-range parsing, including `<140` forms;
  PDF date detection for pre-fill).
- `indexer.py` (chunk → embed → Pinecone; write rows → lab_store).
- Tests: parser on sample lab layouts, range-parsing edge cases.

### Phase 4 — Analysis
- `labs/analyzer.py` — deterministic value-vs-range comparison → findings.
- Tests: high/low/in-range/no-range cases.

### Phase 5 — Retrieval
- `retrieval/query_engine.py` — latest-report metadata filter (`max(report_date)`).
- `retrieval/synthesis.py` — grounded answer composition.
- Tests: latest-report selection logic.

### Phase 6 — Advisory
- `advisor/ddg_search.py` + `advisor/food_advisor.py` (LangChain agent).
- Tests: triggered only on flagged parameters; output shape + citations.

### Phase 7 — Trends endpoint
- `api/routes_trends.py` — `GET /trends`.
- Tests: range filtering, abnormal flagging in series.

### Phase 8 — Frontend (React + Vite)
- Three tabs: **Upload** (date input + report list), **Ask** (chat + findings/advice
  cards), **Trends** (parameter selector + date range + Recharts band chart).
- API client; CORS verified against the FastAPI backend.

### Phase 9 — Hardening
- Error handling at boundaries, input validation, file-size limits.
- Safety disclaimer surfaced in the UI.
- README run instructions; `docker-compose.yml`.

## Testing strategy

- **Unit:** parser, range-parsing, analyzer, latest-report logic, lab_store queries.
- **Integration:** `/reports` → `/ask` → `/trends` against a seeded test report.
- **Target:** 80%+ coverage on backend logic (per project standards).
- Web-search and LLM calls mocked in tests; one optional live smoke test.

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Lab PDF layouts vary widely | LLM-assisted structured extraction + tolerant range parser; surface warnings for unparsed rows. |
| Missing reference ranges in a PDF | Mark `range_available = false`; never invent a range; exclude from abnormality detection. |
| DuckDuckGo result quality/rate | Bound calls to flagged params; synthesize + cite; degrade gracefully on no results. |
| Health-adjacent output liability | Prominent "not medical advice" disclaimer in UI + docs. |
| Date ambiguity (report vs upload) | `report_date` authoritative; `uploaded_at` tiebreaker; warn on PDF/entered mismatch. |

## Definition of done (v1)

- Upload a PDF with a date → it is stored, parsed, indexed.
- Ask a question → grounded answer from the latest report.
- An abnormal value → foods-to-avoid card with sources.
- Trends tab → chart any parameter over a date range with the reference band.
- Backend tests green at 80%+ coverage.
