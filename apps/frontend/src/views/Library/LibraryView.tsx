import { useState, useEffect, useCallback, useRef } from 'react';
import {
  MediaFile,
  getMediaFiles,
  searchMediaFiles,
  semanticSearchMedia,
  type SemanticSearchHit,
} from '../../services/api';
import { SearchBox } from '../../components/SearchBox';
import { MediaGrid } from '../../components/MediaGrid';
import { DetailPane } from '../../components/DetailPane';
import { useNetworkStatus } from '../../hooks/useNetworkStatus';
import './LibraryView.css';

export interface VoiceSearchCommand {
  id: number;
  text: string;
}

interface LibraryViewProps {
  voiceQuery?: VoiceSearchCommand | null;
  onVoiceQueryHandled?: () => void;
}

export function LibraryView({ voiceQuery, onVoiceQueryHandled }: LibraryViewProps) {
  const [allMedia, setAllMedia] = useState<MediaFile[]>([]);
  const [filteredMedia, setFilteredMedia] = useState<MediaFile[]>([]);
  const [selectedMediaId, setSelectedMediaId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const { online } = useNetworkStatus();
  const lastHandledVoiceQueryId = useRef<number | null>(null);
  const hasLoadedOnce = useRef(false);
  const searchRequestId = useRef(0);
  const mediaIndexRef = useRef(new Map<number, MediaFile>());

  useEffect(() => {
    let active = true;

    const loadMedia = async () => {
      if (!online) {
        if (!hasLoadedOnce.current && active) {
          setError('You appear to be offline. Connect to load your library.');
          setLoading(false);
        } else if (active) {
          setStatusMessage('Offline mode: showing the last library results we have.');
          setLoading(false);
        }
        return;
      }

      if (active) {
        setLoading(true);
        setError(null);
        setStatusMessage(null);
      }

      try {
        const data = await getMediaFiles();
        if (active) {
          setAllMedia(data);
          hasLoadedOnce.current = true;
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load media');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void loadMedia();

    return () => {
      active = false;
    };
  }, [online]);

  useEffect(() => {
    mediaIndexRef.current = new Map(allMedia.map((item) => [item.id, item]));
  }, [allMedia]);

  const handleSearch = useCallback(
    (query: string) => {
      const normalizedQuery = query.trim();

      if (!normalizedQuery) {
        setFilteredMedia(allMedia);
        setStatusMessage(null);
        return;
      }

      const requestId = Date.now();
      searchRequestId.current = requestId;
  setStatusMessage('Searching...');

      const fallbackFilter = () => {
        const lowercaseQuery = normalizedQuery.toLowerCase();
        return allMedia.filter((media) =>
          media.file_name.toLowerCase().includes(lowercaseQuery)
        );
      };

      const runSearch = async () => {
        let textResults: MediaFile[] = [];
        let usedFallback = false;

        if (online) {
          try {
            textResults = await searchMediaFiles(normalizedQuery);
          } catch (err) {
            console.error('Text search failed:', err);
            textResults = fallbackFilter();
            usedFallback = true;
          }
        } else {
          textResults = fallbackFilter();
          usedFallback = true;
        }

        let semanticResults: SemanticSearchHit[] = [];
        let semanticLatency: number | null = null;
        if (online) {
          try {
            const response = await semanticSearchMedia(normalizedQuery, 12);
            semanticResults = response.results ?? [];
            semanticLatency = typeof response.latency_ms === 'number' ? response.latency_ms : null;
          } catch (err) {
            console.warn('Semantic search unavailable:', err);
          }
        }

        if (searchRequestId.current !== requestId) {
          return;
        }

        const { mergedResults, semanticOnlyCount } = mergeSearchResults(
          textResults,
          semanticResults,
          mediaIndexRef.current
        );

        if (mergedResults.length === 0) {
          setFilteredMedia(textResults.length ? textResults : fallbackFilter());
        } else {
          setFilteredMedia(mergedResults);
        }

        const statusParts: string[] = [];
        if (usedFallback) {
          statusParts.push(
            online
              ? 'Search service unavailable - showing cached results.'
              : 'Offline search limited to cached titles.'
          );
        }
        if (semanticOnlyCount > 0) {
          const latencyLabel =
            semanticLatency !== null ? ` in ${Math.round(semanticLatency)} ms` : '';
          statusParts.push(
            `Semantic boost added ${semanticOnlyCount} match${semanticOnlyCount === 1 ? '' : 'es'}${latencyLabel}.`
          );
        }

        setStatusMessage(statusParts.length > 0 ? statusParts.join(' ') : null);
      };

      void runSearch();
    },
    [allMedia, online]
  );

  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredMedia(allMedia);
    }
  }, [allMedia, searchQuery]);

  useEffect(() => {
    if (!voiceQuery || !voiceQuery.text.trim()) {
      return;
    }

    if (voiceQuery.id === lastHandledVoiceQueryId.current) {
      return;
    }

    lastHandledVoiceQueryId.current = voiceQuery.id;

    const normalizedQuery = voiceQuery.text.trim();
    setSearchQuery(normalizedQuery);
    handleSearch(normalizedQuery);
    if (onVoiceQueryHandled) {
      onVoiceQueryHandled();
    }
  }, [voiceQuery, handleSearch, onVoiceQueryHandled]);

  const handleSelectMedia = (media: MediaFile) => {
    setSelectedMediaId(media.id);
  };

  if (loading) {
    return (
      <div className="library-view">
        <div className="library-view__loading">Loading media library...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="library-view">
        <div className="library-view__error">
          <h2>Error Loading Media</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="library-view">
      <header className="library-view__header">
        <h1 className="library-view__title">Media Library</h1>
        <SearchBox
          onSearch={handleSearch}
          value={searchQuery}
          onValueChange={setSearchQuery}
        />
      </header>

      {statusMessage && (
        <div className="library-view__notice" role="status">
          {statusMessage}
        </div>
      )}

      <div className="library-view__content">
        <div className="library-view__grid">
          <MediaGrid media={filteredMedia} onSelect={handleSelectMedia} />
        </div>

        {selectedMediaId && (
          <aside className="library-view__detail">
            <DetailPane mediaId={selectedMediaId} />
          </aside>
        )}
      </div>
    </div>
  );
}

interface MergeResultsOutcome {
  mergedResults: MediaFile[];
  semanticOnlyCount: number;
}

function mergeSearchResults(
  textResults: MediaFile[],
  semanticResults: SemanticSearchHit[],
  mediaIndex: Map<number, MediaFile>
): MergeResultsOutcome {
  const aggregated = new Map<number, MediaFile>();
  const textIds = new Set<number>();

  textResults.forEach((item) => {
    aggregated.set(item.id, { ...item, search_origin: 'text' });
    textIds.add(item.id);
  });

  let semanticOnlyCount = 0;
  const semanticCounted = new Set<number>();

  semanticResults.forEach((hit) => {
    if (!hit || hit.media_id == null) {
      return;
    }

    const mediaId = hit.media_id;
    const existing = aggregated.get(mediaId);
    const score = hit.score ?? undefined;
    const fallbackSource = existing ?? mediaIndex.get(mediaId) ?? buildMediaFromSemanticHit(hit);
    if (!fallbackSource) {
      return;
    }

    const next: MediaFile = existing ? { ...existing } : { ...fallbackSource };
    const previousOrigin = next.search_origin ?? (textIds.has(mediaId) ? 'text' : undefined);

    if (previousOrigin === 'text') {
      next.search_origin = 'both';
    } else {
      next.search_origin = previousOrigin ?? (textIds.has(mediaId) ? 'both' : 'semantic');
    }

    if (score !== undefined) {
      next.search_score = next.search_score !== undefined ? Math.max(next.search_score, score) : score;
    }

    aggregated.set(mediaId, next);

    if (!textIds.has(mediaId) && !semanticCounted.has(mediaId)) {
      semanticOnlyCount += 1;
      semanticCounted.add(mediaId);
    }
  });

  const ordered: MediaFile[] = [];
  const seen = new Set<number>();

  textResults.forEach((item) => {
    const media = aggregated.get(item.id);
    if (!media || seen.has(item.id)) {
      return;
    }
    if (!media.search_origin) {
      media.search_origin = 'text';
    }
    ordered.push(media);
    seen.add(item.id);
  });

  const sortedSemantic = [...semanticResults].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  sortedSemantic.forEach((hit) => {
    if (!hit.media_id) {
      return;
    }
    const media = aggregated.get(hit.media_id);
    if (!media || seen.has(hit.media_id)) {
      return;
    }
    if (!media.search_origin) {
      media.search_origin = 'semantic';
    }
    ordered.push(media);
    seen.add(hit.media_id);
  });

  aggregated.forEach((media, id) => {
    if (!seen.has(id)) {
      if (!media.search_origin) {
        media.search_origin = 'semantic';
      }
      ordered.push(media);
      seen.add(id);
    }
  });

  return { mergedResults: ordered, semanticOnlyCount };
}

function buildMediaFromSemanticHit(hit: SemanticSearchHit): MediaFile | null {
  if (hit.media_id == null) {
    return null;
  }

  const metadata = hit.metadata ?? {};
  const nowIso = new Date().toISOString();
  const typeCandidate = (metadata['media_type'] ?? hit.media_type ?? 'video') as string;
  const validTypes: ReadonlyArray<MediaFile['media_type']> = ['video', 'audio', 'photo', 'game'];
  const mediaType = (validTypes.includes(typeCandidate as MediaFile['media_type'])
    ? typeCandidate
    : 'video') as MediaFile['media_type'];

  const createdAt = typeof metadata['created_at'] === 'string' ? (metadata['created_at'] as string) : nowIso;
  const modifiedAt = typeof metadata['modified_at'] === 'string' ? (metadata['modified_at'] as string) : createdAt;
  const indexedAt = typeof metadata['indexed_at'] === 'string' ? (metadata['indexed_at'] as string) : modifiedAt;

  return {
    id: hit.media_id,
    file_path: (metadata['file_path'] as string) ?? '',
    file_name: (metadata['file_name'] as string) ?? hit.title ?? `Item ${hit.media_id}`,
    file_size: typeof metadata['file_size'] === 'number' ? (metadata['file_size'] as number) : 0,
    media_type: mediaType,
    duration_seconds:
      typeof metadata['duration_seconds'] === 'number'
        ? (metadata['duration_seconds'] as number)
        : undefined,
    width: typeof metadata['width'] === 'number' ? (metadata['width'] as number) : undefined,
    height: typeof metadata['height'] === 'number' ? (metadata['height'] as number) : undefined,
    created_at: createdAt,
    modified_at: modifiedAt,
    indexed_at: indexedAt,
    play_count: typeof metadata['play_count'] === 'number' ? (metadata['play_count'] as number) : 0,
    resume_position_seconds:
      typeof metadata['resume_position_seconds'] === 'number'
        ? (metadata['resume_position_seconds'] as number)
        : 0,
    subtitle_tracks:
      typeof metadata['subtitle_tracks'] === 'string'
        ? (metadata['subtitle_tracks'] as string)
        : undefined,
  };
}
