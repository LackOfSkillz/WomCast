export interface Settings {
  // Voice/AI models
  voice_model: string;
  llm_model: string | null;
  stt_enabled: boolean;
  tts_enabled: boolean;
  voice_language?: string;

  // Network shares
  auto_mount_shares: boolean;
  auto_index_shares: boolean;

  // Privacy flags
  analytics_enabled: boolean;
  crash_reporting_enabled: boolean;
  metadata_fetching_enabled: boolean;
  voice_history_days?: number;
  cast_history_days?: number;

  // Pairing
  pairing_enabled?: boolean;
  pairing_pin_length?: number;
  pairing_session_timeout?: number;

  // CEC
  cec_enabled?: boolean;
  cec_auto_switch?: boolean;

  // Network
  stun_server?: string;
  turn_server?: string;
  turn_username?: string;
  turn_password?: string;
  mdns_enabled?: boolean;
  network_diagnostics_enabled?: boolean;

  // UI preferences
  theme: 'dark' | 'light' | 'auto';
  language: string;
  grid_size: 'small' | 'medium' | 'large';
  autoplay_next: boolean;
  show_subtitles: boolean;

  // Playback settings
  default_volume: number;
  resume_threshold_seconds: number;
  skip_intro_seconds: number;

  // Performance
  cache_size_mb: number;
  thumbnail_quality: 'low' | 'medium' | 'high';

  // Notifications
  show_notifications: boolean;
  notification_duration_ms: number;
}
