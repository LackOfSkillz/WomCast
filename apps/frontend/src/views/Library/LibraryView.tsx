import { useState, useEffect } from 'react';
import { MediaFile, getMediaFiles, searchMediaFiles } from '../../services/api';
import { SearchBox } from '../../components/SearchBox';
import { MediaGrid } from '../../components/MediaGrid';
import { DetailPane } from '../../components/DetailPane';
import './LibraryView.css';

export function LibraryView() {
  const [allMedia, setAllMedia] = useState<MediaFile[]>([]);
  const [filteredMedia, setFilteredMedia] = useState<MediaFile[]>([]);
  const [selectedMediaId, setSelectedMediaId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadMedia() {
      try {
        setLoading(true);
        setError(null);
        const data = await getMediaFiles();
        if (mounted) {
          setAllMedia(data);
          setFilteredMedia(data);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load media');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void loadMedia();

    return () => {
      mounted = false;
    };
  }, []);

  const handleSearch = (query: string) => {
    if (!query.trim()) {
      setFilteredMedia(allMedia);
      return;
    }

    void searchMediaFiles(query)
      .then((results) => {
        setFilteredMedia(results);
      })
      .catch((err: unknown) => {
        console.error('Search failed:', err);
        // Fallback to client-side filtering
        const lowercaseQuery = query.toLowerCase();
        const filtered = allMedia.filter((media) =>
          media.file_name.toLowerCase().includes(lowercaseQuery)
        );
        setFilteredMedia(filtered);
      });
  };

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
        <SearchBox onSearch={handleSearch} />
      </header>

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
