import { useState } from 'react';
import { Tabs } from './components/ui/Tabs';
import { UploadTab } from './tabs/UploadTab';
import { AskTab } from './tabs/AskTab';
import { TrendsTab } from './tabs/TrendsTab';

type TabKey = 'upload' | 'ask' | 'trends';

export default function App() {
  const [active, setActive] = useState<TabKey>('upload');

  return (
    <div className="app-shell">
      <header className="masthead">
        <div>
          <p className="masthead__kicker">Personal Bloodwork Intelligence</p>
          <h1 className="masthead__title">
            Health<span>Advocate</span>
          </h1>
        </div>
      </header>

      <p className="disclaimer">
        Informational only — not medical advice. Always consult a qualified clinician about
        your results.
      </p>

      <Tabs
        active={active}
        onChange={(k) => setActive(k as TabKey)}
        tabs={[
          { key: 'upload', label: 'Upload' },
          { key: 'ask', label: 'Ask' },
          { key: 'trends', label: 'Trends' },
        ]}
      />

      <main>
        {active === 'upload' && <UploadTab />}
        {active === 'ask' && <AskTab />}
        {active === 'trends' && <TrendsTab />}
      </main>
    </div>
  );
}
