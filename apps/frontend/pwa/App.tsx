import { useCallback, useEffect, useMemo, useState, type ReactElement } from 'react';
import {
  adjustVolume,
  formatDuration,
  getMediaFiles,
  getMediaItem,
  getPlayerState,
  getVolume,
  playMedia,
  quitPlaybackApplication,
  searchMediaFiles,
  semanticSearchMedia,
  sendInputAction,
  stopPlayback,
  type MediaFile,
  type PlayerState,
} from '../src/services/api';
import { VoiceButton } from '../src/components/VoiceButton';
import { useNetworkStatus } from '../src/hooks/useNetworkStatus';
import './App.css';

type RemoteAction =
  | 'up'
  | 'down'
  | 'left'
  | 'right'
  | 'select'
  | 'back'
  | 'context'
  | 'info'
  | 'home'
  | 'menu'
  | 'play_pause';

const REFRESH_INTERVAL_MS = 5000;
const REMOTE_ACTIONS: Array<{ label: string; action: RemoteAction }> = [
  { label: 'Up', action: 'up' },
  { label: 'Left', action: 'left' },
  { label: 'Select', action: 'select' },
  { label: 'Right', action: 'right' },
  { label: 'Down', action: 'down' },
  { label: 'Back', action: 'back' },
  { label: 'Menu', action: 'menu' },
  { label: 'Info', action: 'info' },
  { label: 'Home', action: 'home' },
  { label: 'Context', action: 'context' },
  { label: 'Play / Pause', action: 'play_pause' },
];

async function resolveMediaById(mediaId: number): Promise<MediaFile | null> {
  try {
    return await getMediaItem(mediaId);
  } catch (error) {
    console.warn('Failed to resolve media item', error);
    return null;
  }
}

export function RemoteApp(): ReactElement {
  const { online } = useNetworkStatus();
  const [playerState, setPlayerState] = useState<PlayerState | null>(null);
  const [playerError, setPlayerError] = useState<string | null>(null);
  const [loadingPlayer, setLoadingPlayer] = useState(false);
  const [mediaType, setMediaType] = useState<'video' | 'audio'>('video');
  const [mediaItems, setMediaItems] = useState<MediaFile[]>([]);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<MediaFile[]>([]);
  const [voiceResults, setVoiceResults] = useState<MediaFile[]>([]);
  const [commandError, setCommandError] = useState<string | null>(null);
  const [isSendingCommand, setIsSendingCommand] = useState(false);
  const [volume, setVolume] = useState<number | null>(null);
  const [isAdjustingVolume, setIsAdjustingVolume] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const refreshPlayerState = useCallback(async () => {
    try {
      setPlayerError(null);
      setLoadingPlayer(true);
      const state = await getPlayerState();
      setPlayerState(state);
    } catch (error) {
      console.warn('Failed to refresh player state', error);
      setPlayerError('Unable to reach playback service.');
    } finally {
      setLoadingPlayer(false);
    }
  }, []);

  const refreshVolume = useCallback(async () => {
    try {
      const current = await getVolume();
      setVolume(current);
    } catch (error) {
      console.warn('Failed to load volume', error);
      setCommandError('Unable to read volume level.');
    }
  }, []);

  useEffect(() => {
    void refreshPlayerState();
    void refreshVolume();
    const handle = window.setInterval(() => {
      void refreshPlayerState();
    }, REFRESH_INTERVAL_MS);
    return () => { window.clearInterval(handle); };
  }, [refreshPlayerState, refreshVolume]);

  useEffect(() => {
    const loadMedia = async () => {
      try {
        setMediaError(null);
        const items = await getMediaFiles(mediaType);
        setMediaItems(items.slice(0, 12));
      } catch (error) {
        console.warn('Failed to load media files', error);
        setMediaError('Unable to load library preview.');
      }
    };

    void loadMedia();
  }, [mediaType]);

  const handleCommandError = (message: string, error: unknown) => {
    console.warn(message, error);
    setCommandError(message);
    window.setTimeout(() => {
      setCommandError(null);
    }, 4000);
  };

  const handleInputAction = async (action: RemoteAction) => {
    try {
      setIsSendingCommand(true);
      if (action === 'home') {
        await quitPlaybackApplication();
        await refreshPlayerState();
      } else {
        await sendInputAction(action);
      }
    } catch (error) {
      const errorMessage =
        action === 'home' ? 'Failed to exit playback application.' : `Failed to send ${action} command.`;
      handleCommandError(errorMessage, error);
    } finally {
      setIsSendingCommand(false);
    }
  };

  const handlePlayMedia = async (filePath: string, friendlyName: string) => {
    try {
      await playMedia(filePath);
      setCommandError(null);
      await refreshPlayerState();
    } catch (error) {
      handleCommandError(`Failed to start ${friendlyName}.`, error);
    }
  };

  const handlePlayFromRecord = async (item: MediaFile) => {
    if (!item.file_path) {
      handleCommandError('Media file missing path metadata.', null);
      return;
    }
  await handlePlayMedia(item.file_path, item.file_name);
  };

  const handleSearchSubmit = async (query: string) => {
    const trimmed = query.trim();
    setSearchQuery(query);
    if (!trimmed) {
      setSearchResults([]);
      return;
    }

    try {
      setIsSearching(true);
      const results = await searchMediaFiles(trimmed);
      setSearchResults(results.slice(0, 8));
    } catch (error) {
      handleCommandError('Search failed. Try again later.', error);
    } finally {
      setIsSearching(false);
    }
  };

  const handleVoiceTranscript = async (text: string) => {
    const normalized = text.trim();
    setVoiceTranscript(normalized);
    if (!normalized) {
      setVoiceResults([]);
      return;
    }

    try {
      setIsSearching(true);
      const response = await semanticSearchMedia(normalized, 5);
      const resolved = await Promise.all(
        response.results
          .filter((hit) => hit.media_id != null)
          .map(async (hit) => {
            const mediaId = hit.media_id;
            if (typeof mediaId !== 'number') {
              return null;
            }
            return resolveMediaById(mediaId);
          })
      );

      const filtered = resolved.filter((item): item is MediaFile => item !== null);
      setVoiceResults(filtered);
    } catch (error) {
      handleCommandError('Semantic search unavailable.', error);
    } finally {
      setIsSearching(false);
    }
  };

  const handleStop = async () => {
    try {
      await stopPlayback();
      await refreshPlayerState();
    } catch (error) {
      handleCommandError('Stop command failed.', error);
    }
  };

  const handleVolumeAdjust = async (delta: number) => {
    try {
      setIsAdjustingVolume(true);
      const newVolume = await adjustVolume(delta);
      setVolume(newVolume);
    } catch (error) {
      handleCommandError('Unable to adjust volume.', error);
    } finally {
      setIsAdjustingVolume(false);
    }
  };

  const nowPlayingTitle = useMemo(() => {
    if (!playerState) return 'Nothing playing';
    if (playerState.title) return playerState.title;
    if (playerState.file_path) {
      const segments = playerState.file_path.split(/[\\/]/);
      return segments[segments.length - 1] ?? 'Unknown media';
    }
    return 'Unknown media';
  }, [playerState]);

  return (
    <div className="remote-app">
      <header className="remote-header">
        <h1>WomCast Remote</h1>
        <p>Control playback, browse the library, or issue voice commands from your phone.</p>
      </header>

      {!online && (
        <div className="remote-banner" role="status">
          Offline mode detected. Remote actions will queue until connectivity returns.
        </div>
      )}

      {commandError && (
        <div className="remote-warning" role="alert">
          {commandError}
        </div>
      )}

      <section className="panel now-playing">
        <div className="panel-header">
          <h2>Now Playing</h2>
          <button
            className="secondary"
            type="button"
            onClick={() => {
              void refreshPlayerState();
            }}
            disabled={loadingPlayer}
          >
            Refresh
          </button>
        </div>
        <div className="now-playing-body">
          <div className="now-playing-title">{nowPlayingTitle}</div>
          <div className="now-playing-meta">
            <span>{playerState?.media_type ?? '—'}</span>
            <span>
              {playerState?.duration_seconds
                ? `${formatDuration(playerState.duration_seconds)} total`
                : 'Duration pending'}
            </span>
          </div>
          {playerState && (
            <div className="progress">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{
                    width:
                      playerState.duration_seconds > 0
                        ? `${Math.min(100, (playerState.position_seconds / playerState.duration_seconds) * 100).toFixed(1)}%`
                        : '0%',
                  }}
                />
              </div>
              <div className="progress-labels">
                <span>{formatDuration(playerState.position_seconds)}</span>
                <span>{formatDuration(playerState.duration_seconds)}</span>
              </div>
            </div>
          )}
          {playerError && <div className="remote-hint">{playerError}</div>}
        </div>
        <div className="control-row">
          <button
            className="primary"
            type="button"
            onClick={() => {
              void handleInputAction('play_pause');
            }}
            disabled={isSendingCommand}
          >
            Play / Pause
          </button>
          <button
            className="secondary"
            type="button"
            onClick={() => {
              void handleStop();
            }}
          >
            Stop
          </button>
        </div>
        <div className="control-row">
          <button
            className="secondary"
            type="button"
            onClick={() => {
              void handleVolumeAdjust(-5);
            }}
            disabled={isAdjustingVolume}
          >
            Volume -
          </button>
          <div className="volume-indicator" aria-live="polite">
            Volume: {volume ?? '…'}
          </div>
          <button
            className="secondary"
            type="button"
            onClick={() => {
              void handleVolumeAdjust(5);
            }}
            disabled={isAdjustingVolume}
          >
            Volume +
          </button>
        </div>
      </section>

      <section className="panel remote-pad">
        <h2>D-Pad</h2>
        <div className="pad-grid">
          {REMOTE_ACTIONS.map(({ label, action }) => (
            <button
              key={action}
              type="button"
              className="pad-button"
              onClick={() => {
                void handleInputAction(action);
              }}
              disabled={isSendingCommand}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      <section className="panel library">
        <div className="panel-header">
          <h2>Library Preview</h2>
          <div className="segmented">
            <button
              type="button"
              className={mediaType === 'video' ? 'active' : ''}
              onClick={() => { setMediaType('video'); }}
            >
              Video
            </button>
            <button
              type="button"
              className={mediaType === 'audio' ? 'active' : ''}
              onClick={() => { setMediaType('audio'); }}
            >
              Audio
            </button>
          </div>
        </div>
        {mediaError && <div className="remote-hint">{mediaError}</div>}
        <div className="media-grid">
          {mediaItems.map((item) => (
            <article className="media-card" key={item.id}>
              <h3>{item.file_name}</h3>
              <p>{item.media_type}</p>
              <button
                type="button"
                onClick={() => {
                  void handlePlayFromRecord(item);
                }}
              >
                Play
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="panel search">
        <h2>Search Library</h2>
        <form
          className="search-form"
          onSubmit={(event) => {
            event.preventDefault();
            void handleSearchSubmit(searchQuery);
          }}
        >
          <input
            type="search"
            value={searchQuery}
            onChange={(event) => {
              setSearchQuery(event.target.value);
            }}
            placeholder="Search by title"
          />
          <button className="secondary" type="submit" disabled={isSearching}>
            Search
          </button>
        </form>
        <div className="media-grid">
          {searchResults.map((item) => (
            <article className="media-card" key={`search-${String(item.id)}`}>
              <h3>{item.file_name}</h3>
              <p>{item.media_type}</p>
              <button
                type="button"
                onClick={() => {
                  void handlePlayFromRecord(item);
                }}
              >
                Play
              </button>
            </article>
          ))}
          {searchResults.length === 0 && searchQuery.trim() && !isSearching && (
            <div className="remote-hint">No direct matches yet.</div>
          )}
        </div>
      </section>

      <section className="panel voice">
        <h2>Voice Remote</h2>
        <p className="remote-hint">Press and hold to speak. Release to run semantic search.</p>
        <VoiceButton
          disabled={!online}
          disabledReason={online ? undefined : 'Voice requires connectivity.'}
          onTranscript={(text) => {
            void handleVoiceTranscript(text);
          }}
          onError={(error) => {
            handleCommandError('Voice capture error.', error);
          }}
        />
        {voiceTranscript && <div className="voice-echo">“{voiceTranscript}”</div>}
        <div className="media-grid">
          {voiceResults.map((item) => (
            <article className="media-card" key={`voice-${String(item.id)}`}>
              <h3>{item.file_name}</h3>
              <p>{item.media_type}</p>
              <button
                type="button"
                onClick={() => {
                  void handlePlayFromRecord(item);
                }}
              >
                Play
              </button>
            </article>
          ))}
          {voiceResults.length === 0 && voiceTranscript && !isSearching && (
            <div className="remote-hint">No semantic matches yet.</div>
          )}
        </div>
      </section>
    </div>
  );
}
