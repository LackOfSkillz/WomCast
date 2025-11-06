import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchWithRetry } from '../../utils/fetchWithRetry';
import { playMedia } from '../../services/api';
import { useNetworkStatus } from '../../hooks/useNetworkStatus';
import './ConnectorsView.css';

interface Connector {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
}

interface ConnectorItem {
  id: string;
  title: string;
  description?: string;
  thumbnail_url?: string;
  stream_url?: string;
  audio_url?: string;
  duration?: number;
  artist_name?: string;
  is_live?: boolean;
}

const CONNECTORS: Connector[] = [
  {
    id: 'internet-archive',
    name: 'Internet Archive',
    description: 'Public domain movies, TV shows, and audio',
    icon: '📚',
    color: '#4a9eff',
  },
  {
    id: 'pbs',
    name: 'PBS',
    description: 'Educational content and documentaries',
    icon: '📺',
    color: '#0055a4',
  },
  {
    id: 'nasa',
    name: 'NASA TV',
    description: 'Live streams and space exploration content',
    icon: '🚀',
    color: '#fc3d21',
  },
  {
    id: 'jamendo',
    name: 'Jamendo',
    description: 'Creative Commons music',
    icon: '🎵',
    color: '#ff6b35',
  },
];

const GATEWAY_API_URL = (import.meta.env.VITE_API_GATEWAY_URL as string) || 'http://localhost:8000';

export function ConnectorsView(): React.JSX.Element {
  const [selectedConnector, setSelectedConnector] = useState<string | null>(null);
  const [items, setItems] = useState<ConnectorItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const hasLoadedOnce = useRef(false);
  const { online } = useNetworkStatus();

  const loadConnectorContent = useCallback(async (connectorId: string) => {
    setLoading(true);
    setError(null);

    if (!online) {
      setLoading(false);
      if (!hasLoadedOnce.current) {
        setError('Connect to load content for this connector.');
      } else {
        setStatusMessage('Offline mode: content may be incomplete.');
      }
      return;
    }

    setStatusMessage(null);

    try {
      let endpoint = '';
      let dataKey = 'items';

      switch (connectorId) {
        case 'internet-archive':
          endpoint = '/v1/connectors/internet-archive/search?rows=20';
          dataKey = 'items';
          break;
        case 'pbs':
          endpoint = '/v1/connectors/pbs/featured?limit=20';
          dataKey = 'items';
          break;
        case 'nasa':
          endpoint = '/v1/connectors/nasa/live';
          dataKey = 'streams';
          break;
        case 'jamendo':
          endpoint = '/v1/connectors/jamendo/popular?limit=20';
          dataKey = 'tracks';
          break;
        default:
          throw new Error('Unknown connector');
      }

      const response = await fetchWithRetry(`${GATEWAY_API_URL}${endpoint}`, undefined, {
        serviceName: 'Connectors API',
      });
      if (!response.ok) {
        throw new Error(`Failed to load content: ${response.statusText}`);
      }

      const data: { items?: ConnectorItem[]; streams?: ConnectorItem[]; tracks?: ConnectorItem[] } =
        (await response.json()) as {
          items?: ConnectorItem[];
          streams?: ConnectorItem[];
          tracks?: ConnectorItem[];
        };
  const newItems = data[dataKey as keyof typeof data] ?? [];
  setItems(newItems);
  hasLoadedOnce.current = true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load content');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [online]);

  useEffect(() => {
    if (selectedConnector) {
      void loadConnectorContent(selectedConnector);
    }
  }, [selectedConnector, loadConnectorContent]);

  useEffect(() => {
    hasLoadedOnce.current = false;
  }, [selectedConnector]);

  const handlePlay = useCallback(async (item: ConnectorItem) => {
    if (!online) {
      setStatusMessage('Offline mode: start playback after reconnecting.');
      return;
    }

    try {
      // Get item details if stream_url not present
      let streamUrl = item.stream_url;

      if (!streamUrl && selectedConnector) {
        const detailsEndpoint = getDetailsEndpoint(selectedConnector, item.id);
        const response = await fetchWithRetry(`${GATEWAY_API_URL}${detailsEndpoint}`, undefined, {
          serviceName: 'Connector details API',
        });
        if (response.ok) {
          const details = (await response.json()) as {
            stream_url?: string;
            audio_url?: string;
          };
          streamUrl = details.stream_url ?? details.audio_url;
        }
      }

      if (!streamUrl) {
        alert('Stream URL not available for this item');
        return;
      }

      // Send to Kodi for playback
      await playMedia(streamUrl);

      alert(`Playing: ${item.title}`);
    } catch (err) {
      alert(`Playback error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  }, [online, selectedConnector]);

  const getDetailsEndpoint = (connectorId: string, itemId: string): string => {
    switch (connectorId) {
      case 'internet-archive':
        return `/v1/connectors/internet-archive/items/${itemId}`;
      case 'pbs':
        return `/v1/connectors/pbs/items/${itemId}`;
      case 'nasa':
        return `/v1/connectors/nasa/items/${itemId}`;
      case 'jamendo':
        return `/v1/connectors/jamendo/tracks/${itemId}`;
      default:
        return '';
    }
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return '';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    const secsStr = secs.toString().padStart(2, '0');
    return `${String(mins)}:${secsStr}`;
  };

  if (selectedConnector) {
    const connector = CONNECTORS.find((c) => c.id === selectedConnector);

    return (
      <div className="connectors-view">
        <header className="connectors-header">
          <button
            className="back-button"
            onClick={() => {
              setSelectedConnector(null);
              setItems([]);
              setStatusMessage(null);
              setError(null);
            }}
            aria-label="Back to connectors"
          >
            ← Back
          </button>
          <h1>
            <span className="connector-icon">{connector?.icon}</span>
            {connector?.name}
          </h1>
        </header>

        {statusMessage && (
          <div className="connectors-status" role="status">
            {statusMessage}
          </div>
        )}

        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading content...</p>
          </div>
        )}

        {error && (
          <div className="error-state">
            <p>⚠️ {error}</p>
            <button
              onClick={() => {
                void loadConnectorContent(selectedConnector);
              }}
            >
              Retry
            </button>
          </div>
        )}
        {!loading && !error && items.length === 0 && (
          <div className="empty-state">
            <p>No content available</p>
          </div>
        )}

        {!loading && items.length > 0 && (
          <div className="items-grid">
            {items.map((item) => (
              <div key={item.id} className="item-card">
                {item.thumbnail_url && (
                  <div className="item-thumbnail">
                    <img src={item.thumbnail_url} alt={item.title} loading="lazy" />
                  </div>
                )}
                <div className="item-details">
                  <h3 className="item-title">{item.title}</h3>
                  {item.description && (
                    <p className="item-description">
                      {item.description.slice(0, 100)}
                      {item.description.length > 100 ? '...' : ''}
                    </p>
                  )}
                  {item.artist_name && (
                    <p className="item-artist">
                      <strong>Artist:</strong> {item.artist_name}
                    </p>
                  )}
                  {item.duration && (
                    <p className="item-duration">⏱️ {formatDuration(item.duration)}</p>
                  )}
                  {item.is_live && <span className="live-badge">🔴 LIVE</span>}
                  <button
                    className="play-button"
                    onClick={() => {
                      void handlePlay(item);
                    }}
                    aria-label={`Play ${item.title}`}
                  >
                    ▶️ Play
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="connectors-view">
      <header className="connectors-header">
        <h1>Free Content Connectors</h1>
        <p className="subtitle">Browse public domain and Creative Commons content</p>
      </header>

      {statusMessage && (
        <div className="connectors-status" role="status">
          {statusMessage}
        </div>
      )}

      <div className="connectors-grid">
        {CONNECTORS.map((connector) => (
          <button
            key={connector.id}
            className="connector-card"
            style={{ borderColor: connector.color }}
            onClick={() => {
              setStatusMessage(null);
              setError(null);
              setSelectedConnector(connector.id);
            }}
            aria-label={`Open ${connector.name}`}
          >
            <div className="connector-icon" style={{ color: connector.color }}>
              {connector.icon}
            </div>
            <h2 className="connector-name">{connector.name}</h2>
            <p className="connector-description">{connector.description}</p>
            <div className="connector-arrow" style={{ color: connector.color }}>
              →
            </div>
          </button>
        ))}
      </div>

      <footer className="connectors-footer">
        <p>
          All content is legally available under public domain or Creative Commons licenses.
        </p>
      </footer>
    </div>
  );
}
