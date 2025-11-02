import { MediaFile } from '../services/api';
import { MediaCard } from './MediaCard';
import './MediaGrid.css';

export interface MediaGridProps {
  media: MediaFile[];
  onSelect: (media: MediaFile) => void;
}

export function MediaGrid({ media, onSelect }: MediaGridProps) {
  if (media.length === 0) {
    return (
      <div className="media-grid--empty">
        <p>No media files found</p>
      </div>
    );
  }

  return (
    <div className="media-grid">
      {media.map((item) => (
        <MediaCard key={item.id} media={item} onClick={onSelect} />
      ))}
    </div>
  );
}
