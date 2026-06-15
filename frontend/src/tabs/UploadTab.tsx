import { useEffect, useState } from 'react';
import { deleteReport, listReports, uploadReport } from '../api/client';
import type { ReportMeta, UploadResponse } from '../types';

export function UploadTab() {
  const [file, setFile] = useState<File | null>(null);
  const [reportDate, setReportDate] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [reports, setReports] = useState<ReportMeta[]>([]);

  const today = new Date().toISOString().slice(0, 10);

  async function refresh() {
    try {
      setReports(await listReports());
    } catch {
      // listing failure is non-fatal for the upload form
    }
  }

  async function onDelete(reportId: string) {
    setError(null);
    try {
      await deleteReport(reportId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !reportDate) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await uploadReport(file, reportDate);
      setResult(res);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="card">
        <p className="card__label">Upload a bloodwork report</p>
        <form onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="pdf">PDF file</label>
            <input
              id="pdf"
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <div className="field">
            <label htmlFor="report-date">Report date (blood-draw date)</label>
            <input
              id="report-date"
              type="date"
              max={today}
              value={reportDate}
              onChange={(e) => setReportDate(e.target.value)}
            />
          </div>
          <button className="btn" type="submit" disabled={busy || !file || !reportDate}>
            {busy ? 'Uploading…' : 'Upload & index'}
          </button>
          {error && <p className="error">{error}</p>}
        </form>
      </section>

      {result && (
        <section className="card" aria-live="polite">
          <p className="card__label">Parsed {result.parsed_parameters.length} parameters</p>
          {result.parsed_parameters.map((p) => (
            <div className="finding" key={`${p.parameter}-${p.value}`}>
              <span className="finding__name">{p.parameter}</span>
              <span className="finding__value">
                {p.value}
                {p.unit ? ` ${p.unit}` : ''}
                <span className="muted">
                  {' '}
                  {p.range_available ? `(ref ${p.ref_low ?? '—'}–${p.ref_high ?? '—'})` : '(no range)'}
                </span>
              </span>
            </div>
          ))}
          {result.warnings.length > 0 && (
            <ul className="advice__list muted">
              {result.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {reports.length > 0 && (
        <section className="card">
          <p className="card__label">Stored reports (newest first)</p>
          {reports.map((r) => (
            <div className="report-row" key={r.report_id}>
              <span className="report-row__date">{r.report_date}</span>
              <span className="muted">{r.filename}</span>
              <button
                type="button"
                className="btn-delete"
                aria-label={`Delete report from ${r.report_date}`}
                onClick={() => onDelete(r.report_id)}
              >
                Delete
              </button>
            </div>
          ))}
        </section>
      )}
    </>
  );
}
