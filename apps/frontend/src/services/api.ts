/**
 * API client for WomCast backend services
 */

import { fetchWithRetry } from '../utils/fetchWithRetry';
import type { Settings } from '../types/settings';
export type SettingsResponse = Partial<Settings> & Record<string, unknown>;


export type ModelVariantStatus = 'ready' | 'missing' | 'downloading' | 'failed' | 'cancelled';
export type DownloadJobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface DiskInfo {
  path: string;
  total_bytes: number;
  free_bytes: number;
}

export interface ModelVariant {
  name: string;
  display_name: string;
  estimated_size_bytes?: number | null;
  installed_size_bytes?: number | null;
  installed: boolean;
  active: boolean;
  status: ModelVariantStatus;
  download_job_id?: string | null;
  error?: string | null;
}

export interface ModelGroupStatus {
  kind: 'voice' | 'llm';
  active_model?: string | null;
  disk: DiskInfo;
  models: ModelVariant[];
}

export interface DownloadJobInfo {
  id: string;
  model: string;
  model_type: 'voice' | 'llm';
  display_name: string;
  status: DownloadJobStatus;
  progress?: number | null;
  downloaded_bytes?: number | null;
  total_bytes?: number | null;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface ModelStatusResponse {
  voice: ModelGroupStatus;
  llm: ModelGroupStatus;
  jobs: DownloadJobInfo[];
  active_job?: DownloadJobInfo | null;
}

export interface LegalProviderInfo {
  name: string;
  terms_url: string;
  privacy_url?: string | null;
  notes?: string | null;
}

export interface LegalSectionInfo {
  title: string;
  items: string[];
}

export interface LegalAcknowledgementInfo {
  version?: string | null;
  accepted_at?: string | null;
}

export interface LegalTermsResponse {
  version: string;
  last_updated: string;
  title: string;
  intro: string;
  sections: LegalSectionInfo[];
  providers: LegalProviderInfo[];
  accepted: LegalAcknowledgementInfo;
}

export interface LegalAckResponse {
  status: string;
  version: string;
  accepted_at: string;
}


const METADATA_API_URL = (import.meta.env.VITE_METADATA_API_URL as string) || 'http://localhost:8001';
const PLAYBACK_API_URL = (import.meta.env.VITE_PLAYBACK_API_URL as string) || 'http://localhost:8002';
const LIVETV_API_URL = (import.meta.env.VITE_LIVETV_API_URL as string) || 'http://localhost:3007';
const CAST_API_URL = (import.meta.env.VITE_CAST_API_URL as string) || 'http://localhost:3005';
const SETTINGS_API_URL = (import.meta.env.VITE_SETTINGS_API_URL as string) || 'http://localhost:3006';
const VOICE_API_URL = (import.meta.env.VITE_VOICE_API_URL as string) || 'http://localhost:3003';
const SEARCH_API_URL = (import.meta.env.VITE_SEARCH_API_URL as string) || 'http://localhost:3004';

const metadataFetch = (input: string, init?: RequestInit) =>
  fetchWithRetry(input, init, { serviceName: 'Metadata API' });

const playbackFetch = (input: string, init?: RequestInit) =>
  fetchWithRetry(input, init, { serviceName: 'Playback API' });

const liveTvFetch = (input: string, init?: RequestInit) =>
  fetchWithRetry(input, init, { serviceName: 'Live TV API' });

const castFetch = (input: string, init?: RequestInit) =>
  fetchWithRetry(input, init, { serviceName: 'Cast API' });

const settingsFetch = (input: string, init?: RequestInit) =>
  fetchWithRetry(input, init, { serviceName: 'Settings API' });

const voiceFetch = (input: string, init?: RequestInit) =>
  fetchWithRetry(input, init, { serviceName: 'Voice API' });

const searchFetch = (input: string, init?: RequestInit) =>
  fetchWithRetry(input, init, { serviceName: 'Search API' });

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
  subtitle_tracks?: string; // JSON string of subtitle track array
  search_origin?: 'text' | 'semantic' | 'both';
  search_score?: number;
}

export interface SemanticSearchHit {
  media_id: number | null;
  title: string | null;
  media_type: string | null;
  score: number | null;
  document: string | null;
  metadata: Record<string, unknown>;
}

export interface SemanticSearchResponse {
  count: number;
  latency_ms: number;
  results: SemanticSearchHit[];
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

  const response = await metadataFetch(url.toString());
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

  const response = await metadataFetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to search media files: ${response.statusText}`);
  }

  return response.json() as Promise<MediaFile[]>;
}

/**
 * Perform semantic search via the dedicated search service
 */
export async function semanticSearchMedia(
  query: string,
  limit: number = 10
): Promise<SemanticSearchResponse> {
  const url = new URL(`${SEARCH_API_URL}/v1/search/semantic`);
  url.searchParams.set('q', query);
  url.searchParams.set('limit', limit.toString());

  const response = await searchFetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to run semantic search: ${response.statusText}`);
  }

  return response.json() as Promise<SemanticSearchResponse>;
}

/**
 * Get detailed media information with metadata
 */
export async function getMediaItem(id: number): Promise<MediaItem> {
  const response = await metadataFetch(`${METADATA_API_URL}/v1/media/${id.toString()}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch media item: ${response.statusText}`);
  }

  return response.json() as Promise<MediaItem>;
}

/**
 * Start playback of a media file
 */
export async function playMedia(filePath: string): Promise<void> {
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/play`, {
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
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/stop`, {
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
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/pause`, {
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
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/player/state`);
  if (!response.ok) {
    throw new Error(`Failed to get player state: ${response.statusText}`);
  }

  return response.json() as Promise<PlayerState>;
}

export async function sendInputAction(action: string): Promise<void> {
  const normalized = action.trim().toLowerCase();
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/input/${encodeURIComponent(normalized)}`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to send input action: ${response.statusText}`);
  }
}

export async function quitPlaybackApplication(): Promise<void> {
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/application/quit`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to quit playback application: ${response.statusText}`);
  }
}

export async function getVolume(): Promise<number> {
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/volume`);
  if (!response.ok) {
    throw new Error(`Failed to get volume: ${response.statusText}`);
  }

  const payload = (await response.json()) as { volume: number };
  return payload.volume;
}

export async function adjustVolume(delta: number): Promise<number> {
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/volume/adjust`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ delta }),
  });

  if (!response.ok) {
    throw new Error(`Failed to adjust volume: ${response.statusText}`);
  }

  const payload = (await response.json()) as { volume: number };
  return payload.volume;
}

/**
 * Seek to a specific position
 */
export async function seekPlayback(positionSeconds: number): Promise<void> {
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/seek`, {
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
 * Update resume position for a media file
 */
export async function updateResumePosition(
  mediaId: number,
  positionSeconds: number
): Promise<void> {
  const response = await metadataFetch(`${METADATA_API_URL}/v1/media/${mediaId.toString()}/resume`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ position_seconds: positionSeconds }),
  });

  if (!response.ok) {
    throw new Error(`Failed to update resume position: ${response.statusText}`);
  }
}

export interface SubtitleTrack {
  index: number;
  language: string;
  name: string;
  current: boolean;
}

/**
 * Get available subtitle tracks
 */
export async function getSubtitles(): Promise<SubtitleTrack[]> {
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/subtitles`);
  if (!response.ok) {
    throw new Error(`Failed to get subtitles: ${response.statusText}`);
  }

  return response.json() as Promise<SubtitleTrack[]>;
}

/**
 * Set active subtitle track
 */
export async function setSubtitle(subtitleIndex: number): Promise<void> {
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/subtitles`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ subtitle_index: subtitleIndex }),
  });

  if (!response.ok) {
    throw new Error(`Failed to set subtitle: ${response.statusText}`);
  }
}

/**
 * Toggle subtitles on/off
 */
export async function toggleSubtitles(): Promise<void> {
  const response = await playbackFetch(`${PLAYBACK_API_URL}/v1/subtitles/toggle`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to toggle subtitles: ${response.statusText}`);
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

export async function getModelStatus(): Promise<ModelStatusResponse> {
  const response = await voiceFetch(`${VOICE_API_URL}/v1/voice/models/status`);

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to load model status: ${statusText}`);
  }

  return (await response.json()) as ModelStatusResponse;
}

export async function startModelDownload(kind: 'voice' | 'llm', model: string): Promise<DownloadJobInfo> {
  const response = await voiceFetch(`${VOICE_API_URL}/v1/voice/models/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, model }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({} as Record<string, unknown>));
    const detail = typeof payload.detail === 'string' ? payload.detail : response.statusText || 'Unknown error';
    throw new Error(`Failed to start download: ${detail}`);
  }

  return (await response.json()) as DownloadJobInfo;
}

export async function cancelModelDownload(jobId: string): Promise<DownloadJobInfo> {
  const response = await voiceFetch(`${VOICE_API_URL}/v1/voice/models/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({} as Record<string, unknown>));
    const detail = typeof payload.detail === 'string' ? payload.detail : response.statusText || 'Unknown error';
    throw new Error(`Failed to cancel download: ${detail}`);
  }

  return (await response.json()) as DownloadJobInfo;
}

// Live TV API

export interface LiveTVChannel {
  id: number;
  name: string;
  stream_url: string;
  logo_url: string | null;
  group_title: string | null;
  language: string | null;
  tvg_id: string | null;
  codec_info: string | null;
}

export async function getLiveTVChannels(group?: string, limit: number = 100): Promise<LiveTVChannel[]> {
  const params = new URLSearchParams();
  if (group) {
    params.append('group', group);
  }
  params.append('limit', String(limit));

  const response = await liveTvFetch(`${LIVETV_API_URL}/v1/livetv/channels?${params.toString()}`);
  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to get channels: ${statusText}`);
  }
  return (await response.json()) as LiveTVChannel[];
}

export async function getLiveTVChannel(channelId: number): Promise<LiveTVChannel> {
  const response = await liveTvFetch(`${LIVETV_API_URL}/v1/livetv/channels/${String(channelId)}`);
  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to get channel: ${statusText}`);
  }
  return (await response.json()) as LiveTVChannel;
}

export async function playLiveTVChannel(streamUrl: string, title: string): Promise<void> {
  try {
    await playMedia(streamUrl);
  } catch (error) {
    const details = error instanceof Error ? error.message : 'Unknown error';
    throw new Error(`Failed to play channel "${title}": ${details}`);
  }
}

export interface EPGProgram {
  channel_id: string;
  title: string;
  start_time: string;
  end_time: string;
  description: string | null;
  category: string | null;
  episode: string | null;
  icon: string | null;
  is_current: boolean;
  progress_percent: number;
}

export interface EPGData {
  channel_id: string;
  current_program: EPGProgram | null;
  next_program: EPGProgram | null;
}

export async function getAllEPG(): Promise<EPGData[]> {
  const response = await liveTvFetch(`${LIVETV_API_URL}/v1/livetv/epg`);
  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to get EPG: ${statusText}`);
  }
  return (await response.json()) as EPGData[];
}

export async function getChannelEPG(channelId: string): Promise<EPGData> {
  const response = await liveTvFetch(`${LIVETV_API_URL}/v1/livetv/epg/${channelId}`);
  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to get channel EPG: ${statusText}`);
  }
  return (await response.json()) as EPGData;
}

export async function setEPGUrl(url: string): Promise<void> {
  const response = await liveTvFetch(`${LIVETV_API_URL}/v1/livetv/epg/url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to set EPG URL: ${statusText}`);
  }
}

// Cast API

export interface CastSession {
  session_id: string;
  pin: string;
  qr_data: string;
  expires_in_seconds: number;
}

export async function createCastSession(deviceType: string = 'phone'): Promise<CastSession> {
  const response = await castFetch(`${CAST_API_URL}/v1/cast/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device_type: deviceType }),
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to create cast session: ${statusText}`);
  }

  return (await response.json()) as CastSession;
}

export async function fetchCastSessionQr(sessionId: string, signal?: AbortSignal): Promise<Blob> {
  const response = await castFetch(`${CAST_API_URL}/v1/cast/session/${sessionId}/qr`, {
    method: 'GET',
    signal,
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to fetch cast session QR: ${statusText}`);
  }

  return response.blob();
}

export interface CastSessionInfo {
  session_id?: string;
  id?: string | number;
  device_name?: string | null;
  device_info?: {
    name?: string;
    device_name?: string;
  } | null;
  expires_at?: string | null;
  [key: string]: unknown;
}

export interface CastSessionsResponse {
  sessions?: CastSessionInfo[];
  [key: string]: unknown;
}

export async function getCastSessions(signal?: AbortSignal): Promise<CastSessionsResponse> {
  const response = await castFetch(`${CAST_API_URL}/v1/cast/sessions`, {
    method: 'GET',
    signal,
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to load cast sessions: ${statusText}`);
  }

  return (await response.json()) as CastSessionsResponse;
}

export async function deleteCastSession(sessionId: string): Promise<Record<string, unknown>> {
  const response = await castFetch(`${CAST_API_URL}/v1/cast/session/${sessionId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to delete cast session: ${statusText}`);
  }

  return (await response.json()) as Record<string, unknown>;
}

export async function resetCastSessions(): Promise<Record<string, unknown>> {
  const response = await castFetch(`${CAST_API_URL}/v1/cast/sessions`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to reset cast sessions: ${statusText}`);
  }

  return (await response.json()) as Record<string, unknown>;
}

export async function fetchPwaQr(origin?: string, signal?: AbortSignal): Promise<Blob> {
  const url = new URL(`${CAST_API_URL}/v1/cast/pwa/qr`);
  if (origin && origin !== 'null' && origin !== 'file://') {
    url.searchParams.set('origin', origin);
  }

  const response = await castFetch(url.toString(), {
    method: 'GET',
    signal,
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to fetch PWA QR: ${statusText}`);
  }

  return response.blob();
}

// Settings API

export async function getSettings(): Promise<SettingsResponse> {
  const response = await settingsFetch(`${SETTINGS_API_URL}/v1/settings`);

  if (!response.ok) {
    throw new Error(`Failed to fetch settings: ${response.statusText || 'Unknown error'}`);
  }

  return (await response.json()) as SettingsResponse;
}

export async function updateSingleSetting(key: string, value: unknown): Promise<void> {
  const response = await settingsFetch(`${SETTINGS_API_URL}/v1/settings/${key}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, value }),
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to update setting: ${statusText}`);
  }
}

export async function updateMultipleSettings(updates: Partial<Settings>): Promise<SettingsResponse> {
  const response = await settingsFetch(`${SETTINGS_API_URL}/v1/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ settings: updates }),
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to update settings: ${statusText}`);
  }

  return (await response.json()) as SettingsResponse;
}

export async function resetAllSettings(): Promise<SettingsResponse> {
  const response = await settingsFetch(`${SETTINGS_API_URL}/v1/settings/reset`, {
    method: 'POST',
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to reset settings: ${statusText}`);
  }

  return (await response.json()) as SettingsResponse;
}

export async function deleteSetting(key: string): Promise<Record<string, string>> {
  const response = await settingsFetch(`${SETTINGS_API_URL}/v1/settings/${key}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to delete setting: ${statusText}`);
  }

  return (await response.json()) as Record<string, string>;
}

export async function getLegalTermsNotice(): Promise<LegalTermsResponse> {
  const response = await settingsFetch(`${SETTINGS_API_URL}/v1/legal/terms`);

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to load legal terms: ${statusText}`);
  }

  return (await response.json()) as LegalTermsResponse;
}

export async function acknowledgeLegalTerms(version: string): Promise<LegalAckResponse> {
  const response = await settingsFetch(`${SETTINGS_API_URL}/v1/legal/ack`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ version }),
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to acknowledge legal terms: ${statusText}`);
  }

  return (await response.json()) as LegalAckResponse;
}

export async function exportPrivacyData(signal?: AbortSignal): Promise<Response> {
  const response = await settingsFetch(`${SETTINGS_API_URL}/v1/privacy/export`, {
    method: 'GET',
    signal,
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to export privacy data: ${statusText}`);
  }

  return response;
}

export async function deletePrivacyData(): Promise<Record<string, unknown>> {
  const response = await settingsFetch(`${SETTINGS_API_URL}/v1/privacy/delete`, {
    method: 'POST',
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to delete privacy data: ${statusText}`);
  }

  return (await response.json()) as Record<string, unknown>;
}

export async function deleteVoiceHistory(): Promise<Record<string, unknown>> {
  const response = await voiceFetch(`${VOICE_API_URL}/v1/voice/history`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const statusText = response.statusText || 'Unknown error';
    throw new Error(`Failed to delete voice history: ${statusText}`);
  }

  return (await response.json()) as Record<string, unknown>;
}
