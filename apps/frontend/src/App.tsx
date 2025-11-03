import { useState } from 'react';
import { LibraryView } from './views/Library/LibraryView';
import { ConnectorsView } from './views/Connectors/ConnectorsView';
import { LiveTVView } from './views/LiveTV/LiveTVView';
import './App.css';

export interface AppProps {
  title?: string;
}

type View = 'library' | 'connectors' | 'livetv';

export function App(): React.JSX.Element {
  const [currentView, setCurrentView] = useState<View>('connectors');

  return (
    <div className="app">
      <nav className="app-nav">
        <button
          className={`nav-button ${currentView === 'library' ? 'active' : ''}`}
          onClick={() => {
            setCurrentView('library');
          }}
        >
          📚 Library
        </button>
        <button
          className={`nav-button ${currentView === 'connectors' ? 'active' : ''}`}
          onClick={() => {
            setCurrentView('connectors');
          }}
        >
          🌐 Connectors
        </button>
        <button
          className={`nav-button ${currentView === 'livetv' ? 'active' : ''}`}
          onClick={() => {
            setCurrentView('livetv');
          }}
        >
          📺 Live TV
        </button>
      </nav>

      <main className="app-content">
        {currentView === 'library' && <LibraryView />}
        {currentView === 'connectors' && <ConnectorsView />}
        {currentView === 'livetv' && <LiveTVView />}
      </main>
    </div>
  );
}
