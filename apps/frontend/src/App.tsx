import { useCallback, useEffect, useState } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import { OfflineBanner } from './components/OfflineBanner';
import { LegalNoticeDialog } from './components/LegalNoticeDialog/LegalNoticeDialog';
import { useNetworkStatus } from './hooks/useNetworkStatus';
import { LibraryView, VoiceSearchCommand } from './views/Library/LibraryView';
import { ConnectorsView } from './views/Connectors/ConnectorsView';
import { LiveTVView } from './views/LiveTV/LiveTVView';
import CastView from './views/Cast/CastView';
import { VoiceView } from './views/Voice/VoiceView';
import { HomeView, type HomeNavTarget } from './views/Home/HomeView';
import { SearchView } from './views/Search/SearchView';
import { RetroHubView } from './views/Retro/RetroHubView';
import SettingsView from './views/Settings/Settings';
import {
  acknowledgeLegalTerms,
  getLegalTermsNotice,
  type LegalAckResponse,
  type LegalTermsResponse,
} from './services/api';
import './App.css';

export interface AppProps {
  title?: string;
}

type View =
  | 'home'
  | 'library'
  | 'search'
  | 'connectors'
  | 'livetv'
  | 'retro'
  | 'voice'
  | 'cast'
  | 'settings';

interface NavItem {
  id: View;
  label: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'home', label: 'Home', icon: '🏠' },
  { id: 'library', label: 'Library', icon: '📚' },
  { id: 'search', label: 'Search', icon: '🔍' },
  { id: 'connectors', label: 'Connectors', icon: '🌐' },
  { id: 'livetv', label: 'Live TV', icon: '📺' },
  { id: 'retro', label: 'Retro Hub', icon: '🕹️' },
  { id: 'voice', label: 'Voice & AI', icon: '🎤' },
  { id: 'cast', label: 'Casting', icon: '📱' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
];

export function App(): React.JSX.Element {
  const [currentView, setCurrentView] = useState<View>('home');
  const [pendingVoiceQuery, setPendingVoiceQuery] = useState<VoiceSearchCommand | null>(null);
  const { online } = useNetworkStatus();
  const [legalDialogOpen, setLegalDialogOpen] = useState(false);
  const [legalTerms, setLegalTerms] = useState<LegalTermsResponse | null>(null);
  const [legalLoading, setLegalLoading] = useState(false);
  const [legalError, setLegalError] = useState<string | null>(null);
  const [legalAcknowledging, setLegalAcknowledging] = useState(false);

  const loadLegalTerms = useCallback(
    async (options?: { forceOpen?: boolean }) => {
      const forceOpen = options?.forceOpen ?? false;

      try {
        setLegalLoading(true);
        setLegalError(null);
        const terms = await getLegalTermsNotice();
        setLegalTerms(terms);

        const acceptedVersion = terms.accepted?.version ?? null;
        const requiresAcknowledgement = acceptedVersion !== terms.version;

        if (forceOpen || requiresAcknowledgement) {
          setLegalDialogOpen(true);
        } else if (!forceOpen) {
          setLegalDialogOpen(false);
        }
      } catch (error) {
        console.error('Failed to load legal terms', error);
        setLegalError(error instanceof Error ? error.message : 'Failed to load legal terms.');
        setLegalDialogOpen(true);
      } finally {
        setLegalLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadLegalTerms();
  }, [loadLegalTerms]);

  useEffect(() => {
    const handleShowLegal = () => {
      setLegalDialogOpen(true);
      if (!legalTerms || legalError) {
        void loadLegalTerms({ forceOpen: true });
      }
    };

    window.addEventListener('womcast:show-legal', handleShowLegal);
    return () => {
      window.removeEventListener('womcast:show-legal', handleShowLegal);
    };
  }, [legalError, legalTerms, loadLegalTerms]);

  const handleLegalAccept = useCallback(async () => {
    if (!legalTerms) {
      return;
    }

    try {
      setLegalAcknowledging(true);
      setLegalError(null);
      const response = await acknowledgeLegalTerms(legalTerms.version);
      setLegalTerms((prev) =>
        prev
          ? {
              ...prev,
              accepted: {
                version: response.version,
                accepted_at: response.accepted_at,
              },
            }
          : prev,
      );
      setLegalDialogOpen(false);
      window.dispatchEvent(
        new CustomEvent<LegalAckResponse>('womcast:legal-acknowledged', {
          detail: response,
        }),
      );
    } catch (error) {
      console.error('Failed to acknowledge legal terms', error);
      setLegalError(
        error instanceof Error ? error.message : 'Failed to acknowledge legal terms.',
      );
    } finally {
      setLegalAcknowledging(false);
    }
  }, [legalTerms]);

  const handleHomeNavigate = (target: HomeNavTarget) => {
    setCurrentView(target);
  };

  return (
    <div className="app">
      <OfflineBanner online={online} />
      <ErrorBoundary>
        <>
          <div className="app-shell">
            <nav className="app-nav">
              {NAV_ITEMS.map((item) => (
                <button
                  key={item.id}
                  className={`nav-button ${currentView === item.id ? 'active' : ''}`}
                  onClick={() => {
                    setCurrentView(item.id);
                  }}
                >
                  <span aria-hidden="true">{item.icon}</span>
                  {item.label}
                </button>
              ))}
            </nav>

            <main className="app-content">
              {currentView === 'home' && <HomeView onNavigate={handleHomeNavigate} online={online} />}
              {currentView === 'library' && (
                <LibraryView
                  voiceQuery={pendingVoiceQuery}
                  onVoiceQueryHandled={() => {
                    setPendingVoiceQuery(null);
                  }}
                />
              )}
              {currentView === 'search' && (
                <SearchView
                  voiceQuery={pendingVoiceQuery}
                  onVoiceQueryHandled={() => {
                    setPendingVoiceQuery(null);
                  }}
                />
              )}
              {currentView === 'connectors' && <ConnectorsView />}
              {currentView === 'livetv' && <LiveTVView />}
              {currentView === 'retro' && <RetroHubView />}
              {currentView === 'voice' && (
                <VoiceView
                  onSearch={(query: string) => {
                    const trimmedQuery = query.trim();
                    if (!trimmedQuery) {
                      return;
                    }
                    setPendingVoiceQuery({ id: Date.now(), text: trimmedQuery });
                    setCurrentView('search');
                  }}
                />
              )}
              {currentView === 'cast' && <CastView />}
              {currentView === 'settings' && <SettingsView />}
            </main>
          </div>

          <LegalNoticeDialog
            open={legalDialogOpen}
            terms={legalTerms}
            loading={legalLoading}
            error={legalError}
            onRetry={() => {
              void loadLegalTerms({ forceOpen: true });
            }}
            onAccept={() => {
              void handleLegalAccept();
            }}
            acknowledging={legalAcknowledging}
          />
        </>
      </ErrorBoundary>
    </div>
  );
}
