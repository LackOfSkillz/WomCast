import { useEffect, useState } from 'react';
import {
  MediaItem,
  getMediaItem,
  playMedia,
  formatDuration,
  formatFileSize,
} from '../services/api';
import './DetailPane.css';

export interface DetailPaneProps {
  mediaId: number;
}

export function DetailPane({ mediaId }: DetailPaneProps) {
  const [media, setMedia] = useState<MediaItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadMedia() {
      try {
        setLoading(true);
        setError(null);
        const data = await getMediaItem(mediaId);
        if (mounted) {
          setMedia(data);
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
  }, [mediaId]);

  const handlePlay = () => {
    if (!media) return;

    void playMedia(media.file_path).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : 'Failed to start playback');
    });
  };

  if (loading) {
    return (
      <div className="detail-pane">
        <div className="detail-pane__loading">Loading...</div>
      </div>
    );
  }

  if (error || !media) {
    return (
      <div className="detail-pane">
        <div className="detail-pane__error">{error || 'Media not found'}</div>
      </div>
    );
  }

  const hasResumePosition = media.resume_position_seconds > 0;
  const resumePercentage = Math.round(
    (media.resume_position_seconds / (media.duration_seconds || 1)) * 100
  );

  // Parse subtitle tracks
  let subtitles: Array<{ language: string; format: string }> = [];
  if (media.subtitle_tracks) {
    try {
      subtitles = JSON.parse(media.subtitle_tracks) as Array<{
        language: string;
        format: string;
      }>;
    } catch {
      // Ignore JSON parse errors
    }
  }

  return (
    <div className="detail-pane">
      <div className="detail-pane__header">
        <h2 className="detail-pane__title">{media.file_name}</h2>
        <button
          className="detail-pane__play-button"
          onClick={handlePlay}
          aria-label="Play media"
        >
          ▶ Play
        </button>
      </div>

      {hasResumePosition && (
        <div className="detail-pane__resume">
          <div className="detail-pane__resume-label">
            Resume from {formatDuration(media.resume_position_seconds)}
          </div>
          <div className="detail-pane__resume-bar">
            <div
              className="detail-pane__resume-progress"
              style={{ width: `${resumePercentage.toString()}%` }}
            />
          </div>
        </div>
      )}

      <div className="detail-pane__metadata">
        <div className="detail-pane__section">
          <h3 className="detail-pane__section-title">File Information</h3>
          <dl className="detail-pane__list">
            <dt>Type</dt>
            <dd className="detail-pane__value--capitalize">{media.media_type}</dd>
            <dt>Size</dt>
            <dd>{formatFileSize(media.file_size)}</dd>
            {media.duration_seconds && (
              <>
                <dt>Duration</dt>
                <dd>{formatDuration(media.duration_seconds)}</dd>
              </>
            )}
            {media.width !== undefined && media.height !== undefined && (
              <>
                <dt>Resolution</dt>
                <dd>{media.width.toString()} × {media.height.toString()}</dd>
              </>
            )}
            {media.play_count > 0 && (
              <>
                <dt>Play Count</dt>
                <dd>{media.play_count}</dd>
              </>
            )}
            {subtitles.length > 0 && (
              <>
                <dt>Subtitles</dt>
                <dd>
                  {subtitles
                    .map((sub) => `${sub.language} (${sub.format})`)
                    .join(', ')}
                </dd>
              </>
            )}
          </dl>
        </div>

        {media.video_metadata && (
          <div className="detail-pane__section">
            <h3 className="detail-pane__section-title">Video Details</h3>
            <dl className="detail-pane__list">
              {media.video_metadata.title && (
                <>
                  <dt>Title</dt>
                  <dd>{media.video_metadata.title}</dd>
                </>
              )}
              {media.video_metadata.year && (
                <>
                  <dt>Year</dt>
                  <dd>{media.video_metadata.year}</dd>
                </>
              )}
              {media.video_metadata.genre && (
                <>
                  <dt>Genre</dt>
                  <dd>{media.video_metadata.genre}</dd>
                </>
              )}
              {media.video_metadata.director && (
                <>
                  <dt>Director</dt>
                  <dd>{media.video_metadata.director}</dd>
                </>
              )}
              {media.video_metadata.rating && (
                <>
                  <dt>Rating</dt>
                  <dd>{media.video_metadata.rating}/10</dd>
                </>
              )}
            </dl>
            {media.video_metadata.plot && (
              <div className="detail-pane__plot">
                <h4 className="detail-pane__plot-title">Plot</h4>
                <p className="detail-pane__plot-text">{media.video_metadata.plot}</p>
              </div>
            )}
          </div>
        )}

        {media.audio_metadata && (
          <div className="detail-pane__section">
            <h3 className="detail-pane__section-title">Audio Details</h3>
            <dl className="detail-pane__list">
              {media.audio_metadata.title && (
                <>
                  <dt>Title</dt>
                  <dd>{media.audio_metadata.title}</dd>
                </>
              )}
              {media.audio_metadata.artist && (
                <>
                  <dt>Artist</dt>
                  <dd>{media.audio_metadata.artist}</dd>
                </>
              )}
              {media.audio_metadata.album && (
                <>
                  <dt>Album</dt>
                  <dd>{media.audio_metadata.album}</dd>
                </>
              )}
              {media.audio_metadata.year && (
                <>
                  <dt>Year</dt>
                  <dd>{media.audio_metadata.year}</dd>
                </>
              )}
              {media.audio_metadata.genre && (
                <>
                  <dt>Genre</dt>
                  <dd>{media.audio_metadata.genre}</dd>
                </>
              )}
              {media.audio_metadata.track_number && (
                <>
                  <dt>Track</dt>
                  <dd>{media.audio_metadata.track_number}</dd>
                </>
              )}
            </dl>
          </div>
        )}
      </div>

      <div className="detail-pane__path">
        <strong>Path:</strong> {media.file_path}
      </div>
    </div>
  );
}
