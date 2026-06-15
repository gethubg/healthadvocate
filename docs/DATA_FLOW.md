# Data Flow

Three flows: **ingestion**, **query (Ask)**, and **trends**. The advisory path is a
branch of the query flow.

## 1. Ingestion flow (Upload tab)

```
User selects PDF + enters report_date
        │
        ▼
POST /reports  (multipart: file, report_date)
        │
        ▼
pdf_store.save()
   ├─ write PDF to PDF_STORAGE_DIR/<report_id>.pdf
   └─ manifest entry: { report_id, filename, report_date, uploaded_at, path }
        │
        ▼
parser.parse(pdf)
   ├─ extract full text  ───────────────┐
   └─ extract structured rows:          │
      (parameter, value, unit,          │
       ref_low, ref_high,               │
       range_available, flag)           │
        │                               │
        ▼                               ▼
indexer.index()                    (text chunks)
   ├─ lab_store.insert(rows, report_id, report_date)   → SQLite
   └─ chunk → embed (OpenAI) → upsert to Pinecone with metadata:
        { report_id, report_date, uploaded_at, filename }
        │
        ▼
Response: { report_id, report_date, parsed_parameters: [...], warnings: [...] }
```

**Date handling.** `report_date` is user-supplied. The parser also attempts to detect a
date in the PDF; the frontend pre-fills the input with it, but the user's value wins.
`uploaded_at` is the server clock, used only as a tiebreaker.

**Warnings surfaced to the user:** parameters with `range_available = false`, unparseable
rows, or a PDF-detected date that disagrees with the entered date.

## 2. Query flow (Ask tab)

```
User question
        │
        ▼
POST /ask  { question }
        │
        ▼
Resolve latest report:  report_id = argmax(report_date, then uploaded_at)
        │
        ▼
query_engine.query(question, filter = { report_id == latest })
   ├─ retrieve top-k chunks from Pinecone (filtered to latest report)
   └─ synthesis (OpenAI) → grounded answer
        │
        ▼
analyzer.analyze(latest report rows from lab_store)
   └─ for each row with range_available:
        value < ref_low OR value > ref_high  → AbnormalFinding
        │
        ├─ no abnormal findings ──────────────► return { answer, findings: [] }
        │
        ▼ abnormal findings exist
food_advisor.advise(finding.parameter)   [for each flagged parameter]
   ├─ ddg_search("foods to avoid <direction> <parameter>")
   └─ LangChain synthesis → { parameter, foods_to_avoid: [...], sources: [...] }
        │
        ▼
Response: {
  answer,
  findings: [ { parameter, value, unit, ref_low, ref_high, direction } ],
  advice:   [ { parameter, foods_to_avoid, sources } ]
}
```

The advisory branch runs **only** when the analyzer flags something, and only for the
flagged parameters — bounding web calls.

## 3. Trends flow (Trends tab)

```
User picks parameter + date range
        │
        ▼
GET /trends?parameter=sodium&from=2025-01-01&to=2026-06-15
        │
        ▼
lab_store.query(parameter, from, to)   → ordered by report_date
        │
        ▼
Response: {
  parameter, unit,
  points: [ { report_date, value, ref_low, ref_high, abnormal } ],
}
        │
        ▼
Frontend (Recharts): line chart, shaded reference band, abnormal points highlighted.
Clicking an abnormal point reuses the food-advisor advice.
```

Trends read **only** from SQLite — no vector search, no LLM — so the chart is fast and
deterministic.
