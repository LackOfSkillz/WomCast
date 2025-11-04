import { useState } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import { OfflineBanner } from './components/OfflineBanner';
import { useNetworkStatus } from './hooks/useNetworkStatus';
import { LibraryView, VoiceSearchCommand } from './views/Library/LibraryView';
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
  const [pendingVoiceQuery, setPendingVoiceQuery] = useState<VoiceSearchCommand | null>(null);
  const { online } = useNetworkStatus();

  return (
    <div className="app">
      <OfflineBanner online={online} />
      <ErrorBoundary>
        <div className="app-shell">
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
            {currentView === 'library' && (
              <LibraryView
                voiceQuery={pendingVoiceQuery}
                onVoiceQueryHandled={() => {
                  setPendingVoiceQuery(null);
                }}
              />
            )}
            {currentView === 'connectors' && <ConnectorsView />}
            {currentView === 'livetv' && <LiveTVView />}
            {currentView === 'voice' && (
              <VoiceView
                onSearch={(query: string) => {
                  const trimmedQuery = query.trim();
                  if (!trimmedQuery) {
                    return;
                  }
                  setPendingVoiceQuery({ id: Date.now(), text: trimmedQuery });
                  setCurrentView('library');
                }}
              />
            )}
          </main>
        </div>
      </ErrorBoundary>
    </div>
  );
}
