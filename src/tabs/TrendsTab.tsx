import { lazy, Suspense, useState } from 'react';
import { getTrends } from '../api/client';
import type { TrendSeries } from '../types';

// Recharts is heavy; load it only when the Trends tab actually renders a chart.
const TrendChart = lazy(() =>
  import('../components/TrendChart').then((m) => ({ default: m.TrendChart })),
);

export function TrendsTab() {
  const [parameter, setParameter] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [series, setSeries] = useState<TrendSeries | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!parameter.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setSeries(await getTrends(parameter.trim(), from || undefined, to || undefined));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load trend');
      setSeries(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="card">
        <p className="card__label">Chart an attribute over time</p>
        <form onSubmit={onSubmit}>
          <div className="toolbar">
            <div className="field" style={{ flex: '1 1 200px', marginBottom: 0 }}>
              <label htmlFor="param">Parameter</label>
              <input
                id="param"
                type="text"
                placeholder="e.g. Sodium"
                value={parameter}
                onChange={(e) => setParameter(e.target.value)}
              />
            </div>
            <div className="field" style={{ marginBottom: 0 }}>
              <label htmlFor="from">From</label>
              <input id="from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
            </div>
            <div className="field" style={{ marginBottom: 0 }}>
              <label htmlFor="to">To</label>
              <input id="to" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
            </div>
            <button className="btn" type="submit" disabled={busy || !parameter.trim()}>
              {busy ? 'Loading…' : 'Plot'}
            </button>
          </div>
          {error && <p className="error">{error}</p>}
        </form>
      </section>

      {series && (
        <section className="card" aria-live="polite">
          <p className="card__label">
            {series.parameter}
            {series.unit ? ` · ${series.unit}` : ''} · {series.points.length} readings
          </p>
          <Suspense fallback={<p className="muted">Loading chart…</p>}>
            <TrendChart series={series} />
          </Suspense>
          <p className="muted advice__sources">
            Shaded band = reference range. Highlighted points fall outside it.
          </p>
        </section>
      )}
    </>
  );
}
