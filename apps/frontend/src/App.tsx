import { useState } from 'react';
import { LibraryView } from './views/Library/LibraryView';
import { ConnectorsView } from './views/Connectors/ConnectorsView';
import { LiveTVView } from './views/LiveTV/LiveTVView';
import { VoiceView } from './views/Voice/VoiceView';
import './App.css';

export interface AppProps {
  title?: string;
}

type View = 'library' | 'connectors' | 'livetv' | 'voice';

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
        <button
          className={`nav-button ${currentView === 'voice' ? 'active' : ''}`}
          onClick={() => {
            setCurrentView('voice');
          }}
        >
          🎤 Voice
        </button>
      </nav>

      <main className="app-content">
        {currentView === 'library' && <LibraryView />}
        {currentView === 'connectors' && <ConnectorsView />}
        {currentView === 'livetv' && <LiveTVView />}
        {currentView === 'voice' && <VoiceView onSearch={(query: string) => {
          setCurrentView('library');
          // TODO: Trigger search with query
          console.log('Voice search:', query);
        }} />}
      </main>
    </div>
  );
}
