import type { AskResponse, ReportMeta, TrendSeries, UploadResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function uploadReport(file: File, reportDate: string): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('report_date', reportDate);
  const res = await fetch(`${API_BASE}/reports`, { method: 'POST', body: form });
  return handle<UploadResponse>(res);
}

export async function listReports(): Promise<ReportMeta[]> {
  const res = await fetch(`${API_BASE}/reports`);
  const body = await handle<{ reports: ReportMeta[] }>(res);
  return body.reports;
}

export async function deleteReport(reportId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/reports/${reportId}`, { method: 'DELETE' });
  if (!res.ok && res.status !== 204) {
    await handle(res); // throws with detail
  }
}

export async function ask(question: string): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  return handle<AskResponse>(res);
}

export async function getTrends(
  parameter: string,
  from?: string,
  to?: string,
): Promise<TrendSeries> {
  const params = new URLSearchParams({ parameter });
  if (from) params.append('from', from);
  if (to) params.append('to', to);
  const res = await fetch(`${API_BASE}/trends?${params.toString()}`);
  return handle<TrendSeries>(res);
}
