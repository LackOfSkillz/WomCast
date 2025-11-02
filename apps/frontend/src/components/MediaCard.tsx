import { MediaFile, formatDuration, formatFileSize } from '../services/api';
import './MediaCard.css';

export interface MediaCardProps {
  media: MediaFile;
  onClick: (media: MediaFile) => void;
}

export function MediaCard({ media, onClick }: MediaCardProps): React.JSX.Element {
  const getMediaIcon = (type: string): string => {
    switch (type) {
      case 'video':
        return '🎬';
      case 'audio':
        return '🎵';
      case 'photo':
        return '📷';
      case 'game':
        return '🎮';
      default:
        return '📁';
    }
  };

  const handleClick = () => {
    onClick(media);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick(media);
    }
  };

  return (
    <div
      className="media-card"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`Play ${media.file_name}`}
    >
      <div className="media-card__thumbnail">
        <span className="media-card__icon">{getMediaIcon(media.media_type)}</span>
        {media.duration_seconds && (
          <span className="media-card__duration">
            {formatDuration(media.duration_seconds)}
          </span>
        )}
        {media.resume_position_seconds > 0 && media.duration_seconds && (
          <div
            className="media-card__progress"
            style={{
              width: `${Math.round((media.resume_position_seconds / media.duration_seconds) * 100).toString()}%`,
            }}
          />
        )}
      </div>
      <div className="media-card__info">
        <h3 className="media-card__title" title={media.file_name}>
          {media.file_name}
        </h3>
        <div className="media-card__meta">
          <span className="media-card__type">{media.media_type}</span>
          <span className="media-card__size">{formatFileSize(media.file_size)}</span>
        </div>
        {media.play_count > 0 && (
          <div className="media-card__plays">▶ {media.play_count}</div>
        )}
      </div>
    </div>
  );
}
