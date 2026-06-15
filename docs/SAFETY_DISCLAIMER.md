# Safety & Disclaimer

## Not medical advice

HealthAdvocate is an **informational and educational tool**. It does **not** provide
medical advice, diagnosis, or treatment. Nothing produced by this application —
including answers, abnormality flags, trend charts, or "foods to avoid" suggestions —
should be used as a substitute for the judgment of a qualified healthcare professional.

**Always consult your physician or a licensed clinician** about your lab results and any
decisions regarding diet, medication, or care.

## Scope and limitations

- **Abnormality detection is mechanical.** The app compares each value against the
  reference range printed in your report. Reference ranges vary by lab, age, sex,
  pregnancy status, and clinical context. A value inside a printed range is not
  guaranteed "fine," and a value outside it is not necessarily a problem. Only a
  clinician can interpret results in context.
- **No ranges are invented.** If a report does not include a parseable reference range
  for a parameter, that parameter is **not** flagged and is excluded from analysis.
- **Web guidance is automated and may be imperfect.** "Foods to avoid" suggestions are
  synthesized from live DuckDuckGo search results. Sources are cited so you can verify
  them, but they are not vetted by a medical professional and may be incomplete,
  outdated, or not applicable to your situation.
- **Parsing may be imperfect.** Lab PDFs vary widely in format. Extraction errors are
  possible; always cross-check against the original report.
- **The app answers from a single report at a time** (the latest by report date) in the
  Ask tab. It does not reason across your full medical history.

## Data handling

- Uploaded PDFs are stored locally in the configured storage directory.
- Lab values are stored in a local SQLite database; text chunks and embeddings are
  stored in your configured Pinecone index.
- This is a single-user local tool in v1; no authentication or multi-tenant isolation is
  provided. Do not deploy it as-is to a shared or public environment with real patient
  data without adding appropriate access controls and compliance review.
- Bloodwork is sensitive personal health information. Handle exports, backups, and API
  keys accordingly.

## No warranty

This software is provided "as is," without warranty of any kind. The authors are not
liable for any decisions made based on its output.
