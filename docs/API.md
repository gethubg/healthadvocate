# API Reference

Base URL (dev): `http://localhost:8000`

All responses are JSON. Errors use a consistent envelope:

```json
{ "detail": "human-readable message" }
```

---

## POST /reports

Upload and ingest a bloodwork PDF.

**Request** — `multipart/form-data`:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `file` | file (PDF) | yes | The bloodwork report. |
| `report_date` | string (`YYYY-MM-DD`) | yes | Blood-draw date. Must not be in the future. |

**Response** `201`:

```json
{
  "report_id": "rpt_a1b2c3",
  "filename": "labcorp_2026-05-01.pdf",
  "report_date": "2026-05-01",
  "uploaded_at": "2026-06-15T14:41:00Z",
  "parsed_parameters": [
    { "parameter": "Sodium", "value": 148, "unit": "mmol/L",
      "ref_low": 135, "ref_high": 145, "range_available": true }
  ],
  "warnings": [
    "Parameter 'Vitamin D' has no parseable reference range."
  ]
}
```

**Errors**: `400` (invalid/future date, non-PDF, parse failure), `413` (file too large).

---

## POST /ask

Ask a question against the **latest** report (`max(report_date)`).

**Request** — `application/json`:

```json
{ "question": "Is my sodium level okay?" }
```

**Response** `200`:

```json
{
  "answer": "Your most recent report (2026-05-01) shows sodium at 148 mmol/L, above the reference range of 135–145 mmol/L.",
  "report_id": "rpt_a1b2c3",
  "report_date": "2026-05-01",
  "findings": [
    { "parameter": "Sodium", "value": 148, "unit": "mmol/L",
      "ref_low": 135, "ref_high": 145, "direction": "high" }
  ],
  "advice": [
    { "parameter": "Sodium",
      "foods_to_avoid": ["Processed meats", "Canned soups", "Salted snacks"],
      "sources": [ { "title": "...", "url": "https://..." } ] }
  ]
}
```

`findings` and `advice` are empty arrays when nothing is abnormal.

**Errors**: `404` (no reports uploaded yet), `502` (LLM/search upstream failure).

---

## GET /trends

Time series for one parameter over a date range.

**Query parameters:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `parameter` | string | yes | e.g. `sodium` (case-insensitive). |
| `from` | `YYYY-MM-DD` | no | Defaults to earliest available. |
| `to` | `YYYY-MM-DD` | no | Defaults to latest available. |

**Response** `200`:

```json
{
  "parameter": "Sodium",
  "unit": "mmol/L",
  "points": [
    { "report_date": "2026-01-10", "value": 140, "ref_low": 135, "ref_high": 145, "abnormal": false },
    { "report_date": "2026-05-01", "value": 148, "ref_low": 135, "ref_high": 145, "abnormal": true }
  ]
}
```

**Errors**: `404` (parameter not found in any report), `400` (invalid date range).

---

## GET /reports

List uploaded reports (for the Upload tab's report list), sorted by `report_date` desc.

**Response** `200`:

```json
{
  "reports": [
    { "report_id": "rpt_a1b2c3", "filename": "labcorp_2026-05-01.pdf",
      "report_date": "2026-05-01", "uploaded_at": "2026-06-15T14:41:00Z" }
  ]
}
```

---

## DELETE /reports/{report_id}

Remove a report from all stores: SQLite rows, the stored PDF, and its Pinecone
vectors. Vector deletion is best-effort — if it fails, the rows and file are still
removed (logged server-side).

**Response** `204` (no content).

**Errors**: `404` (unknown `report_id`).

---

## GET /health

Liveness probe → `{ "status": "ok" }`.
