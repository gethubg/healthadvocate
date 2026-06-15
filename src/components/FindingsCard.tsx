import type { AbnormalFinding } from '../types';

export function FindingsCard({ findings }: { findings: AbnormalFinding[] }) {
  if (findings.length === 0) return null;

  return (
    <section className="card" aria-labelledby="findings-label">
      <p id="findings-label" className="card__label">
        Abnormal findings
      </p>
      {findings.map((f) => (
        <div className="finding" key={`${f.parameter}-${f.value}`}>
          <span className="finding__name">{f.parameter}</span>
          <span className="finding__value">
            {f.value}
            {f.unit ? ` ${f.unit}` : ''}
            <span className="muted">
              {' '}
              (ref {f.ref_low ?? '—'}–{f.ref_high ?? '—'})
            </span>
          </span>
          <span className={`pill pill--${f.direction}`}>{f.direction}</span>
        </div>
      ))}
    </section>
  );
}
