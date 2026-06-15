import type { FoodAdvice } from '../types';

export function FoodAdviceCard({ advice }: { advice: FoodAdvice[] }) {
  const actionable = advice.filter((a) => a.foods_to_avoid.length > 0);
  if (actionable.length === 0) return null;

  return (
    <section className="card" aria-labelledby="advice-label">
      <p id="advice-label" className="card__label">
        Foods to avoid
      </p>
      {actionable.map((a) => (
        <div key={a.parameter}>
          <h3>{a.parameter}</h3>
          <ul className="advice__list">
            {a.foods_to_avoid.map((food) => (
              <li key={food}>{food}</li>
            ))}
          </ul>
          {a.sources.length > 0 && (
            <p className="advice__sources">
              Sources:{' '}
              {a.sources.map((s, i) => (
                <span key={s.url}>
                  {i > 0 && ', '}
                  <a href={s.url} target="_blank" rel="noreferrer noopener">
                    {s.title || new URL(s.url).hostname}
                  </a>
                </span>
              ))}
            </p>
          )}
        </div>
      ))}
    </section>
  );
}
