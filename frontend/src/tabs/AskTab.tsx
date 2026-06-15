import { useState } from 'react';
import { ask } from '../api/client';
import { FindingsCard } from '../components/FindingsCard';
import { FoodAdviceCard } from '../components/FoodAdviceCard';
import type { AskResponse } from '../types';

export function AskTab() {
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<AskResponse | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setResponse(await ask(question.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed');
      setResponse(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="card">
        <p className="card__label">Ask about your latest report</p>
        <form onSubmit={onSubmit}>
          <div className="field">
            <textarea
              rows={3}
              placeholder="e.g. Is my sodium level okay?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </div>
          <button className="btn" type="submit" disabled={busy || !question.trim()}>
            {busy ? 'Thinking…' : 'Ask'}
          </button>
          {error && <p className="error">{error}</p>}
        </form>
      </section>

      {response && (
        <>
          <section className="card" aria-live="polite">
            <p className="card__label">
              Answer {response.report_date && `· report ${response.report_date}`}
            </p>
            <p>{response.answer}</p>
          </section>
          <FindingsCard findings={response.findings} />
          <FoodAdviceCard advice={response.advice} />
        </>
      )}
    </>
  );
}
