/**
 * API client for WomCast backend services
 */

const METADATA_API_URL = import.meta.env.VITE_METADATA_API_URL || 'http://localhost:8001';
const PLAYBACK_API_URL = import.meta.env.VITE_PLAYBACK_API_URL || 'http://localhost:8002';

export interface MediaFile {
  id: number;
  file_path: string;
  file_name: string;
  file_size: number;
  media_type: 'video' | 'audio' | 'photo' | 'game';
  duration_seconds?: number;
  width?: number;
  height?: number;
  created_at: string;
  modified_at: string;
  indexed_at: string;
  play_count: number;
  resume_position_seconds: number;
}

export interface VideoMetadata {
  id: number;
  media_file_id: number;
  title?: string;
  year?: number;
  genre?: string;
  director?: string;
  plot?: string;
  rating?: number;
  poster_url?: string;
}

export interface AudioMetadata {
  id: number;
  media_file_id: number;
  title?: string;
  artist?: string;
  album?: string;
  year?: number;
  genre?: string;
  track_number?: number;
  artwork_url?: string;
}

export interface PlayerState {
  player_id?: number;
  playing: boolean;
  paused: boolean;
  position_seconds: number;
  duration_seconds: number;
  speed: number;
  media_type?: string;
  title?: string;
  file_path?: string;
}

export interface MediaItem extends MediaFile {
  video_metadata?: VideoMetadata;
  audio_metadata?: AudioMetadata;
}

/**
 * Fetch all media files from the database
 */
export async function getMediaFiles(
  mediaType?: 'video' | 'audio' | 'photo' | 'game'
): Promise<MediaFile[]> {
  const url = new URL(`${METADATA_API_URL}/v1/media`);
  if (mediaType) {
    url.searchParams.set('type', mediaType);
  }

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to fetch media files: ${response.statusText}`);
  }

  return response.json() as Promise<MediaFile[]>;
}

/**
 * Search media files by name
 */
export async function searchMediaFiles(query: string): Promise<MediaFile[]> {
  const url = new URL(`${METADATA_API_URL}/v1/media/search`);
  url.searchParams.set('q', query);

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to search media files: ${response.statusText}`);
  }

  return response.json() as Promise<MediaFile[]>;
}

/**
 * Get detailed media information with metadata
 */
export async function getMediaItem(id: number): Promise<MediaItem> {
  const response = await fetch(`${METADATA_API_URL}/v1/media/${id.toString()}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch media item: ${response.statusText}`);
  }

  return response.json() as Promise<MediaItem>;
}

/**
 * Start playback of a media file
 */
export async function playMedia(filePath: string): Promise<void> {
  const response = await fetch(`${PLAYBACK_API_URL}/v1/play`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ file_path: filePath }),
  });

  if (!response.ok) {
    throw new Error(`Failed to start playback: ${response.statusText}`);
  }
}

/**
 * Stop playback
 */
export async function stopPlayback(): Promise<void> {
  const response = await fetch(`${PLAYBACK_API_URL}/v1/stop`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to stop playback: ${response.statusText}`);
  }
}

/**
 * Pause/unpause playback
 */
export async function pausePlayback(): Promise<void> {
  const response = await fetch(`${PLAYBACK_API_URL}/v1/pause`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to pause playback: ${response.statusText}`);
  }
}

/**
 * Get current player state
 */
export async function getPlayerState(): Promise<PlayerState> {
  const response = await fetch(`${PLAYBACK_API_URL}/v1/player/state`);
  if (!response.ok) {
    throw new Error(`Failed to get player state: ${response.statusText}`);
  }

  return response.json() as Promise<PlayerState>;
}

/**
 * Seek to a specific position
 */
export async function seekPlayback(positionSeconds: number): Promise<void> {
  const response = await fetch(`${PLAYBACK_API_URL}/v1/seek`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ position_seconds: positionSeconds }),
  });

  if (!response.ok) {
    throw new Error(`Failed to seek: ${response.statusText}`);
  }
}

/**
 * Format duration in seconds to readable time string
 */
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours.toString()}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes.toString()}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format file size to readable string
 */
export function formatFileSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  const unit = units[unitIndex];
  return unit !== undefined ? `${size.toFixed(1)} ${unit}` : `${bytes.toString()} B`;
}
